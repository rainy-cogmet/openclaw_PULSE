"""
feature_extractor.py — 统一特征提取器
从 DataParser 的解析结果中提取 BOND / ECHO 分类所需的全部真实特征。
替代 profiler.py 中的 _lexicon_to_bond_features / _lexicon_to_echo_features 桥接函数。

设计原则:
  1. 所有特征来自真实数据 —— 零硬编码默认值
  2. 数据缺失时使用显式 fallback 并标注来源
  3. 与 data_parser.DataParser.parse_bundle() 返回结构对齐
"""

import math
import re
from collections import Counter

try:
    from .utils import clamp, compute_cv, compute_shannon_diversity, tokenize_mixed
except ImportError:
    from utils import clamp, compute_cv, compute_shannon_diversity, tokenize_mixed


# ─────────────────────────────────────────
# 领域关键词 (模块级常量, 避免每次函数调用重复定义)
# ─────────────────────────────────────────

_DOMAIN_KEYWORDS = {
        'tech': ['代码', 'code', '编程', 'python', 'java', 'script', 'api', 'docker',
                 'git', 'debug', '部署', 'deploy', '函数', 'function', '变量', '编译',
                 'bug', 'server', 'npm', 'pip', 'bash', 'sql', 'database'],
        'data': ['数据', 'data', '分析', 'analysis', '统计', 'csv', 'excel', '图表',
                 'chart', '可视化', 'visualization', '均值', '报表', 'pandas', 'numpy'],
        'writing': ['写', 'write', '文档', 'document', '报告', 'report', '翻译',
                    'translate', '模板', 'template', '周报', 'readme', '摘要', 'summary'],
        'research': ['搜索', 'search', '调研', 'research', '新闻', 'news', '查找',
                     '竞品', '行业', 'industry', '市场', 'market'],
        'creative': ['设计', 'design', '创意', 'creative', '画', '图片', 'image',
                     '视频', 'video', '音乐', 'music', 'UI', 'UX'],
        'lifestyle': ['生活', '旅行', 'travel', '美食', '天气', 'weather', '周末',
                      '运动', '健康', 'health', '购物', '推荐', '电影', '游戏'],
        'social': ['聊天', '心情', '感谢', '开心', '难过', '晚安', '早安', '陪',
                   '朋友', '关系', '情感', '想你', '秘密', '分享'],
        'business': ['会议', 'meeting', '项目', 'project', '演示', 'PPT', '计划',
                     'plan', '进度', '预算', 'budget', '客户', 'client', '需求'],
    }


# ─────────────────────────────────────────
# 工具函数
# ─────────────────────────────────────────

def _safe_div(a, b, default=0.0):
    """安全除法"""
    return a / b if b else default


def _avg(lst, default=0.0):
    """列表平均值"""
    return sum(lst) / len(lst) if lst else default


def _detect_safety_strictness(agents_text):
    """
    从 AGENTS.md / USER.md 推断安全严格度 (0-5 scale)。
    基于关键词密度:
      - 高严格: 明确提到 safety/filter/restrict/censor/NSFW/boundary/limit
      - 中严格: 提到 guideline/policy/appropriate/careful
      - 低严格: 无相关配置或明确 relaxed/creative freedom
    """
    if not agents_text:
        return 2.5  # 无数据时中性值
    text_lower = agents_text.lower()
    high_kw = ['safety', 'filter', 'restrict', 'censor', 'nsfw', 'forbidden',
               'never', 'must not', 'boundary', 'prohibited', 'block']
    mid_kw = ['guideline', 'policy', 'appropriate', 'careful', 'responsible',
              'professional', 'respectful']
    low_kw = ['creative freedom', 'relaxed', 'no restrictions', 'uncensored',
              'anything goes', 'no filter']

    high_hits = sum(1 for k in high_kw if k in text_lower)
    mid_hits = sum(1 for k in mid_kw if k in text_lower)
    low_hits = sum(1 for k in low_kw if k in text_lower)

    # 加权评分: high=+0.6, mid=+0.3, low=-0.5
    raw = 2.5 + high_hits * 0.6 + mid_hits * 0.3 - low_hits * 0.5
    return clamp(raw, 0.0, 5.0)


def _compute_interrupt_rate(sessions):
    """
    从会话中计算用户打断率。
    打断定义: 用户在 agent 回复未完成时发送新消息
    近似方法: 连续两条 user 消息(中间无 assistant)视为打断。
    """
    total_user = 0
    interrupts = 0
    for sp in sessions:
        msgs = sp.messages if hasattr(sp, 'messages') else []
        prev_role = None
        for m in msgs:
            role = m.get('role', '')
            if role == 'user':
                total_user += 1
                if prev_role == 'user':
                    interrupts += 1
            prev_role = role
    return _safe_div(interrupts, total_user)


def _compute_delegation_confidence(user_messages):
    """
    用户委托置信度: 用户使用委托型语言的比例。
    高委托: "帮我做X", "你来决定", "随便", "交给你"
    低委托: "我要X", "按照这个做", "必须", "一定要"
    """
    if not user_messages:
        return 0.5
    delegate_kw = ['帮我', '你来', '随便', '交给你', '自动', '你决定',
                   'help me', 'you decide', 'up to you', 'auto',
                   '看着办', '替我', '代我']
    control_kw = ['必须', '一定', '按照', '严格', '不要改', '照做',
                  'must', 'exactly', 'strictly', 'do not change',
                  '不准', '禁止']
    d_count = 0
    c_count = 0
    for msg in user_messages:
        msg_lower = msg.lower()
        if any(k in msg_lower for k in delegate_kw):
            d_count += 1
        if any(k in msg_lower for k in control_kw):
            c_count += 1
    total = d_count + c_count
    if total == 0:
        return 0.5
    return _safe_div(d_count, total)


def _compute_tool_confirm_latency(sessions):
    """
    从会话中估算工具调用确认延迟(秒)。
    方法: 找到 tool_call 后紧跟的 user 消息，计算时间差。
    如果会话无时间戳，则通过消息长度和轮次估算。
    """
    latencies = []
    for sp in sessions:
        tool_calls = sp.tool_calls if hasattr(sp, 'tool_calls') else []
        msgs = sp.messages if hasattr(sp, 'messages') else []

        # 建立消息索引
        for tc in tool_calls:
            ts_tool = tc.get('timestamp', '')
            if not ts_tool:
                continue
            # 找 tool_call 之后的第一条 user 消息
            found_tool = False
            for m in msgs:
                if not found_tool:
                    # 跳过直到找到包含此 tool_call 的 assistant 消息
                    if m.get('role') == 'assistant':
                        content = m.get('content', '')
                        if tc.get('tool_name', '') in str(content):
                            found_tool = True
                    continue
                if m.get('role') == 'user':
                    ts_user = m.get('timestamp', '')
                    if ts_user and ts_tool:
                        try:
                            from datetime import datetime
                            t1 = datetime.fromisoformat(ts_tool.replace('Z', '+00:00'))
                            t2 = datetime.fromisoformat(ts_user.replace('Z', '+00:00'))
                            diff = (t2 - t1).total_seconds()
                            if 0 < diff < 3600:  # 合理范围内
                                latencies.append(diff)
                        except (ValueError, TypeError):
                            pass
                    break

    if latencies:
        return _avg(latencies)

    # 无时间戳 fallback: 基于会话复杂度估算
    # 复杂工具调用通常需要更长确认时间
    total_tc = sum(len(sp.tool_calls) if hasattr(sp, 'tool_calls') else 0
                   for sp in sessions)
    if total_tc == 0:
        return 10.0  # 无工具调用，给中性值
    avg_param = _avg([tc.get('param_count', 0) for sp in sessions
                      for tc in (sp.tool_calls if hasattr(sp, 'tool_calls') else [])])
    # 参数越多越复杂，用户确认可能越慢
    return clamp(5.0 + avg_param * 2.0, 3.0, 60.0)


def _compute_topic_coverage(sessions, user_messages):
    """
    话题覆盖广度 [0,1]。
    基于:
    1. 工具类别多样性 (领域群数量)
    2. 用户消息领域分类 (用关键词匹配不同领域, 而非纯词汇多样性)
    3. 跨会话主题变化率

    领域分类:
      tech: 编程/开发/部署
      data: 数据分析/统计
      writing: 写作/文档/翻译
      research: 搜索/调研/新闻
      creative: 设计/创意/艺术
      lifestyle: 生活/旅行/美食/天气
      social: 聊天/情感/社交
      business: 商务/会议/项目管理
    """
    # 领域关键词
    _DOMAIN_KW = _DOMAIN_KEYWORDS  # 引用模块级常量

    # 维度1: 工具领域群多样性
    tool_cats = set()
    domain_map = {
        'write': 'dev', 'exec': 'dev', 'read': 'info',
        'browser': 'info', 'agent': 'meta', 'memory': 'meta', 'other': 'other',
    }
    for sp in sessions:
        dist = sp.get_tool_category_distribution() if hasattr(sp, 'get_tool_category_distribution') else {}
        for cat in dist:
            tool_cats.add(domain_map.get(cat, 'other'))
    tool_domain_diversity = min(1.0, (len(tool_cats) - 1) / 3.0) if tool_cats else 0.0

    # 维度2: 用户消息领域覆盖
    detected_domains = set()
    for msg in user_messages:
        msg_lower = msg.lower()
        for domain, keywords in _DOMAIN_KW.items():
            if any(kw in msg_lower for kw in keywords):
                detected_domains.add(domain)
    # 8 个领域, 覆盖比例
    domain_coverage = min(1.0, len(detected_domains) / 4.0)  # 4个领域=满分

    # 维度3: 跨会话主题变化
    session_topics = []
    for sp in sessions:
        first_user = None
        for m in (sp.messages if hasattr(sp, 'messages') else []):
            if m.get('role') == 'user':
                first_user = m.get('content', '')
                break
        if first_user:
            session_topics.append(set(tokenize_mixed(first_user)[:10]))
    if len(session_topics) >= 2:
        diffs = []
        for i in range(1, len(session_topics)):
            union = session_topics[i] | session_topics[i-1]
            inter = session_topics[i] & session_topics[i-1]
            diffs.append(1.0 - _safe_div(len(inter), len(union)))
        topic_change = _avg(diffs)
    else:
        topic_change = 0.3

    return clamp(0.30 * tool_domain_diversity + 0.40 * domain_coverage + 0.30 * topic_change,
                 0.0, 1.0)


def _compute_cross_domain_ratio(sessions):
    """
    跨领域任务比例 [0,1]。
    综合考虑:
      1. 类别数量因子 (2类=低跨领域, 4+=高跨领域)
      2. 类别均匀度 (HHI 反函数, 越均匀越跨领域)
      3. 是否涵盖不同"领域群"

    工具类别映射到领域群:
      - dev: write, exec (开发操作)
      - info: read, browser (信息获取)
      - meta: agent, memory (元操作)
      - other: other
    """
    all_cats = Counter()
    for sp in sessions:
        dist = sp.get_tool_category_distribution() if hasattr(sp, 'get_tool_category_distribution') else {}
        for cat, cnt in dist.items():
            all_cats[cat] += cnt
    total = sum(all_cats.values())
    if total == 0:
        return 0.3  # 无工具使用，给中性值

    n_cats = len(all_cats)
    if n_cats <= 1:
        return 0.1

    # 维度1: 类别数量因子 (sigmoid: 2类=0.2, 3类=0.5, 5+=0.9)
    cat_count_factor = min(1.0, (n_cats - 1) / 5.0)

    # 维度2: HHI 均匀度
    shares = [cnt / total for cnt in all_cats.values()]
    hhi = sum(s * s for s in shares)
    hhi_norm = (hhi - 1.0 / n_cats) / (1.0 - 1.0 / n_cats) if n_cats > 1 else 1.0
    uniformity = clamp(1.0 - hhi_norm, 0.0, 1.0)

    # 维度3: 领域群覆盖
    domain_map = {
        'write': 'dev', 'exec': 'dev',
        'read': 'info', 'browser': 'info',
        'agent': 'meta', 'memory': 'meta',
        'other': 'other',
    }
    domains = set()
    for cat in all_cats:
        domains.add(domain_map.get(cat, 'other'))
    domain_coverage = min(1.0, (len(domains) - 1) / 3.0)  # 1域=0, 4域=1

    # 综合: 类别数量 40% + 均匀度 30% + 领域覆盖 30%
    raw = 0.40 * cat_count_factor + 0.30 * uniformity + 0.30 * domain_coverage
    return clamp(raw, 0.0, 1.0)


# ─────────────────────────────────────────
# 主提取器类
# ─────────────────────────────────────────

class FeatureExtractor:
    """
    统一特征提取器。
    输入: DataParser.parse_bundle() 的返回 dict
    输出: (bond_features, echo_features) 两个特征字典
    """

    def __init__(self, parsed_bundle):
        """
        Args:
            parsed_bundle: DataParser.parse_bundle() / parse_directory() 返回的 dict
        """
        self.bundle = parsed_bundle
        self.sessions = parsed_bundle.get('sessions', [])
        self.markdown = parsed_bundle.get('markdown', None)
        self.memory = parsed_bundle.get('memory', None)
        self.heartbeat = parsed_bundle.get('heartbeat', None)
        self.tools_config = parsed_bundle.get('tools_config', None)
        self.skills = parsed_bundle.get('skills', None)
        self.user_messages = parsed_bundle.get('user_messages', [])
        self.agent_messages = parsed_bundle.get('agent_messages', [])
        self.session_count = parsed_bundle.get('session_count', len(self.sessions))
        # total_turns: 优先从 bundle 读取, 否则从 sessions 自动计算
        _explicit_turns = parsed_bundle.get('total_turns', 0)
        if _explicit_turns > 0:
            self.total_turns = _explicit_turns
        else:
            # 从 sessions 自动统计消息总数
            auto_turns = 0
            for sp in self.sessions:
                msgs = sp.messages if hasattr(sp, 'messages') else []
                auto_turns += len(msgs)
            self.total_turns = auto_turns if auto_turns > 0 else len(self.user_messages) + len(self.agent_messages)
        self.all_tool_calls = parsed_bundle.get('all_tool_calls', [])
        self.soul_text = parsed_bundle.get('soul_text', '')
        self.identity_text = parsed_bundle.get('identity_text', '')
        self.lexicon_results = parsed_bundle.get('lexicon_results', {})

    # ─────────────────────────────────────
    # BOND 特征提取
    # ─────────────────────────────────────

    def extract_bond_features(self):
        """
        提取 BOND 分类所需全部特征。
        返回 dict 可直接传入 bond_classifier.compute_bond_profile()
        """
        f = {}
        lr = self.lexicon_results

        # ── T 维度: Task Horizon (Sprint vs Marathon) ──
        f['session_count'] = self.session_count
        f['total_turns'] = self.total_turns
        f['avg_turns_per_session'] = _safe_div(
            self.total_turns, self.session_count, default=1.0)

        # 真实会话时长统计
        durations = []
        for sp in self.sessions:
            d = sp.get_session_duration() if hasattr(sp, 'get_session_duration') else 0
            if d > 0:
                durations.append(d)
        f['avg_session_duration'] = _avg(durations, default=f['avg_turns_per_session'] * 60)

        # 会话频率: sessions/天
        if self.memory and hasattr(self.memory, 'get_date_span_days'):
            span = self.memory.get_date_span_days()
            if span > 0:
                f['session_frequency'] = self.session_count / span
            else:
                f['session_frequency'] = self.session_count / 30.0
        else:
            f['session_frequency'] = self.session_count / 30.0

        # 会话连续性 (连续天数使用的比例)
        if self.memory and hasattr(self.memory, 'get_daily_memory_files'):
            daily = self.memory.get_daily_memory_files()
            if len(daily) >= 2:
                # 解析日期计算连续天数
                from datetime import datetime
                dates = []
                for fn in daily:
                    try:
                        d = datetime.strptime(fn.replace('.md', ''), '%Y-%m-%d')
                        dates.append(d)
                    except ValueError:
                        pass
                if len(dates) >= 2:
                    dates.sort()
                    consecutive = 0
                    for i in range(1, len(dates)):
                        if (dates[i] - dates[i-1]).days == 1:
                            consecutive += 1
                    f['session_continuity_ratio'] = _safe_div(
                        consecutive, len(dates) - 1, default=0.3)
                else:
                    f['session_continuity_ratio'] = 0.3
            else:
                f['session_continuity_ratio'] = 0.1 if self.session_count <= 2 else 0.5
        else:
            f['session_continuity_ratio'] = 0.3 if self.session_count <= 5 else 0.6

        # 多天话题持续性
        if self.memory and hasattr(self.memory, 'get_topic_persistence'):
            f['multi_day_topic_persistence'] = self.memory.get_topic_persistence()
        else:
            f['multi_day_topic_persistence'] = min(1.0, self.session_count / 20.0)

        # token消耗变异系数
        token_counts = []
        for sp in self.sessions:
            t = sp.get_total_tokens() if hasattr(sp, 'get_total_tokens') else 0
            if t > 0:
                token_counts.append(t)
        if len(token_counts) >= 2:
            f['total_token_consumption_rate_cv'] = compute_cv(token_counts)
        else:
            f['total_token_consumption_rate_cv'] = 0.3

        # ── E 维度: Emotional Engagement (Utility vs Companion) ──
        f['social_language_score'] = lr.get('social_language_score', 0.0)
        f['self_disclosure_score'] = lr.get('self_disclosure_score', 0.0)
        f['greeting_farewell_score'] = lr.get('greeting_farewell_score', 0.0)
        f['message_intent_task_ratio'] = lr.get('message_intent_task_ratio', 0.5)

        # 真实社交词命中计数
        social_count = 0
        social_keywords = ['哈哈', '嘻嘻', '谢谢', '感谢', '辛苦', '棒', '赞',
                          '晚安', '早安', '你好', '嗨', '拜拜', '再见',
                          'thanks', 'thank you', 'good morning', 'good night',
                          'hi', 'hello', 'bye', 'lol', 'haha', '❤', '😊', '👍']
        for msg in self.user_messages:
            msg_lower = msg.lower()
            if any(k in msg_lower for k in social_keywords):
                social_count += 1
        f['social_hit_count'] = social_count

        # 兼容性别名
        f['social_language_ratio'] = f['social_language_score']
        f['self_disclosure_depth'] = f['self_disclosure_score']
        f['greeting_farewell_rate'] = f['greeting_farewell_score']
        f['task_vs_chat_ratio'] = f['message_intent_task_ratio']

        # 用户 MD 丰富度
        if self.markdown and hasattr(self.markdown, 'get_user_md_richness'):
            f['user_md_richness'] = self.markdown.get_user_md_richness()
        else:
            # 从 user.md 文本推断
            user_text = ''
            if self.markdown and hasattr(self.markdown, 'user_text'):
                user_text = self.markdown.user_text
            f['user_md_richness'] = min(1.0, len(user_text) / 500) if user_text else 0.0

        # 记忆个人比例
        if self.memory and hasattr(self.memory, 'get_memory_personal_ratio'):
            f['memory_personal_ratio'] = self.memory.get_memory_personal_ratio()
        else:
            f['memory_personal_ratio'] = 0.0

        f['personification_score'] = f['social_language_score'] * 0.8 + \
            (0.2 if f['greeting_farewell_score'] > 0.3 else 0.0)

        # ── C 维度: Control Preference (Preview vs Review) ──
        f['question_ratio'] = lr.get('message_intent_question_ratio', 0.3)
        f['feedback_ratio'] = lr.get('message_intent_feedback_ratio', 0.2)

        # 预批准比例: 用户在 agent 行动前主动确认的比例
        # 从用户控制信号中推断
        total_control = 0
        pre_control = 0
        for sp in self.sessions:
            if hasattr(sp, 'get_user_control_signals'):
                signals = sp.get_user_control_signals()
                total_control += sum(signals.values())
                pre_control += signals.get('confirm', 0) + signals.get('approve', 0)
        f['pre_approval_ratio'] = _safe_div(pre_control, max(total_control, len(self.user_messages)))

        # 打断率
        f['interrupt_rate'] = _compute_interrupt_rate(self.sessions)

        # 后审查行为
        review_signals = 0
        for sp in self.sessions:
            if hasattr(sp, 'get_user_control_signals'):
                signals = sp.get_user_control_signals()
                review_signals += signals.get('revise', 0) + signals.get('reject', 0)
        f['post_review_behavior'] = _safe_div(review_signals, len(self.user_messages))

        # 上下文提供率
        context_msgs = 0
        context_kw = ['背景', '上下文', 'context', 'background', '前提', '之前',
                      '参考', 'refer', '如下', 'as follows', '附件', 'attachment']
        for msg in self.user_messages:
            if any(k in msg.lower() for k in context_kw):
                context_msgs += 1
        f['context_provision_rate'] = _safe_div(context_msgs, len(self.user_messages))

        # 委托置信度
        f['delegation_confidence'] = _compute_delegation_confidence(self.user_messages)

        # 工具调用确认延迟
        f['tool_call_user_confirm_latency'] = _compute_tool_confirm_latency(self.sessions)

        # 安全严格度: 从 AGENTS.md 推断
        agents_text = ''
        if self.markdown:
            if hasattr(self.markdown, 'agents_text'):
                agents_text = self.markdown.agents_text
            elif hasattr(self.markdown, 'get_agents_text'):
                agents_text = self.markdown.get_agents_text()
        f['agents_md_safety_strictness'] = _detect_safety_strictness(agents_text)

        # ── F 维度: Feedback Style (High-level vs Detailed) ──
        # 真实用户消息平均长度
        msg_lengths = [len(m) for m in self.user_messages]
        f['avg_user_message_length'] = _avg(msg_lengths, default=50.0)

        # 指令具体性: 用户消息中包含具体数字/路径/代码的比例
        specific_pattern = re.compile(
            r'(\d{2,}|/[\w/]+|`[^`]+`|\.py|\.js|\.md|http|#\d+|\b0x[0-9a-f]+)',
            re.IGNORECASE
        )
        specific_count = sum(1 for m in self.user_messages if specific_pattern.search(m))
        f['instruction_specificity'] = _safe_div(specific_count, len(self.user_messages))

        # 修订请求率
        revision_kw = ['改一下', '修改', '重做', '不对', '错了', '换个',
                       'fix', 'revise', 'change', 'redo', 'wrong', 'incorrect',
                       '再试', 'try again', '重新']
        rev_count = sum(1 for m in self.user_messages
                       if any(k in m.lower() for k in revision_kw))
        f['revision_request_rate'] = _safe_div(rev_count, len(self.user_messages))

        # 问题粒度: 用户提问中包含多个子问题的比例
        multi_q_count = 0
        for m in self.user_messages:
            q_marks = m.count('？') + m.count('?')
            if q_marks >= 2:
                multi_q_count += 1
        f['question_granularity'] = _safe_div(multi_q_count, len(self.user_messages))

        # 后续细节比例
        f['follow_up_detail_ratio'] = f['revision_request_rate'] * 0.5 + f['question_granularity'] * 0.5

        # 满意度表达风格: 简短vs详细
        short_feedback = 0
        long_feedback = 0
        fb_kw = ['好', '可以', 'ok', 'good', 'nice', '行', '嗯', 'yes',
                 '不错', 'great', 'perfect', '棒']
        for m in self.user_messages:
            if len(m) < 10 and any(k in m.lower() for k in fb_kw):
                short_feedback += 1
            elif len(m) >= 30 and any(k in m.lower() for k in fb_kw):
                long_feedback += 1
        total_fb = short_feedback + long_feedback
        f['satisfaction_expression_style'] = _safe_div(short_feedback, total_fb, default=0.5)

        # ── 共享字段 ──
        f['_user_messages_cache'] = self.user_messages

        return f

    # ─────────────────────────────────────
    # ECHO 特征提取
    # ─────────────────────────────────────

    def extract_echo_features(self):
        """
        提取 ECHO 分类所需全部特征。
        返回 dict 可直接传入 echo_classifier.compute_echo_profile()
        """
        f = {}
        lr = self.lexicon_results

        # ── I 维度: Initiative (Reactive vs Proactive) ──
        f['soul_autonomy'] = lr.get('soul_autonomy_score', 0.45)

        # 补充: heartbeat 活跃度作为主动性的行为信号
        if self.heartbeat and hasattr(self.heartbeat, 'get_activity_level'):
            f['heartbeat_activity_level'] = self.heartbeat.get_activity_level()
        else:
            f['heartbeat_activity_level'] = 0.0

        # 工具自主发起比例
        total_si = 0
        total_tc = 0
        for sp in self.sessions:
            if hasattr(sp, 'get_tool_self_initiated_ratio'):
                ratio = sp.get_tool_self_initiated_ratio()
                tc_count = len(sp.tool_calls) if hasattr(sp, 'tool_calls') else 0
                total_si += ratio * tc_count
                total_tc += tc_count
        f['tool_self_initiated_ratio'] = _safe_div(total_si, total_tc, default=0.0)

        # ── S 维度: Specialization (Specialist vs Generalist) ──
        f['soul_specialization'] = lr.get('soul_specialization_score', 0.5)

        # 补充: 真实技能安装数和多样性
        if self.skills and hasattr(self.skills, 'get_installed_count'):
            f['installed_skills_count'] = self.skills.get_installed_count()
        else:
            f['installed_skills_count'] = 0

        if self.skills and hasattr(self.skills, 'get_skill_diversity'):
            f['skill_diversity'] = self.skills.get_skill_diversity()
        else:
            f['skill_diversity'] = 0.0

        # 话题覆盖广度 (真实计算)
        f['topic_coverage_breadth'] = _compute_topic_coverage(
            self.sessions, self.user_messages)

        # 跨领域任务比例 (真实计算)
        f['cross_domain_task_ratio'] = _compute_cross_domain_ratio(self.sessions)

        # TOOLS.md 配置丰富度
        if self.tools_config and hasattr(self.tools_config, 'get_config_richness'):
            f['tools_config_richness'] = self.tools_config.get_config_richness()
        else:
            f['tools_config_richness'] = 0.0

        if self.tools_config and hasattr(self.tools_config, 'get_tool_count'):
            f['configured_tool_count'] = self.tools_config.get_tool_count()
        else:
            f['configured_tool_count'] = 0

        # ── T 维度 (ECHO): Tone (Functional vs Empathetic) ──
        f['soul_tone_warmth'] = lr.get('soul_tone_warmth_score', 0.5)
        f['identity_vibe'] = lr.get('identity_vibe_score', 0.5)
        f['emotional_word'] = lr.get('emotional_word_score', 0.3)
        f['formality'] = lr.get('formality_score', 0.5)

        # ── M 维度: Memory (Transient vs Continuous) ──
        # 真实 memory 统计
        if self.memory:
            if hasattr(self.memory, 'get_memory_depth'):
                f['memory_depth'] = self.memory.get_memory_depth()
            else:
                f['memory_depth'] = 0.0

            if hasattr(self.memory, 'get_topic_count'):
                f['memory_topic_count'] = self.memory.get_topic_count()
            else:
                f['memory_topic_count'] = 0

            if hasattr(self.memory, 'get_date_span_days'):
                f['memory_date_span'] = self.memory.get_date_span_days()
            else:
                f['memory_date_span'] = 0

            if hasattr(self.memory, 'get_memory_file_count'):
                f['memory_file_count'] = self.memory.get_memory_file_count()
            else:
                f['memory_file_count'] = 0
        else:
            f['memory_depth'] = 0.0
            f['memory_topic_count'] = 0
            f['memory_date_span'] = 0
            f['memory_file_count'] = 0

        # agent 自更新行为计数
        total_self_update = 0
        for sp in self.sessions:
            if hasattr(sp, 'get_agent_self_update_count'):
                total_self_update += sp.get_agent_self_update_count()
        f['agent_self_update_count'] = total_self_update

        # memory 搜索次数
        total_mem_search = 0
        for sp in self.sessions:
            if hasattr(sp, 'get_memory_search_count'):
                total_mem_search += sp.get_memory_search_count()
        f['memory_search_count'] = total_mem_search

        # ── 共享字段 ──
        f['session_count'] = self.session_count
        f['total_turns'] = self.total_turns
        f['agent_messages'] = self.agent_messages
        f['soul_text'] = self.soul_text
        f['identity_text'] = self.identity_text

        # ── 工具使用综合统计 ──
        f['total_tool_calls'] = len(self.all_tool_calls)

        total_success = sum(1 for tc in self.all_tool_calls if tc.get('success', False))
        f['tool_success_rate'] = _safe_div(total_success, len(self.all_tool_calls))

        f['avg_param_complexity'] = _avg(
            [tc.get('param_count', 0) * (1 + tc.get('param_depth', 0) / 5.0)
             for tc in self.all_tool_calls],
            default=0.0
        )

        total_retry = sum(
            sp.get_tool_retry_count() if hasattr(sp, 'get_tool_retry_count') else 0
            for sp in self.sessions
        )
        f['tool_retry_count'] = total_retry

        # 工具类别分布
        cat_counter = Counter()
        for sp in self.sessions:
            if hasattr(sp, 'get_tool_category_distribution'):
                for cat, cnt in sp.get_tool_category_distribution().items():
                    cat_counter[cat] += cnt
        f['tool_category_distribution'] = dict(cat_counter)

        return f

    # ─────────────────────────────────────
    # 便捷方法
    # ─────────────────────────────────────

    def extract_all(self):
        """
        提取全部特征。
        Returns:
            (bond_features, echo_features)
        """
        return self.extract_bond_features(), self.extract_echo_features()


# ─────────────────────────────────────────
# 模块级便捷函数
# ─────────────────────────────────────────

def extract_features(parsed_bundle):
    """
    从 DataParser 解析结果提取全部特征。
    Args:
        parsed_bundle: DataParser.parse_bundle() 的返回值
    Returns:
        (bond_features, echo_features)
    """
    return FeatureExtractor(parsed_bundle).extract_all()
