# -*- coding: utf-8 -*-
"""
BOND Profile 分类器 — 人类用户 16 类型
=========================================

四维度模型:
  T (Task Horizon)         : Sprint(S) < 0.5  vs  Marathon(M) >= 0.5
  E (Emotional Engagement) : Utility(U) < 0.5  vs  Companion(C) >= 0.5
  C (Control Preference)   : Preview(P) < 0.5  vs  Review(R) >= 0.5
  F (Feedback Style)       : High-level(H) < 0.5  vs  Detailed(D) >= 0.5

核心算法创新: E 维度 v2 非对称基线优化
  - 增强弱伴侣信号 (social/disclosure/greeting)  via x^0.6
  - 抑制强基线任务信号 (task_ratio)              via x^1.5
  - 先验基线 0.20 (OpenClaw 用户默认偏工具模式)
  - 触发阈值 + 最少命中数 bonus 机制

纯 Python stdlib, 零外部依赖 (仅 math, re).
"""

import math
import re
from typing import Dict, List, Optional, Tuple

try:
    from .utils import (
    sigmoid_normalize,
    clamp,
    classify_dimension,
    compute_shannon_diversity,
    compute_hhi,
    compute_cv,
    tokenize_mixed,
    )
except ImportError:
    from utils import (
    sigmoid_normalize,
    clamp,
    classify_dimension,
    compute_shannon_diversity,
    compute_hhi,
    compute_cv,
    tokenize_mixed,
    )
try:
    from .type_definitions import BOND_TYPES, BOND_DIM_LABELS
except ImportError:
    from type_definitions import BOND_TYPES, BOND_DIM_LABELS
try:
    from .all_lexicons import (
    SocialLanguageLexicon,
    MessageIntentLexicon,
    SelfDisclosureLexicon,
    GreetingFarewellLexicon,
    )
except ImportError:
    from all_lexicons import (
    SocialLanguageLexicon,
    MessageIntentLexicon,
    SelfDisclosureLexicon,
    GreetingFarewellLexicon,
    )


# ===================================================================
# 维度编码映射
# ===================================================================

# dim_key -> (pole_low_letter, pole_high_letter)
BOND_DIMS: Dict[str, Tuple[str, str]] = {
    "T": ("S", "M"),   # Sprint / Marathon
    "E": ("U", "C"),   # Utility / Companion
    "C": ("P", "R"),   # Preview / Review
    "F": ("H", "D"),   # High-level / Detailed
}

BOND_DIM_NAMES: Dict[str, str] = {
    "T": "Task Horizon",
    "E": "Emotional Engagement",
    "C": "Control Preference",
    "F": "Feedback Style",
}


# ===================================================================
# E 维度 v2 — 非对称基线优化核心参数与函数
# ===================================================================
# 这是本分类器的核心算法创新点.
# OpenClaw 生态中, 绝大多数用户默认以任务/工具模式与 Agent 交互,
# 导致 E 维度原始信号严重偏向 Utility 极.
# v2 方案通过非对称变换解决此问题:
#   - 增强 (amplify):  对伴侣型弱信号施加 x^0.6 幂次放大
#   - 抑制 (dampen):   对基线任务信号施加 x^1.5 幂次压缩
#   - 噪声地板:        低于 0.10 的信号视为噪声, 半衰处理
#   - 先验基线:        所有用户起始 E=0.20, 避免零启动
#   - 触发加分:        当社交原始信号 > 阈值且命中词数 >= 最小数时额外加分

_E_AMPLIFY_POWER: float = 0.6       # 增强幂 (x^0.6 放大弱信号)
_E_DAMPEN_POWER: float = 1.5        # 抑制幂 (x^1.5 压缩基线信号)
_E_NOISE_FLOOR: float = 0.10        # 低于此值视为噪声, 半衰
_E_PRIOR_BASELINE: float = 0.20     # 先验基线 (OpenClaw 用户默认任务模式)
_E_TRIGGER_THRESHOLD: float = 0.30  # 原始信号触发阈值
_E_TRIGGER_MIN_COUNT: int = 2       # 最少命中词数
_E_TRIGGER_BONUS: float = 0.08      # 触发加分


def _e_amplify(x: float, power: float = _E_AMPLIFY_POWER) -> float:
    """增强变换: 放大弱伴侣信号.

    - x <= 0        -> 0.0
    - x < NOISE_FLOOR -> x * 0.5 (噪声半衰)
    - otherwise     -> min(1.0, x^power)
    """
    if x <= 0.0:
        return 0.0
    if x < _E_NOISE_FLOOR:
        return x * 0.5
    return min(1.0, x ** power)


def _e_dampen(x: float, power: float = _E_DAMPEN_POWER) -> float:
    """抑制变换: 压缩基线任务信号.

    - x <= 0 -> 0.0
    - otherwise -> min(1.0, x^power)
    """
    if x <= 0.0:
        return 0.0
    return min(1.0, x ** power)


# ===================================================================
# 词法分析器实例 (模块级单例, 避免重复实例化)
# ===================================================================

_social_lex = SocialLanguageLexicon()
_intent_lex = MessageIntentLexicon()
_disclosure_lex = SelfDisclosureLexicon()
_greeting_lex = GreetingFarewellLexicon()


# ===================================================================
# T 维度计算: Task Horizon
# ===================================================================

def _compute_T(
    session_count: int,
    total_turns: int,
    avg_turns_per_session: float,
) -> float:
    """T (Task Horizon): 0 = Sprint, 1 = Marathon.

    信号来源:
      - session_count:        多会话 = 长期 = Marathon
      - total_turns:          多轮 = 长期
      - avg_turns_per_session: 每会话平均轮数

    融合公式:
      raw = session_count_factor * 0.4
          + total_turns_factor  * 0.3
          + avg_turns_factor    * 0.3
      T = sigmoid_normalize(raw)
    """
    # session_count: 1 会话 -> 短期, 5+ 会话 -> 长期
    sc_factor = sigmoid_normalize(float(session_count), mu=3.0, sigma=2.0)

    # total_turns: 归一化, 10 轮是中位, 50+ 偏长期
    tt_factor = sigmoid_normalize(float(total_turns), mu=20.0, sigma=15.0)

    # avg_turns_per_session: 3 轮是短, 15+ 是深度
    at_factor = sigmoid_normalize(avg_turns_per_session, mu=8.0, sigma=5.0)

    raw = sc_factor * 0.4 + tt_factor * 0.3 + at_factor * 0.3
    return clamp(raw)


# ===================================================================
# E 维度计算: Emotional Engagement (v2 非对称基线优化)
# ===================================================================

def _compute_E(
    user_messages: List[str],
    lexicon_results: Optional[Dict] = None,
) -> float:
    """E (Emotional Engagement): 0 = Utility, 1 = Companion.

    v2 非对称基线优化算法:

    信号来源 (全部来自用户消息):
      amplify 增强信号 (x^0.6):
        - social_language_score  : SocialLanguageLexicon
        - self_disclosure_score  : SelfDisclosureLexicon
        - greeting_farewell_score: GreetingFarewellLexicon
      dampen 抑制信号 (x^1.5):
        - message_intent_task_ratio: MessageIntentLexicon 的 task ratio

    融合:
      E_raw = avg(amplified_signals) * (1 - dampened_task_ratio)
      if 触发条件满足: E_raw += bonus
      E = clamp(prior_baseline + E_raw, 0, 1)
    """
    if not user_messages:
        return _E_PRIOR_BASELINE

    # ---- 从 lexicon_results 取值或现场计算 ----
    if lexicon_results and "social_language_score" in lexicon_results:
        raw_social = float(lexicon_results["social_language_score"])
    else:
        social_scores = [_social_lex.score(m) for m in user_messages]
        raw_social = sum(social_scores) / len(social_scores) if social_scores else 0.0

    if lexicon_results and "self_disclosure_score" in lexicon_results:
        raw_disclosure = float(lexicon_results["self_disclosure_score"])
    else:
        disc_scores = [_disclosure_lex.score(m) for m in user_messages]
        raw_disclosure = sum(disc_scores) / len(disc_scores) if disc_scores else 0.0

    if lexicon_results and "greeting_farewell_score" in lexicon_results:
        raw_greeting = float(lexicon_results["greeting_farewell_score"])
    else:
        greet_scores = [_greeting_lex.score(m) for m in user_messages]
        raw_greeting = sum(greet_scores) / len(greet_scores) if greet_scores else 0.0

    if lexicon_results and "message_intent_task_ratio" in lexicon_results:
        raw_task_ratio = float(lexicon_results["message_intent_task_ratio"])
    else:
        task_count = 0
        for m in user_messages:
            intent = _intent_lex.compute_intent(m)
            if max(intent, key=intent.get) == "task":
                task_count += 1
        raw_task_ratio = task_count / len(user_messages) if user_messages else 1.0

    # ---- 社交命中计数 (用于触发判断) ----
    if lexicon_results and "social_hit_count" in lexicon_results:
        social_hit_count = int(lexicon_results["social_hit_count"])
    else:
        social_hit_count = _count_social_hits(user_messages)

    # ---- 非对称变换 ----
    amp_social = _e_amplify(raw_social)
    amp_disclosure = _e_amplify(raw_disclosure)
    amp_greeting = _e_amplify(raw_greeting)
    damp_task = _e_dampen(raw_task_ratio)

    # ---- 融合 ----
    amplified_avg = (amp_social + amp_disclosure + amp_greeting) / 3.0
    e_raw = amplified_avg * (1.0 - damp_task)

    # ---- 触发加分 ----
    if raw_social > _E_TRIGGER_THRESHOLD and social_hit_count >= _E_TRIGGER_MIN_COUNT:
        e_raw += _E_TRIGGER_BONUS

    # ---- 先验基线 + 原始信号 ----
    e_final = _E_PRIOR_BASELINE + e_raw
    return clamp(e_final)


def _count_social_hits(user_messages: List[str]) -> int:
    """统计用户消息中社交关键词的总命中次数.

    遍历所有用户消息, 对每条消息的 token 进行社交强关键词匹配,
    返回全局累计命中数.
    """
    total_hits = 0
    for msg in user_messages:
        tokens = tokenize_mixed(msg)
        for tok in tokens:
            if tok in _social_lex.social_strong:
                total_hits += 1
    return total_hits


# ===================================================================
# C 维度计算: Control Preference
# ===================================================================

# 编译一次, 复用
_PAT_QUESTION = re.compile(
    r"(?:请问|怎么|如何|能不能|可以吗|是不是|为什么|什么时候|哪个|哪些"
    r"|\?|？"
    r"|\bhow\b|\bwhat\b|\bwhy\b|\bwhich\b|\bcan you\b|\bcould you\b"
    r"|\bis it\b|\bdo you\b)",
    re.IGNORECASE,
)

_PAT_COMMAND = re.compile(
    r"(?:帮我|请|麻烦|给我|替我|把.*改成|写一个|做一个|生成|创建|执行|运行"
    r"|\bplease\b|\bhelp me\b|\bwrite\b|\bcreate\b|\bgenerate\b"
    r"|\brun\b|\bexecute\b|\bdo\b)",
    re.IGNORECASE,
)

_PAT_FEEDBACK = re.compile(
    r"(?:不错|很好|很棒|可以|没问题|完美|不行|不对|不好|差|重新|再来"
    r"|做得好|还行|满意|改一下|修改|有问题"
    r"|\bgood\b|\bbad\b|\bperfect\b|\bwrong\b|\bredo\b|\bfix\b"
    r"|\bgreat\b|\bnice\b|\bnot right\b)",
    re.IGNORECASE,
)

_PAT_REVIEW = re.compile(
    r"(?:检查|review|看看|check|验证|verify|确认一下|核实"
    r"|\breview\b|\bcheck\b|\bverify\b|\bvalidate\b)",
    re.IGNORECASE,
)


def _compute_C(
    user_messages: List[str],
    lexicon_results: Optional[Dict] = None,
) -> float:
    """C (Control Preference): 0 = Preview(事前预审), 1 = Review(事后复盘).

    信号来源:
      - 用户消息中 命令/提问 vs 评价/反馈 的比例
      - MessageIntentLexicon 的 question_ratio vs feedback_ratio

    Preview 用户: 多提问/命令, 事前指导 -> 低分
    Review 用户:  多反馈/评价, 事后审查 -> 高分
    """
    if not user_messages:
        return 0.5

    # ---- 从 lexicon_results 取值或现场计算 ----
    if lexicon_results and "question_ratio" in lexicon_results:
        question_ratio = float(lexicon_results["question_ratio"])
        feedback_ratio = float(lexicon_results.get("feedback_ratio", 0.0))
    else:
        question_count = 0.0
        feedback_count = 0.0
        for m in user_messages:
            intent = _intent_lex.compute_intent(m)
            question_count += intent.get("task", 0.0) + intent.get("chat", 0.0)
            feedback_count += intent.get("feedback", 0.0)
        total_if = question_count + feedback_count
        if total_if > 0:
            question_ratio = question_count / total_if
            feedback_ratio = feedback_count / total_if
        else:
            question_ratio = 0.5
            feedback_ratio = 0.5

    # ---- 正则模式匹配 ----
    command_hits = 0
    question_hits = 0
    feedback_hits = 0
    review_hits = 0

    for m in user_messages:
        if _PAT_COMMAND.search(m):
            command_hits += 1
        if _PAT_QUESTION.search(m):
            question_hits += 1
        if _PAT_FEEDBACK.search(m):
            feedback_hits += 1
        if _PAT_REVIEW.search(m):
            review_hits += 1

    n = len(user_messages)
    command_ratio = command_hits / n
    question_hit_ratio = question_hits / n
    feedback_hit_ratio = feedback_hits / n
    review_hit_ratio = review_hits / n

    # Preview 信号: 命令 + 提问 (事前控制)
    preview_signal = (command_ratio * 0.4 + question_hit_ratio * 0.3
                      + question_ratio * 0.3)

    # Review 信号: 反馈 + 评价 + 复盘 (事后审查)
    review_signal = (feedback_hit_ratio * 0.3 + review_hit_ratio * 0.3
                     + feedback_ratio * 0.4)

    # C = review_signal / (preview + review) 映射到 [0,1]
    total_signal = preview_signal + review_signal
    if total_signal < 0.01:
        return 0.5

    raw_c = review_signal / total_signal
    return clamp(raw_c)


# ===================================================================
# F 维度计算: Feedback Style
# ===================================================================

_PAT_SPECIFIC = re.compile(
    r"(?:\d+|```|(?:用|in\s+(?:Python|JS|Go|Java|Rust|C\+\+|TypeScript))"
    r"|(?:不要|avoid|必须|must|至少|至多|不超过|限制)"
    r"|(?:比如|e\.g\.|例如|for example)"
    r"|(?:第\d|第[一二三四五六七八九十]|step\s*\d)"
    r"|(?:格式|format|输出|output))",
    re.IGNORECASE,
)

_PAT_CONTEXT = re.compile(
    r"(?:背景|context|因为|because|之前|之所以|原因是|由于"
    r"|我这边|the thing is|here's the deal)",
    re.IGNORECASE,
)


def _compute_F(user_messages: List[str]) -> float:
    """F (Feedback Style): 0 = High-level(意图概括), 1 = Detailed(精确具体).

    信号来源:
      - 用户消息平均长度
      - 词汇多样性 (unique/total ratio)
      - 具体指标关键词密度
    """
    if not user_messages:
        return 0.5

    n = len(user_messages)

    # ---- 消息平均长度 ----
    lengths = [len(m) for m in user_messages]
    avg_len = sum(lengths) / n
    # 归一化: 50 字以下偏简短, 200+ 字偏详细
    len_score = sigmoid_normalize(avg_len, mu=100.0, sigma=60.0)

    # ---- 词汇多样性 ----
    all_tokens: List[str] = []
    for m in user_messages:
        all_tokens.extend(tokenize_mixed(m))

    if len(all_tokens) > 0:
        unique_count = len(set(all_tokens))
        total_count = len(all_tokens)
        diversity_ratio = unique_count / total_count
    else:
        diversity_ratio = 0.5

    # 多样性高 -> 更具体详细
    diversity_score = sigmoid_normalize(diversity_ratio, mu=0.5, sigma=0.2)

    # ---- 具体指标关键词密度 ----
    specific_count = 0
    context_count = 0
    for m in user_messages:
        hits = _PAT_SPECIFIC.findall(m)
        if len(hits) >= 2:
            specific_count += 1
        if _PAT_CONTEXT.search(m):
            context_count += 1

    specificity_score = specific_count / n
    context_score = context_count / n

    # ---- 融合 ----
    f_raw = (
        len_score * 0.30
        + diversity_score * 0.20
        + specificity_score * 0.30
        + context_score * 0.20
    )
    return clamp(f_raw)


# ===================================================================
# 维度 -> 类型编码 辅助
# ===================================================================

def _score_to_letter(dim_key: str, score: float) -> str:
    """将维度得分映射为类型字母.

    score < 0.5 -> 第一极 (S/U/P/H)
    score >= 0.5 -> 第二极 (M/C/R/D)
    """
    low, high = BOND_DIMS[dim_key]
    return high if score >= 0.5 else low


# ===================================================================
# 特征提取器 (兼容 profiler.py 旧管线)
# ===================================================================

class BONDFeatureExtractor:
    """从 OpenClaw 数据中提取 BOND 四维度的原始特征.

    .. deprecated::
        此类为旧版兼容保留。新代码请使用 feature_extractor.FeatureExtractor,
        它提供更完整的特征提取 (BOND + ECHO) 并与 DataParser 对齐。

    旧调用方式:
        bond_extractor = BONDFeatureExtractor()
        bond_features = bond_extractor.extract_from_sessions(sessions)
        md_features = bond_extractor.extract_from_markdown(md, mem)

    推荐替代:
        from feature_extractor import FeatureExtractor
        extractor = FeatureExtractor(parsed_bundle)
        bond_features, echo_features = extractor.extract_all()
    """

    def __init__(self) -> None:
        self._social_lex = _social_lex
        self._intent_lex = _intent_lex
        self._disclosure_lex = _disclosure_lex
        self._greeting_lex = _greeting_lex

    # ------------------------------------------------------------------
    # extract_from_sessions
    # ------------------------------------------------------------------
    def extract_from_sessions(self, sessions) -> Dict[str, float]:
        """从多个 SessionParser 实例提取聚合特征."""
        features: Dict = {}

        # ---- 收集全部用户文本 ----
        all_user_texts: List[str] = []
        for s in sessions:
            all_user_texts.extend(
                [m["content"] for m in s.get_user_messages()]
            )

        turns_list = [s.get_user_message_count() for s in sessions]

        # ---- T 维度特征 ----
        features["session_count"] = float(len(sessions))
        features["total_turns"] = float(sum(turns_list))
        features["avg_turns_per_session"] = (
            sum(turns_list) / len(turns_list) if turns_list else 0.0
        )

        # ---- E 维度特征 (存储原始子信号供后续使用) ----
        if all_user_texts:
            social_scores = [
                self._social_lex.score(t) for t in all_user_texts
            ]
            features["social_language_score"] = (
                sum(social_scores) / len(social_scores)
            )

            disc_scores = [
                self._disclosure_lex.score(t) for t in all_user_texts
            ]
            features["self_disclosure_score"] = (
                sum(disc_scores) / len(disc_scores)
            )

            greet_scores = [
                self._greeting_lex.score(t) for t in all_user_texts
            ]
            features["greeting_farewell_score"] = (
                sum(greet_scores) / len(greet_scores)
            )

            # task ratio
            task_count = 0
            for t in all_user_texts:
                if self._intent_lex.compute_primary_intent(t) == "task":
                    task_count += 1
            features["message_intent_task_ratio"] = (
                task_count / len(all_user_texts)
            )

            # 社交命中计数
            features["social_hit_count"] = float(
                _count_social_hits(all_user_texts)
            )

            # intent 分布 (供 C 维度使用)
            q_total = 0.0
            fb_total = 0.0
            for t in all_user_texts:
                intent = self._intent_lex.compute_intent(t)
                q_total += intent.get("task", 0.0) + intent.get("chat", 0.0)
                fb_total += intent.get("feedback", 0.0)
            qf_sum = q_total + fb_total
            if qf_sum > 0:
                features["question_ratio"] = q_total / qf_sum
                features["feedback_ratio"] = fb_total / qf_sum
            else:
                features["question_ratio"] = 0.5
                features["feedback_ratio"] = 0.5
        else:
            features["social_language_score"] = 0.0
            features["self_disclosure_score"] = 0.0
            features["greeting_farewell_score"] = 0.0
            features["message_intent_task_ratio"] = 1.0
            features["social_hit_count"] = 0.0
            features["question_ratio"] = 0.5
            features["feedback_ratio"] = 0.5

        # 缓存用户文本 (供维度计算器使用)
        features["_user_messages_cache"] = all_user_texts

        return features

    # ------------------------------------------------------------------
    # extract_from_markdown
    # ------------------------------------------------------------------
    def extract_from_markdown(self, md, mem) -> Dict[str, float]:
        """从 MarkdownAnalyzer 和 MemoryAnalyzer 提取补充特征.

        .. deprecated:: 使用 FeatureExtractor.extract_bond_features() 替代.
        """
        # 安全严格度: 优先调用 get_agents_safety_strictness,
        # 不存在时 fallback 到 agents_text 的关键词检测
        safety = 2.5
        if hasattr(md, 'get_agents_safety_strictness'):
            safety = md.get_agents_safety_strictness() * 5
        elif hasattr(md, 'agents_text'):
            # 简单关键词检测
            text = (md.agents_text or '').lower()
            high_kw = ['safety', 'filter', 'restrict', 'never', 'must not']
            safety = 2.5 + sum(0.5 for k in high_kw if k in text)
            safety = min(5.0, safety)

        return {
            "user_md_richness": float(md.get_user_md_richness()),
            "memory_personal_ratio": mem.get_memory_personal_ratio(),
            "multi_day_topic_persistence": mem.get_topic_persistence(),
            "agents_md_safety_strictness": safety,
        }


# ===================================================================
# 维度得分计算 — 从特征字典 (兼容旧管线)
# ===================================================================

def _compute_T_from_features(features: Dict) -> float:
    """从特征字典计算 T 维度得分."""
    return _compute_T(
        session_count=int(features.get("session_count", 1)),
        total_turns=int(features.get("total_turns", 1)),
        avg_turns_per_session=float(
            features.get("avg_turns_per_session", 1.0)
        ),
    )


def _compute_E_from_features(features: Dict) -> float:
    """从特征字典计算 E 维度得分."""
    user_messages = features.get("_user_messages_cache", [])
    lexicon_results = {
        "social_language_score": features.get("social_language_score"),
        "self_disclosure_score": features.get("self_disclosure_score"),
        "greeting_farewell_score": features.get("greeting_farewell_score"),
        "message_intent_task_ratio": features.get(
            "message_intent_task_ratio"
        ),
        "social_hit_count": features.get("social_hit_count"),
    }
    # 如果 lexicon 子信号都存在, 优先用预计算值
    if all(v is not None for v in lexicon_results.values()):
        return _compute_E(user_messages, lexicon_results)
    return _compute_E(user_messages, None)


def _compute_C_from_features(features: Dict) -> float:
    """从特征字典计算 C 维度得分."""
    user_messages = features.get("_user_messages_cache", [])
    lexicon_results = {}
    if "question_ratio" in features:
        lexicon_results["question_ratio"] = features["question_ratio"]
    if "feedback_ratio" in features:
        lexicon_results["feedback_ratio"] = features["feedback_ratio"]
    return _compute_C(user_messages, lexicon_results if lexicon_results else None)


def _compute_F_from_features(features: Dict) -> float:
    """从特征字典计算 F 维度得分."""
    user_messages = features.get("_user_messages_cache", [])
    return _compute_F(user_messages)


# 维度 -> 计算函数映射 (供 EMA tracker 等使用)
_DIM_SCORE_FUNCS = {
    "T": _compute_T_from_features,
    "E": _compute_E_from_features,
    "C": _compute_C_from_features,
    "F": _compute_F_from_features,
}


# ===================================================================
# compute_bond_profile — 兼容 profiler.py 旧管线入口
# ===================================================================

def compute_bond_profile(features: Dict[str, float]) -> Dict:
    """计算完整的 BOND Profile.

    兼容 profiler.py 中的调用:
        bond_profile = compute_bond_profile(bond_features)

    返回:
        {
            'type_code': str,         # e.g. 'SUPH'
            'type_name_zh': str,      # e.g. '指挥官'
            'type_name_en': str,      # e.g. 'Sprint-Utility-Preview-High-level'
            'confidence': float,      # [0, 1]
            'dimensions': {
                'T': {'score', 'pole', 'pole_name', 'confidence',
                       'probability_B', 'dim_name'},
                'E': {...}, 'C': {...}, 'F': {...},
            }
        }
    """
    type_code = ""
    total_conf = 0.0
    dimensions: Dict[str, Dict] = {}

    for dim_key in ["T", "E", "C", "F"]:
        score = _DIM_SCORE_FUNCS[dim_key](features)
        pole_label, conf, prob_b = classify_dimension(score)
        letter = (
            BOND_DIMS[dim_key][1]
            if pole_label == "B"
            else BOND_DIMS[dim_key][0]
        )
        type_code += letter
        total_conf += conf
        dimensions[dim_key] = {
            "score": round(score, 4),
            "pole": letter,
            "pole_name": letter,
            "confidence": round(conf, 4),
            "probability_B": round(prob_b, 4),
            "dim_name": BOND_DIM_NAMES[dim_key],
        }

    type_info = BOND_TYPES.get(type_code)
    if type_info:
        zh_name = type_info["name"]
        en_name = type_info.get("dims", type_code)
    else:
        zh_name = "未知类型"
        en_name = "Unknown"

    return {
        "type_code": type_code,
        "type_name_zh": zh_name,
        "type_name_en": en_name,
        "confidence": round(total_conf / 4.0, 4),
        "dimensions": dimensions,
    }


# ===================================================================
# 冷启动策略
# ===================================================================

def apply_cold_start_adjustments(
    features: Dict[str, float],
    md=None,
    session_count: int = 0,
) -> Dict[str, float]:
    """冷启动补偿: 当数据量不足时基于先验知识调整特征.

    调整策略:
      - USER.md 丰富 (>200 字) -> 提升 E 方向的 social 信号
      - 长消息 (avg > 150 字) -> 提升 F 方向
      - 会话数少但 turns 多 -> 提升 T 方向
    """
    f = dict(features)
    # 保持 _user_messages_cache 引用
    if "_user_messages_cache" in features:
        f["_user_messages_cache"] = features["_user_messages_cache"]

    if session_count < 3:
        # USER.md 丰富 -> 偏 Companion (提升社交信号)
        if md is not None and hasattr(md, "get_user_md_richness"):
            richness = md.get_user_md_richness()
            if richness > 200:
                current_social = f.get("social_language_score", 0.0)
                if isinstance(current_social, (int, float)):
                    f["social_language_score"] = min(1.0, current_social + 0.10)
                current_disc = f.get("self_disclosure_score", 0.0)
                if isinstance(current_disc, (int, float)):
                    f["self_disclosure_score"] = min(1.0, current_disc + 0.08)

        # 长消息 -> 偏 Detailed
        user_msgs = f.get("_user_messages_cache", [])
        if user_msgs and isinstance(user_msgs, list) and len(user_msgs) > 0:
            avg_len = sum(len(m) for m in user_msgs) / len(user_msgs)
            if avg_len > 150:
                f["_cold_start_f_boost"] = 0.10

        # 会话数少但 turns 多 -> 偏 Marathon
        total_turns = f.get("total_turns", 0)
        if isinstance(total_turns, (int, float)) and total_turns > 15 and session_count <= 2:
            current_sc = f.get("session_count", 1.0)
            if isinstance(current_sc, (int, float)):
                f["session_count"] = max(current_sc, 3.0)

    return f


# ===================================================================
# classify() — 新版主入口
# ===================================================================

def classify(
    user_messages: List[str],
    agent_messages: List[str],
    session_count: int = 1,
    total_turns: int = 0,
    lexicon_results: Optional[Dict] = None,
) -> Dict:
    """BOND Profile 分类主入口.

    参数:
        user_messages:   用户消息列表
        agent_messages:  Agent 消息列表 (当前主要用于轮数推断)
        session_count:   会话总数
        total_turns:     总对话轮数 (若为 0 则从消息数推断)
        lexicon_results: 预计算的词法分析结果字典, 可选.
                         支持的 key:
                           social_language_score, self_disclosure_score,
                           greeting_farewell_score, message_intent_task_ratio,
                           social_hit_count, question_ratio, feedback_ratio

    返回:
        {
            'code':       str,        # 4 字母编码, e.g. 'SUPH'
            'name':       str,        # 中文名, e.g. '指挥官'
            'group':      str,        # 分组名, e.g. '即用型工具派'
            'group_code': str,        # 分组编码, e.g. 'SU'
            'color':      str,        # 颜色标签, e.g. '紫'
            'dims':       dict,       # {dim_key: score}  e.g. {'T': 0.32, ...}
            'scores':     dict,       # 同 dims (别名)
            'traits':     list[str],  # 特质列表
            'motto':      str,        # 座右铭
            'features':   list[str],  # 维度特征描述
        }
    """
    if total_turns <= 0:
        total_turns = max(len(user_messages), len(agent_messages), 1)

    avg_turns = total_turns / max(session_count, 1)

    # ---- 计算四维度得分 ----
    t_score = _compute_T(
        session_count=session_count,
        total_turns=total_turns,
        avg_turns_per_session=avg_turns,
    )

    e_score = _compute_E(
        user_messages=user_messages,
        lexicon_results=lexicon_results,
    )

    c_score = _compute_C(
        user_messages=user_messages,
        lexicon_results=lexicon_results,
    )

    f_score = _compute_F(
        user_messages=user_messages,
    )

    # ---- 编码 ----
    scores = {"T": t_score, "E": e_score, "C": c_score, "F": f_score}
    code = ""
    for dim_key in ["T", "E", "C", "F"]:
        code += _score_to_letter(dim_key, scores[dim_key])

    # ---- 类型信息 ----
    type_info = BOND_TYPES.get(code)
    if type_info:
        name = type_info["name"]
        group = type_info["group"]
        group_code = type_info["group_code"]
        color = type_info["color"]
        traits_str = type_info.get("traits", "")
        motto = type_info.get("motto", "")
    else:
        name = "未知类型"
        group = "未知"
        group_code = "??"
        color = "灰"
        traits_str = ""
        motto = ""

    traits = [t.strip() for t in traits_str.split("，") if t.strip()] if traits_str else []

    # ---- 维度特征描述 ----
    features_desc = _build_features_description(code, scores)

    return {
        "code": code,
        "name": name,
        "group": group,
        "group_code": group_code,
        "color": color,
        "dims": {k: round(v, 4) for k, v in scores.items()},
        "scores": {k: round(v, 4) for k, v in scores.items()},
        "traits": traits,
        "motto": motto,
        "features": features_desc,
    }


def _build_features_description(code: str, scores: Dict[str, float]) -> List[str]:
    """根据类型编码和得分生成人类可读的维度特征描述列表."""
    desc: List[str] = []

    # T
    t_letter = code[0]
    t_score = scores["T"]
    if t_letter == "S":
        desc.append(
            "T={:.0f}% Sprint: 偏好快速交互, 即时获取结果".format(t_score * 100)
        )
    else:
        desc.append(
            "T={:.0f}% Marathon: 愿意长期培养, 深度使用 Agent".format(t_score * 100)
        )

    # E
    e_letter = code[1]
    e_score = scores["E"]
    if e_letter == "U":
        desc.append(
            "E={:.0f}% Utility: 工具理性导向, 聚焦任务完成".format(e_score * 100)
        )
    else:
        desc.append(
            "E={:.0f}% Companion: 伙伴情感导向, 重视交互关系".format(e_score * 100)
        )

    # C
    c_letter = code[2]
    c_score = scores["C"]
    if c_letter == "P":
        desc.append(
            "C={:.0f}% Preview: 事前预审, 先看方案再执行".format(c_score * 100)
        )
    else:
        desc.append(
            "C={:.0f}% Review: 事后复盘, 先执行再检查调整".format(c_score * 100)
        )

    # F
    f_letter = code[3]
    f_score = scores["F"]
    if f_letter == "H":
        desc.append(
            "F={:.0f}% High-level: 意图导向, 给出大方向".format(f_score * 100)
        )
    else:
        desc.append(
            "F={:.0f}% Detailed: 精确具体, 提供详细约束".format(f_score * 100)
        )

    return desc


# ===================================================================
# EMA 渐进更新追踪器
# ===================================================================

class BONDProfileTracker:
    """EMA (Exponential Moving Average) 渐进更新追踪器.

    随着新会话数据到来, 通过指数移动平均平滑更新各维度得分,
    避免单次异常数据导致类型剧烈变化.
    """

    def __init__(self, alpha: float = 0.3, min_sessions: int = 3) -> None:
        """
        参数:
            alpha:        EMA 衰减因子, 越大越重视新数据
            min_sessions: 最少会话数, 少于此数时输出 insufficient_data
        """
        self.alpha = alpha
        self.min_sessions = min_sessions
        self.history: Dict[str, List[float]] = {
            "T": [], "E": [], "C": [], "F": [],
        }
        self.current_scores: Dict[str, float] = {
            "T": 0.5, "E": 0.5, "C": 0.5, "F": 0.5,
        }

    def update(self, features: Dict[str, float]) -> None:
        """用新一批特征更新 EMA 得分."""
        new_scores = {
            "T": _compute_T_from_features(features),
            "E": _compute_E_from_features(features),
            "C": _compute_C_from_features(features),
            "F": _compute_F_from_features(features),
        }
        for dim in ["T", "E", "C", "F"]:
            self.history[dim].append(new_scores[dim])
            if len(self.history[dim]) == 1:
                self.current_scores[dim] = new_scores[dim]
            else:
                self.current_scores[dim] = (
                    self.alpha * new_scores[dim]
                    + (1.0 - self.alpha) * self.current_scores[dim]
                )

    def get_profile(self) -> Dict:
        """获取当前 EMA 平滑后的 BOND Profile.

        数据不足时返回 status='insufficient_data',
        否则返回完整 profile (status='ready').
        """
        n_sessions = len(self.history["T"])
        if n_sessions < self.min_sessions:
            return {
                "status": "insufficient_data",
                "sessions_needed": self.min_sessions - n_sessions,
                "current_scores": dict(self.current_scores),
            }
        return self._profile_from_scores(self.current_scores)

    def _profile_from_scores(self, scores: Dict[str, float]) -> Dict:
        """从裸分构建完整 profile 字典."""
        type_code = ""
        total_conf = 0.0
        dimensions: Dict[str, Dict] = {}

        for dim_key in ["T", "E", "C", "F"]:
            score = scores[dim_key]
            pole_label, conf, prob_b = classify_dimension(score)
            letter = (
                BOND_DIMS[dim_key][1]
                if pole_label == "B"
                else BOND_DIMS[dim_key][0]
            )
            type_code += letter
            total_conf += conf
            dimensions[dim_key] = {
                "score": round(score, 4),
                "pole": letter,
                "confidence": round(conf, 4),
                "dim_name": BOND_DIM_NAMES[dim_key],
            }

        type_info = BOND_TYPES.get(type_code)
        if type_info:
            zh_name = type_info["name"]
            en_name = type_info.get("dims", type_code)
        else:
            zh_name = "未知类型"
            en_name = "Unknown"

        return {
            "status": "ready",
            "type_code": type_code,
            "type_name_zh": zh_name,
            "type_name_en": en_name,
            "confidence": round(total_conf / 4.0, 4),
            "dimensions": dimensions,
        }
