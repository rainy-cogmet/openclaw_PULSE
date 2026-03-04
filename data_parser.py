# -*- coding: utf-8 -*-
"""
OpenClaw 数据解析器 — Session JSONL, Markdown, Memory, Heartbeat, Tools, Skills

完整解析 OpenClaw 生态数据包：
- SessionParser:      JSONL 会话记录，含完整 tool_call 上下文分析
- MarkdownAnalyzer:   SOUL.md / IDENTITY.md / USER.md / AGENTS.md
- MemoryAnalyzer:     MEMORY.md + memory/ 日期文件
- HeartbeatParser:    HEARTBEAT.md 周期性任务
- ToolsConfigParser:  TOOLS.md 本地工具配置
- SkillsAnalyzer:     skills/ 目录已安装技能
- DataParser:         统一入口（bundle / directory）
"""
import json
import math
import os
import re
from collections import Counter
from datetime import datetime
from typing import Dict, List, Optional, Tuple


# =====================================================================
# 常量
# =====================================================================

TOOL_CATEGORIES: Dict[str, List[str]] = {
    'read':    ['Read', 'Glob', 'Grep', 'Search', 'cat', 'ls', 'find', 'read'],
    'write':   ['Write', 'Edit', 'NotebookEdit', 'write', 'save', 'create'],
    'exec':    ['Bash', 'bash', 'execute', 'run', 'shell', 'terminal'],
    'browser': ['browser', 'Browser', 'web', 'fetch', 'url', 'http'],
    'agent':   ['Task', 'Agent', 'subagent', 'dispatch'],
    'memory':  ['memory', 'Memory', 'recall', 'remember'],
    'other':   [],
}

_ACTION_KEYWORDS = frozenset([
    '运行', '执行', '调用', '使用', '帮我', '请',
    'call', 'run', 'use', 'execute', 'invoke', 'please',
])

_CONTROL_SIGNALS = [
    '等一下', '继续', '停', '取消', '暂停', '别动', '不要',
    'wait', 'stop', 'continue', 'cancel', 'pause', 'halt', 'abort',
]

_CONFIG_PATH_MARKERS = frozenset([
    'soul', 'identity', 'memory', 'heartbeat', 'tools',
    'SOUL', 'IDENTITY', 'MEMORY', 'HEARTBEAT', 'TOOLS',
])


# =====================================================================
# 辅助函数
# =====================================================================

def _calc_param_depth(obj, _current=0):
    """递归计算 dict/list 嵌套深度。"""
    if isinstance(obj, dict):
        if not obj:
            return _current + 1
        return max(_calc_param_depth(v, _current + 1) for v in obj.values())
    elif isinstance(obj, list):
        if not obj:
            return _current + 1
        return max(_calc_param_depth(v, _current + 1) for v in obj)
    return _current


def _classify_tool(tool_name):
    """根据 tool_name 匹配 TOOL_CATEGORIES，返回类别字符串。

    优先检查更具体的类别（memory, agent, browser），避免被通用类别
    （如 read 中的 'Search'）误匹配。
    """
    name_lower = tool_name.lower()
    # 按优先级排序：更具体的类别先匹配
    _PRIORITY_ORDER = ['memory', 'agent', 'browser', 'exec', 'write', 'read']
    for category in _PRIORITY_ORDER:
        keywords = TOOL_CATEGORIES.get(category, [])
        for kw in keywords:
            if kw.lower() in name_lower:
                return category
    return 'other'


def _flatten_content(content):
    """将 message.content 统一为纯文本字符串。"""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                if block.get('type') == 'text':
                    parts.append(block.get('text', ''))
                elif block.get('type') == 'tool_result':
                    inner = block.get('content', '')
                    if isinstance(inner, list):
                        for ib in inner:
                            if isinstance(ib, dict) and ib.get('type') == 'text':
                                parts.append(ib.get('text', ''))
                    elif isinstance(inner, str):
                        parts.append(inner)
            elif isinstance(block, str):
                parts.append(block)
        return ' '.join(parts)
    return str(content) if content else ''


def _user_mentions_tool(user_text, tool_name):
    """判断用户消息是否明确提到了该工具名或动作词。"""
    if not user_text or not tool_name:
        return False
    text_lower = user_text.lower()
    if tool_name.lower() in text_lower:
        return True
    for kw in _ACTION_KEYWORDS:
        if kw in text_lower:
            return True
    return False


# =====================================================================
# SessionParser
# =====================================================================

class SessionParser:
    """解析 OpenClaw session JSONL 文件或内存记录列表。

    增强 tool_calls：完整保存 parameters / result / error / timestamp /
    param_count / param_depth / success / self_initiated / category /
    context_msg_role。
    """

    def __init__(self, jsonl_path_or_records):
        self.messages = []
        self.tool_calls = []
        self.metadata = {}
        if isinstance(jsonl_path_or_records, str):
            self._parse_file(jsonl_path_or_records)
        elif isinstance(jsonl_path_or_records, dict):
            # OpenClaw 标准 session JSON 对象:
            #   {"session_id": "...", "messages": [...], "tool_calls": [...]}
            self._parse_openclaw_session(jsonl_path_or_records)
        elif isinstance(jsonl_path_or_records, list):
            self._parse_records(jsonl_path_or_records)

    # ------------------------------------------------------------------
    # 核心解析
    # ------------------------------------------------------------------

    def _parse_file(self, path):
        with open(path, 'r', encoding='utf-8') as f:
            raw = f.read().strip()
        if not raw:
            return
        # 自动检测: JSON 对象 / JSON 数组 / JSONL
        if raw.startswith('{'):
            # 可能是单个 JSON 对象 (OpenClaw 标准 session) 或 JSONL
            try:
                obj = json.loads(raw)
                # 单个 JSON 对象 — 视为 OpenClaw session
                if 'messages' in obj or 'session_id' in obj:
                    self._parse_openclaw_session(obj)
                    return
                # 其他 JSON 对象 — 尝试当作单条 record
                self._parse_records([obj])
                return
            except json.JSONDecodeError:
                pass
            # 不是有效单一 JSON — 按 JSONL 逐行解析
            records = []
            for line in raw.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
            self._parse_records(records)
        elif raw.startswith('['):
            # JSON 数组 — 数组中每个元素是一条 record 或一个 OpenClaw session
            arr = json.loads(raw)
            if arr and isinstance(arr[0], dict) and 'messages' in arr[0]:
                # 数组中是 OpenClaw session 对象 — 只取第一个
                self._parse_openclaw_session(arr[0])
            else:
                self._parse_records(arr)
        else:
            # JSONL: 每行一个 JSON
            records = []
            for line in raw.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
            self._parse_records(records)

    def _parse_openclaw_session(self, session_obj):
        """解析 OpenClaw 标准 session JSON 对象。

        OpenClaw 标准格式:
          {
            "session_id": "sess_001",
            "messages": [
              {"role": "user", "content": "..."},
              {"role": "assistant", "content": "...", "tool_calls": [...]}
            ],
            "tool_calls": [...],       // 可选: 顶层 tool_calls
            "metadata": {...},         // 可选
          }

        兼容转换为 v3 内部 records 格式后调用 _parse_records。
        """
        self.metadata = {
            k: v for k, v in session_obj.items()
            if k not in ('messages', 'tool_calls')
        }
        self.metadata['type'] = 'session'

        records = []
        messages = session_obj.get('messages', [])
        # 顶层 tool_calls（某些格式将 tool_calls 放在 session 顶层）
        top_tool_calls = session_obj.get('tool_calls', [])
        if not isinstance(top_tool_calls, list):
            top_tool_calls = []

        for msg in messages:
            if not isinstance(msg, dict):
                continue
            role = msg.get('role', '')
            if not role:
                continue

            # 构建 v3 内部 record
            rec = {
                'type': 'message',
                'role': role,
                'content': msg.get('content', ''),
                'timestamp': msg.get('timestamp', msg.get('created_at', '')),
                'usage': msg.get('usage', {}),
            }

            # tool_calls: 优先用消息级别的
            msg_tc = msg.get('tool_calls', [])
            if msg_tc and isinstance(msg_tc, list):
                rec['tool_calls'] = msg_tc

            records.append(rec)

        # 如果有顶层 tool_calls 但消息中没有，关联到最后一条 assistant 消息
        if top_tool_calls:
            last_assistant_idx = None
            for i, r in enumerate(records):
                if r.get('role') == 'assistant':
                    last_assistant_idx = i
            if last_assistant_idx is not None:
                existing_tc = records[last_assistant_idx].get('tool_calls', [])
                if not existing_tc:
                    records[last_assistant_idx]['tool_calls'] = top_tool_calls

        self._parse_records(records)

    def _parse_records(self, records):
        # 第一遍：收集所有消息
        raw_messages = []
        for rec in records:
            rtype = rec.get('type', '')
            if rtype == 'session':
                self.metadata = rec
                continue
            if rtype == 'message' or 'message' in rec or 'role' in rec:
                msg = rec.get('message', rec)
                content_raw = msg.get('content', '')
                content = _flatten_content(content_raw)

                tc_raw = msg.get('tool_calls', [])
                if not isinstance(tc_raw, list):
                    tc_raw = []

                ts = rec.get('timestamp', msg.get('timestamp', ''))
                usage = rec.get('usage', msg.get('usage', {}))
                if not isinstance(usage, dict):
                    usage = {}

                role = msg.get('role', 'unknown')

                raw_messages.append({
                    'role': role,
                    'content': content,
                    '_tc_raw': tc_raw,
                    'usage': usage,
                    'timestamp': ts,
                })

        # 第二遍：解析 tool_calls，带上下文判定 self_initiated
        for idx, raw_msg in enumerate(raw_messages):
            tc_raw = raw_msg.pop('_tc_raw')
            parsed_tc = []

            # 获取前一条 user 消息文本（用于 self_initiated 判定）
            prev_user_text = ''
            if raw_msg['role'] == 'assistant':
                for j in range(idx - 1, -1, -1):
                    if raw_messages[j]['role'] == 'user':
                        prev_user_text = raw_messages[j]['content']
                        break

            for t in tc_raw:
                if not isinstance(t, dict):
                    continue

                name = t.get('name', t.get('tool_name', t.get('function', {}).get('name', '')))
                if not name and isinstance(t.get('function'), dict):
                    name = t['function'].get('name', '')

                # 参数提取
                params = t.get('parameters', t.get('params', {}))
                if not isinstance(params, dict):
                    fn = t.get('function', {})
                    args_raw = fn.get('arguments', '{}')
                    if isinstance(args_raw, str):
                        try:
                            params = json.loads(args_raw)
                        except (json.JSONDecodeError, TypeError):
                            params = {}
                    elif isinstance(args_raw, dict):
                        params = args_raw
                    else:
                        params = {}

                result = t.get('result', t.get('output', None))
                if isinstance(result, dict):
                    result = json.dumps(result, ensure_ascii=False)
                elif result is not None:
                    result = str(result)

                error = t.get('error', t.get('error_message', None))
                if isinstance(error, dict):
                    error = json.dumps(error, ensure_ascii=False)
                elif error is not None:
                    error = str(error)

                call_ts = t.get('timestamp', raw_msg['timestamp'])

                param_count = len(params) if isinstance(params, dict) else 0
                param_depth = _calc_param_depth(params) if params else 0
                success = not bool(error)
                self_initiated = not _user_mentions_tool(prev_user_text, name)
                category = _classify_tool(name)

                tc_entry = {
                    'tool_name': name,
                    'parameters': params,
                    'result': result,
                    'error': error,
                    'timestamp': str(call_ts) if call_ts else '',
                    'param_count': param_count,
                    'param_depth': param_depth,
                    'success': success,
                    'self_initiated': self_initiated,
                    'category': category,
                    'context_msg_role': raw_msg['role'],
                }
                parsed_tc.append(tc_entry)

            self.tool_calls.extend(parsed_tc)
            self.messages.append({
                'role': raw_msg['role'],
                'content': raw_msg['content'],
                'tool_calls': parsed_tc,
                'usage': raw_msg['usage'],
                'timestamp': raw_msg['timestamp'],
            })

    # ------------------------------------------------------------------
    # 时间解析
    # ------------------------------------------------------------------

    def _parse_ts(self, ts_str):
        if not ts_str:
            return None
        s = str(ts_str).strip()
        # Unix timestamp（秒或毫秒）
        try:
            num = float(s)
            if num > 1e12:
                num = num / 1000.0
            return datetime.utcfromtimestamp(num)
        except (ValueError, TypeError, OverflowError, OSError):
            pass

        for fmt in (
            '%Y-%m-%dT%H:%M:%SZ',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M:%S.%fZ',
            '%Y-%m-%dT%H:%M:%S.%f',
            '%Y-%m-%dT%H:%M:%S%z',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d %H:%M:%S.%f',
        ):
            try:
                cleaned = s.replace('+00:00', 'Z').replace('+0000', 'Z')
                if cleaned.endswith('Z') and not fmt.endswith('Z'):
                    cleaned = cleaned[:-1]
                return datetime.strptime(cleaned, fmt.rstrip('Z'))
            except (ValueError, TypeError):
                continue
        return None

    # ------------------------------------------------------------------
    # 原有方法（向后兼容）
    # ------------------------------------------------------------------

    def get_session_duration(self):
        timestamps = []
        for m in self.messages:
            dt = self._parse_ts(m['timestamp'])
            if dt:
                timestamps.append(dt)
        if len(timestamps) < 2:
            return 0.0
        return (max(timestamps) - min(timestamps)).total_seconds()

    def get_user_messages(self):
        return [m for m in self.messages if m['role'] == 'user']

    def get_assistant_messages(self):
        return [m for m in self.messages if m['role'] == 'assistant']

    def get_user_message_count(self):
        return len(self.get_user_messages())

    def get_avg_user_message_length(self):
        msgs = self.get_user_messages()
        if not msgs:
            return 0.0
        return sum(len(m['content']) for m in msgs) / len(msgs)

    def get_tool_usage_distribution(self):
        return dict(Counter(tc['tool_name'] for tc in self.tool_calls))

    def get_memory_search_count(self):
        return sum(1 for tc in self.tool_calls
                   if 'memory' in tc['tool_name'].lower())

    def get_total_tokens(self):
        total = 0
        for m in self.messages:
            u = m.get('usage', {})
            total += u.get('totalTokens', u.get('total_tokens', 0))
        return total

    # ------------------------------------------------------------------
    # 新增统计方法
    # ------------------------------------------------------------------

    def get_tool_success_rate(self):
        """工具调用成功率。"""
        if not self.tool_calls:
            return 1.0
        success_count = sum(1 for tc in self.tool_calls if tc['success'])
        return success_count / len(self.tool_calls)

    def get_tool_self_initiated_ratio(self):
        """Agent 自主调用工具的比例。"""
        if not self.tool_calls:
            return 0.0
        self_count = sum(1 for tc in self.tool_calls if tc['self_initiated'])
        return self_count / len(self.tool_calls)

    def get_tool_category_distribution(self):
        """各类别工具使用分布。"""
        dist = {}
        for tc in self.tool_calls:
            cat = tc.get('category', 'other')
            dist[cat] = dist.get(cat, 0) + 1
        return dist

    def get_avg_param_complexity(self):
        """平均参数复杂度 = mean(param_count * (1 + param_depth / 5))。"""
        if not self.tool_calls:
            return 0.0
        total = 0.0
        for tc in self.tool_calls:
            pc = tc.get('param_count', 0)
            pd = tc.get('param_depth', 0)
            total += pc * (1.0 + pd / 5.0)
        return total / len(self.tool_calls)

    def get_tool_retry_count(self):
        """重试次数：连续调用同一工具名视为重试。"""
        if len(self.tool_calls) < 2:
            return 0
        retries = 0
        for i in range(1, len(self.tool_calls)):
            if self.tool_calls[i]['tool_name'] == self.tool_calls[i - 1]['tool_name']:
                retries += 1
        return retries

    def get_user_control_signals(self):
        """统计用户控制信号出现次数。"""
        result = {}
        user_texts = [m['content'].lower() for m in self.messages if m['role'] == 'user']
        combined = ' '.join(user_texts)
        for signal in _CONTROL_SIGNALS:
            count = combined.count(signal.lower())
            if count > 0:
                result[signal] = count
        return result

    def get_agent_self_update_count(self):
        """Agent 自主修改配置文件的次数。

        tool_name 含 write/edit 且 parameters 中路径含 soul/identity/memory 等。
        """
        count = 0
        for tc in self.tool_calls:
            name_lower = tc['tool_name'].lower()
            if 'write' not in name_lower and 'edit' not in name_lower:
                continue
            params_str = json.dumps(tc.get('parameters', {}), ensure_ascii=False).lower()
            for marker in _CONFIG_PATH_MARKERS:
                if marker.lower() in params_str:
                    count += 1
                    break
        return count


# =====================================================================
# MarkdownAnalyzer
# =====================================================================

class MarkdownAnalyzer:
    """分析 SOUL.md / IDENTITY.md / USER.md / AGENTS.md。"""

    KNOWN_TEMPLATES = [
        'Gold Standard', 'Senior Software Architect', 'Deep Researcher',
        'Sassy Personal Assistant', 'Obsessive Optimizer', 'Sales Expert',
        'HR Expert', 'Finance Expert', 'Tech Architect', 'SRE Security',
    ]

    SAFETY_KEYWORDS = frozenset([
        'safety', 'filter', 'block', 'restricted', 'harmful', 'moderation',
        'forbidden', 'prohibited', 'banned', 'disallow', 'reject', 'refuse',
        '安全', '过滤', '屏蔽', '限制', '有害', '审核', '禁止', '拒绝',
    ])

    def __init__(self, soul_text='', identity_text='', user_text='', agents_text=''):
        self.soul = soul_text
        self.identity = identity_text
        self.user = user_text
        self.agents = agents_text

    def get_section(self, text, heading):
        pattern = re.compile(
            r'^(#{1,6})\s+' + re.escape(heading) + r'\s*$',
            re.MULTILINE)
        m = pattern.search(text)
        if not m:
            return ''
        level = len(m.group(1))
        start = m.end()
        next_heading = re.compile(r'^#{1,' + str(level) + r'}\s+', re.MULTILINE)
        nm = next_heading.search(text[start:])
        end = start + nm.start() if nm else len(text)
        return text[start:end].strip()

    def get_soul_section(self, heading):
        return self.get_section(self.soul, heading)

    def get_identity_field(self, field_name):
        pattern = re.compile(
            r'\*\*' + re.escape(field_name) + r':\*\*\s*(.+)',
            re.IGNORECASE)
        m = pattern.search(self.identity)
        return m.group(1).strip() if m else ''

    def get_user_md_richness(self):
        return len(self.user)

    def get_agents_safety_strictness(self):
        if not self.agents:
            return 0.0
        words = re.findall(r'[a-zA-Z]+|[\u4e00-\u9fff]+', self.agents.lower())
        if not words:
            return 0.0
        hits = sum(1 for w in words if w in self.SAFETY_KEYWORDS)
        return min(1.0, hits / max(len(words), 1) * 15)

    def get_soul_emotional_gears_richness(self):
        section = self.get_soul_section('Emotional Gears')
        if not section:
            section = self.get_soul_section('Emotion')
        if not section:
            return 0.0
        return min(1.0, len(section) / 300)

    def get_continuity_prompt_richness(self):
        section = self.get_soul_section('Continuity')
        if not section:
            section = self.get_soul_section('Memory')
        if not section:
            return 0.0
        return min(1.0, len(section) / 200)

    def detect_soul_template(self):
        text_lower = self.soul.lower()
        for tpl in self.KNOWN_TEMPLATES:
            if tpl.lower() in text_lower:
                return tpl
        return 'custom'


# =====================================================================
# MemoryAnalyzer
# =====================================================================

class MemoryAnalyzer:
    """分析 memory 目录和 MEMORY.md。"""

    PERSONAL_KEYWORDS = frozenset([
        'preference', 'personal', 'hobby', 'like', 'dislike', 'favorite',
        'birthday', 'family', 'friend', 'pet', 'habit',
        '偏好', '个人', '爱好', '喜欢', '不喜欢', '最爱', '生日',
        '家人', '朋友', '宠物', '习惯',
    ])

    _DATE_PATTERN = re.compile(r'(\d{4}-\d{2}-\d{2})')

    def __init__(self, memory_dir=None, memory_md_text=''):
        self.memory_dir = memory_dir
        self.memory_md = memory_md_text
        self._files = []
        self._daily_files = []
        self._file_sizes = {}

        if memory_dir and os.path.isdir(memory_dir):
            self._files = [f for f in os.listdir(memory_dir) if f.endswith('.md')]
            for f in self._files:
                if self._DATE_PATTERN.match(f):
                    self._daily_files.append(f)
                fpath = os.path.join(memory_dir, f)
                try:
                    self._file_sizes[f] = os.path.getsize(fpath)
                except OSError:
                    self._file_sizes[f] = 0

    # ------------------------------------------------------------------
    # 原有方法（向后兼容）
    # ------------------------------------------------------------------

    def get_memory_file_count(self):
        return len(self._files)

    def get_memory_md_size(self):
        return len(self.memory_md)

    def get_memory_personal_ratio(self):
        if not self.memory_md:
            return 0.0
        lines = self.memory_md.strip().split('\n')
        if not lines:
            return 0.0
        personal = sum(1 for l in lines
                       if any(kw in l.lower() for kw in self.PERSONAL_KEYWORDS))
        return personal / len(lines)

    def get_topic_persistence(self):
        """跨天话题持续性 [0,1]。"""
        if not self._files:
            if not self.memory_md:
                return 0.0
            dates = re.findall(r'\d{4}-\d{2}-\d{2}', self.memory_md)
            unique_dates = set(dates)
            return min(1.0, len(unique_dates) / max(len(dates), 1)) if dates else 0.0
        dates = set()
        for f in self._files:
            m = re.match(r'(\d{4}-\d{2}-\d{2})', f)
            if m:
                dates.add(m.group(1))
        return min(1.0, len(dates) / max(len(self._files), 1))

    # ------------------------------------------------------------------
    # 新增方法
    # ------------------------------------------------------------------

    def get_daily_memory_files(self):
        """返回 memory/YYYY-MM-DD.md 格式的文件列表。"""
        return sorted(self._daily_files)

    def get_memory_depth(self):
        """记忆深度 = sum(file_sizes) / 1000, clamped to [0, 1]。"""
        total_size = sum(self._file_sizes.values()) + len(self.memory_md)
        return min(1.0, max(0.0, total_size / 1000.0))

    def get_topic_count(self):
        """统计 memory 中不同话题数（通过 heading 计数）。"""
        heading_pattern = re.compile(r'^#{1,6}\s+.+', re.MULTILINE)
        count = len(heading_pattern.findall(self.memory_md))
        if self.memory_dir and os.path.isdir(self.memory_dir):
            for f in self._files:
                fpath = os.path.join(self.memory_dir, f)
                try:
                    with open(fpath, 'r', encoding='utf-8') as fh:
                        text = fh.read()
                    count += len(heading_pattern.findall(text))
                except (OSError, UnicodeDecodeError):
                    pass
        return count

    def get_date_span_days(self):
        """最早到最晚 memory 文件的天数跨度。"""
        dates = []
        for f in self._daily_files:
            m = self._DATE_PATTERN.match(f)
            if m:
                try:
                    dates.append(datetime.strptime(m.group(1), '%Y-%m-%d'))
                except ValueError:
                    pass
        if len(dates) < 2:
            return 0
        return (max(dates) - min(dates)).days


# =====================================================================
# HeartbeatParser
# =====================================================================

class HeartbeatParser:
    """解析 HEARTBEAT.md 文件 -- 周期性任务和自动化清单。"""

    _CHECKBOX_RE = re.compile(
        r'^[-*]\s+\[([ xX])\]\s+(.+)$', re.MULTILINE
    )
    _SCHEDULE_RE = re.compile(r'@\s*(.+?)$')
    _EVERY_RE = re.compile(r'\b(every\s+.+?(?:\s+|$))', re.IGNORECASE)
    _MEIMEI_RE = re.compile(r'(每[\u4e00-\u9fff0-9]+(?:[\u4e00-\u9fff]+)?)')

    def __init__(self, text=''):
        self.text = text
        self.tasks = []
        self._parse()

    def _parse(self):
        if not self.text:
            return
        for match in self._CHECKBOX_RE.finditer(self.text):
            checked = match.group(1).lower() == 'x'
            raw_line = match.group(2).strip()

            schedule = ''
            sch_match = self._SCHEDULE_RE.search(raw_line)
            if sch_match:
                schedule = sch_match.group(1).strip()
                name = raw_line[:sch_match.start()].strip()
            else:
                every_match = self._EVERY_RE.search(raw_line)
                meimei_match = self._MEIMEI_RE.search(raw_line)
                if every_match:
                    schedule = every_match.group(1).strip()
                    name = raw_line[:every_match.start()].strip() or raw_line
                elif meimei_match:
                    schedule = meimei_match.group(1).strip()
                    name = raw_line[:meimei_match.start()].strip() or raw_line
                else:
                    name = raw_line

            self.tasks.append({
                'name': name,
                'schedule': schedule,
                'enabled': checked,
            })

    def get_task_count(self):
        return len(self.tasks)

    def get_enabled_count(self):
        return sum(1 for t in self.tasks if t['enabled'])

    def get_activity_level(self):
        """heartbeat 活跃度 = enabled_tasks / max(total_tasks, 1)。"""
        total = len(self.tasks)
        if total == 0:
            return 0.0
        return self.get_enabled_count() / total

    def has_heartbeat(self):
        return bool(self.text.strip())


# =====================================================================
# ToolsConfigParser
# =====================================================================

class ToolsConfigParser:
    """解析 TOOLS.md -- 本地工具配置、SSH 主机、语音偏好等。"""

    def __init__(self, text=''):
        self.text = text
        self.tools = []
        self.ssh_hosts = []
        self.preferences = {}
        self.custom_commands = []
        self._parse()

    def _parse(self):
        if not self.text:
            return

        current_section = ''
        for line in self.text.split('\n'):
            stripped = line.strip()

            heading_match = re.match(r'^#{1,6}\s+(.+)', stripped)
            if heading_match:
                current_section = heading_match.group(1).strip().lower()
                continue

            list_match = re.match(r'^[-*]\s+(.+)', stripped)
            if not list_match:
                continue
            item = list_match.group(1).strip()

            kv_match = re.match(r'^([^:]+):\s*(.+)', item)
            if not kv_match:
                continue
            key = kv_match.group(1).strip()
            value = kv_match.group(2).strip()

            if 'ssh' in current_section:
                self.ssh_hosts.append({'alias': key, 'target': value})
            elif 'custom' in current_section or 'command' in current_section:
                self.custom_commands.append({'name': key, 'command': value})
            elif 'tool' in current_section or 'local' in current_section:
                self.tools.append({
                    'name': key,
                    'type': self._infer_tool_type(key, value),
                    'config': {'value': value},
                })
            elif 'preference' in current_section or 'setting' in current_section:
                self.preferences[key] = value
            else:
                if '@' in value or 'ssh' in value.lower():
                    self.ssh_hosts.append({'alias': key, 'target': value})
                else:
                    self.tools.append({
                        'name': key,
                        'type': self._infer_tool_type(key, value),
                        'config': {'value': value},
                    })

    @staticmethod
    def _infer_tool_type(key, value):
        kl = key.lower()
        vl = value.lower()
        if 'camera' in kl or 'photo' in kl:
            return 'camera'
        if 'voice' in kl or 'speech' in kl or 'tts' in kl:
            return 'voice'
        if 'editor' in kl or 'ide' in kl:
            return 'editor'
        if 'ssh' in kl or '@' in vl:
            return 'ssh'
        return 'generic'

    def get_tool_count(self):
        return len(self.tools)

    def get_ssh_host_count(self):
        return len(self.ssh_hosts)

    def get_has_custom_commands(self):
        return len(self.custom_commands) > 0

    def get_config_richness(self):
        """配置丰富度 = min(1.0, (tool_count + ssh_hosts + custom_commands) / 10)。"""
        total = len(self.tools) + len(self.ssh_hosts) + len(self.custom_commands)
        return min(1.0, total / 10.0)


# =====================================================================
# SkillsAnalyzer
# =====================================================================

class SkillsAnalyzer:
    """分析 skills/ 目录 -- 已安装的 skills。"""

    _DOMAIN_KEYWORDS = {
        'code': ['code', 'programming', 'dev', 'debug', 'lint', 'compile', 'build'],
        'data': ['data', 'analytics', 'sql', 'csv', 'excel', 'chart', 'plot'],
        'web': ['web', 'http', 'api', 'scrape', 'crawl', 'browser', 'fetch'],
        'ai': ['ai', 'ml', 'model', 'gpt', 'llm', 'neural', 'train'],
        'productivity': ['note', 'todo', 'calendar', 'email', 'slack', 'notion'],
        'system': ['system', 'os', 'file', 'disk', 'process', 'shell', 'terminal'],
        'media': ['image', 'video', 'audio', 'photo', 'music', 'camera'],
        'communication': ['chat', 'message', 'sms', 'call', 'voice'],
    }

    def __init__(self, skills_dir=''):
        self.skills_dir = skills_dir
        self.skills = []
        if skills_dir and os.path.isdir(skills_dir):
            self._scan()

    def _scan(self):
        """扫描 skills/ 下的子目录，每个含 SKILL.md 的视为一个 skill。"""
        try:
            entries = os.listdir(self.skills_dir)
        except OSError:
            return

        for entry in sorted(entries):
            subdir = os.path.join(self.skills_dir, entry)
            if not os.path.isdir(subdir):
                continue
            skill_md = os.path.join(subdir, 'SKILL.md')
            if not os.path.isfile(skill_md):
                continue

            has_script = os.path.isdir(os.path.join(subdir, 'scripts'))
            if not has_script:
                try:
                    has_script = any(
                        f.endswith(('.py', '.sh', '.js', '.ts'))
                        for f in os.listdir(subdir)
                        if os.path.isfile(os.path.join(subdir, f))
                    )
                except OSError:
                    pass

            domain = self._infer_domain(entry, skill_md)
            self.skills.append({
                'name': entry,
                'has_script': has_script,
                'domain': domain,
            })

    def _infer_domain(self, skill_name, skill_md_path):
        """从 skill 名称和 SKILL.md 内容推断域。"""
        text = skill_name.lower()
        try:
            with open(skill_md_path, 'r', encoding='utf-8') as f:
                text += ' ' + f.read(2000).lower()
        except (OSError, UnicodeDecodeError):
            pass

        best_domain = 'general'
        best_score = 0
        for domain, keywords in self._DOMAIN_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text)
            if score > best_score:
                best_score = score
                best_domain = domain
        return best_domain

    def get_installed_count(self):
        return len(self.skills)

    def get_skill_diversity(self):
        """skill 多样性 = unique_domains / max(total_skills, 1)。"""
        if not self.skills:
            return 0.0
        unique_domains = set(s['domain'] for s in self.skills)
        return len(unique_domains) / max(len(self.skills), 1)

    def get_skill_names(self):
        return [s['name'] for s in self.skills]


# =====================================================================
# DataParser — 统一入口
# =====================================================================

class DataParser:
    """统一数据解析入口。

    提供两种解析方式：
    - parse_bundle(bundle):    解析 JSON 字典（来自 API 调用）
    - parse_directory(dirpath): 解析文件目录（本地数据包）
    """

    @staticmethod
    def parse_bundle(bundle):
        """解析 JSON bundle，返回标准化数据包。

        自动检测并兼容三种 bundle 格式:

        格式 A — v3 原始格式 (sessions 是 record 数组的数组):
          {
            'soul': str,
            'identity': str,
            'sessions': [ [record, ...], ... ],
          }

        格式 B — OpenClaw 标准格式 (sessions 是 session 对象数组):
          {
            'soul': str,                                    // 或 'soul_text'
            'identity': str,                                // 或 'identity_text'
            'sessions': [
              {"session_id": "s1", "messages": [...]},      // 标准 session 对象
              ...
            ],
          }

        格式 C — 简易格式 (无 sessions，仅消息列表):
          {
            'user_messages': ["...", ...],
            'agent_messages': ["...", ...],
            'soul_text': str,
          }

        格式 D — 单个 session 对象 (无外层包装):
          {
            'session_id': 'sess_001',
            'messages': [{"role": "user", "content": "..."}],
          }
        """
        # --- 格式检测 ---
        has_sessions = 'sessions' in bundle
        has_messages_field = 'messages' in bundle and isinstance(bundle.get('messages'), list)
        has_user_messages = 'user_messages' in bundle

        # 格式 D: 单个 session 对象
        if has_messages_field and not has_sessions:
            bundle = {'sessions': [bundle]}
            has_sessions = True

        # 兼容 key 别名: soul_text → soul, identity_text → identity
        soul_text = bundle.get('soul', bundle.get('soul_text', ''))
        identity_text = bundle.get('identity', bundle.get('identity_text', ''))
        user_text = bundle.get('user', bundle.get('user_text', ''))
        agents_text = bundle.get('agents', bundle.get('agents_text', ''))
        heartbeat_text = bundle.get('heartbeat', '')
        tools_text = bundle.get('tools', '')
        memory_md_text = bundle.get('memory_md', bundle.get('memory_md_text', ''))

        # --- 解析 sessions ---
        sessions = []
        if has_sessions:
            raw_sessions = bundle.get('sessions', [])
            for session_data in raw_sessions:
                try:
                    if isinstance(session_data, dict):
                        # 格式 B: OpenClaw 标准 session 对象 {"session_id":..., "messages":[...]}
                        # 格式 A fallback: 如果 dict 没有 messages 字段, 当作单条 record
                        sessions.append(SessionParser(session_data))
                    elif isinstance(session_data, list):
                        # 格式 A: v3 原始 record 数组
                        sessions.append(SessionParser(session_data))
                    elif isinstance(session_data, str):
                        # 文件路径
                        if os.path.isfile(session_data):
                            sessions.append(SessionParser(session_data))
                except Exception:
                    continue

        # --- 解析 Markdown ---
        # heartbeat/tools 可能是文本 (str) 或预解析对象
        if isinstance(heartbeat_text, str):
            hb = HeartbeatParser(heartbeat_text)
        else:
            hb = heartbeat_text  # 已经是 HeartbeatParser 或 Mock 对象

        if isinstance(tools_text, str):
            tc = ToolsConfigParser(tools_text)
        else:
            tc = tools_text

        md = MarkdownAnalyzer(soul_text, identity_text, user_text, agents_text)
        mem = MemoryAnalyzer(memory_dir=None, memory_md_text=memory_md_text if isinstance(memory_md_text, str) else '')
        sk = SkillsAnalyzer('')

        # --- 提取消息 ---
        if sessions:
            user_messages = DataParser.extract_user_messages(sessions)
            agent_messages = DataParser.extract_agent_messages(sessions)
        elif has_user_messages:
            # 格式 C: 简易格式, 直接使用
            user_messages = bundle.get('user_messages', [])
            agent_messages = bundle.get('agent_messages', [])
        else:
            user_messages = []
            agent_messages = []

        all_tool_calls = []
        total_turns = 0
        for s in sessions:
            all_tool_calls.extend(s.tool_calls)
            total_turns += len(s.messages)

        # 如果从 sessions 没有解析到 turns，使用消息列表长度
        if total_turns == 0:
            total_turns = len(user_messages) + len(agent_messages)

        return {
            'sessions': sessions,
            'markdown': md,
            'memory': mem,
            'heartbeat': hb,
            'tools_config': tc,
            'skills': sk,
            'user_messages': user_messages,
            'agent_messages': agent_messages,
            'session_count': max(len(sessions), bundle.get('session_count', 1)),
            'total_turns': total_turns,
            'all_tool_calls': all_tool_calls,
            'soul_text': soul_text,
            'identity_text': identity_text,
            # 透传额外字段 (lexicon_results, user_name, agent_name 等)
            **{k: v for k, v in bundle.items()
               if k not in ('sessions', 'soul', 'soul_text', 'identity', 'identity_text',
                            'user', 'user_text', 'agents', 'agents_text',
                            'heartbeat', 'tools', 'memory_md', 'memory_md_text',
                            'messages')},
        }

    @staticmethod
    def parse_directory(dirpath):
        """解析目录结构，返回标准化数据包。

        目录结构：
            dirpath/
                SOUL.md
                IDENTITY.md
                USER.md (可选)
                AGENTS.md (可选)
                HEARTBEAT.md (可选)
                TOOLS.md (可选)
                MEMORY.md (可选)
                memory/ (可选, 含 YYYY-MM-DD.md)
                skills/ (可选)
                sessions/ (含 *.jsonl)
                .openclaw/ (可选)
        """

        def _read_optional(filename):
            fpath = os.path.join(dirpath, filename)
            if os.path.isfile(fpath):
                try:
                    with open(fpath, 'r', encoding='utf-8') as f:
                        return f.read()
                except (OSError, UnicodeDecodeError):
                    pass
            return ''

        # 尝试多种文件名: SOUL.md / soul.md，以及 .openclaw/ 子目录
        def _read_multi(names):
            for name in names:
                result = _read_optional(name)
                if result:
                    return result
                # 尝试 .openclaw/ 子目录
                alt = os.path.join('.openclaw', name)
                result = _read_optional(alt)
                if result:
                    return result
                # 尝试 .openclaw/agents/*/ 子目录 (OpenClaw 标准路径)
                agents_base = os.path.join(dirpath, '.openclaw', 'agents')
                if os.path.isdir(agents_base):
                    try:
                        for agent_name in sorted(os.listdir(agents_base)):
                            agent_dir = os.path.join(agents_base, agent_name)
                            if os.path.isdir(agent_dir):
                                candidate = os.path.join(agent_dir, name)
                                if os.path.isfile(candidate):
                                    try:
                                        with open(candidate, 'r', encoding='utf-8') as f:
                                            return f.read()
                                    except (OSError, UnicodeDecodeError):
                                        pass
                    except OSError:
                        pass
            return ''

        soul_text = _read_multi(['SOUL.md', 'soul.md'])
        identity_text = _read_multi(['IDENTITY.md', 'identity.md'])
        user_text = _read_multi(['USER.md', 'user.md'])
        agents_text = _read_multi(['AGENTS.md', 'agents.md'])
        heartbeat_text = _read_multi(['HEARTBEAT.md', 'heartbeat.md'])
        tools_text = _read_multi(['TOOLS.md', 'tools.md'])
        memory_md_text = _read_multi(['MEMORY.md', 'memory.md'])

        # Sessions
        sessions = []
        # 查找 sessions 目录, 按优先级尝试:
        #   1. dirpath/sessions/
        #   2. dirpath/.openclaw/sessions/
        #   3. dirpath/.openclaw/agents/*/sessions/  (OpenClaw 标准路径)
        sessions_dir = os.path.join(dirpath, 'sessions')
        if not os.path.isdir(sessions_dir):
            alt_dir = os.path.join(dirpath, '.openclaw', 'sessions')
            if os.path.isdir(alt_dir):
                sessions_dir = alt_dir
            else:
                # OpenClaw 标准路径: .openclaw/agents/<agent_name>/sessions/
                agents_base = os.path.join(dirpath, '.openclaw', 'agents')
                if os.path.isdir(agents_base):
                    for agent_name in sorted(os.listdir(agents_base)):
                        candidate = os.path.join(agents_base, agent_name, 'sessions')
                        if os.path.isdir(candidate):
                            sessions_dir = candidate
                            break

        if os.path.isdir(sessions_dir):
            # 支持 .jsonl 和 .json 文件
            session_files = sorted(
                f for f in os.listdir(sessions_dir)
                if f.endswith('.jsonl') or f.endswith('.json')
            )
            for jf in session_files:
                try:
                    sessions.append(SessionParser(os.path.join(sessions_dir, jf)))
                except (OSError, json.JSONDecodeError, UnicodeDecodeError):
                    pass

        # Memory
        memory_dir = os.path.join(dirpath, 'memory')
        mem = MemoryAnalyzer(
            memory_dir=memory_dir if os.path.isdir(memory_dir) else None,
            memory_md_text=memory_md_text,
        )

        # Markdown
        md = MarkdownAnalyzer(soul_text, identity_text, user_text, agents_text)

        # Heartbeat
        hb = HeartbeatParser(heartbeat_text)

        # Tools
        tc = ToolsConfigParser(tools_text)

        # Skills
        skills_dir = os.path.join(dirpath, 'skills')
        sk = SkillsAnalyzer(skills_dir if os.path.isdir(skills_dir) else '')

        # 聚合
        user_messages = DataParser.extract_user_messages(sessions)
        agent_messages = DataParser.extract_agent_messages(sessions)
        all_tool_calls = []
        total_turns = 0
        for s in sessions:
            all_tool_calls.extend(s.tool_calls)
            total_turns += len(s.messages)

        return {
            'sessions': sessions,
            'markdown': md,
            'memory': mem,
            'heartbeat': hb,
            'tools_config': tc,
            'skills': sk,
            'user_messages': user_messages,
            'agent_messages': agent_messages,
            'session_count': len(sessions),
            'total_turns': total_turns,
            'all_tool_calls': all_tool_calls,
            'soul_text': soul_text,
            'identity_text': identity_text,
        }

    @staticmethod
    def extract_user_messages(sessions):
        """从 session 列表提取所有用户消息文本。"""
        texts = []
        for s in sessions:
            for m in s.get_user_messages():
                content = m.get('content', '')
                if content:
                    texts.append(content)
        return texts

    @staticmethod
    def extract_agent_messages(sessions):
        """从 session 列表提取所有 agent 消息文本。"""
        texts = []
        for s in sessions:
            for m in s.get_assistant_messages():
                content = m.get('content', '')
                if content:
                    texts.append(content)
        return texts
