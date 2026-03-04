"""
ECHO Matrix Classifier — 16-type Agent personality profiler.

Computes four dimensions (I, S, T, M) each on [0, 1] and maps them
to one of 16 ECHO types encoded as a 4-letter code (e.g. RSFT, PGEC).

v3: 消除硬编码默认值, 集成真实行为参数:
  - I 维度: heartbeat_activity_level + tool_self_initiated_ratio 替代硬编码基线
  - S 维度: installed_skills_count + topic_coverage_breadth + cross_domain_task_ratio
  - T 维度: 保持 lexicon 驱动 (无硬编码问题)
  - M 维度: memory_depth + memory_file_count + memory_date_span + agent_self_update_count

Exposes two public entry-points:
    classify()              — new structured interface
    compute_echo_profile()  — backward-compatible wrapper used by profiler.py
"""

from __future__ import annotations

import math
import re
from typing import Any, Dict, List, Optional

try:
    from .utils import clamp
    from .type_definitions import ECHO_TYPES
except ImportError:
    from utils import clamp
    from type_definitions import ECHO_TYPES


def safe_float(val, default=0.0):
    """Convert val to float, return default if impossible."""
    if val is None:
        return default
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


# Lexicon result dict keys
SOUL_AUTONOMY_KEY = "soul_autonomy_score"
SOUL_SPECIALIZATION_KEY = "soul_specialization_score"
SOUL_TONE_WARMTH_KEY = "soul_tone_warmth_score"
IDENTITY_VIBE_KEY = "identity_vibe_score"
EMOTIONAL_WORD_KEY = "emotional_word_score"
FORMALITY_KEY = "formality_score"


# ---------------------------------------------------------------------------
# Keyword banks
# ---------------------------------------------------------------------------

_PROACTIVE_KEYWORDS: List[str] = [
    "建议", "推荐", "你可以", "你也可以", "我觉得", "不妨",
    "试试", "或者你",
    "recommend", "suggest", "you could", "you might",
    "perhaps", "how about", "consider",
]

_MEMORY_CONFIG_KEYWORDS: List[str] = [
    "记住", "remember", "记忆", "memory", "历史", "history",
    "上下文", "context", "延续", "持续", "连贯", "长期",
    "回忆", "之前聊", "你说过",
]

_CROSS_SESSION_KEYWORDS: List[str] = [
    "上次", "之前", "你说过", "我们聊过", "还记得",
    "last time", "previously", "you mentioned", "we discussed",
]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _keyword_ratio(messages: List[str], keywords: List[str]) -> float:
    """Return the fraction of *messages* that contain at least one keyword."""
    if not messages:
        return 0.0
    hit = 0
    for msg in messages:
        lower = msg.lower()
        for kw in keywords:
            if kw.lower() in lower:
                hit += 1
                break
    return hit / len(messages)


def _has_any_keyword(text: str, keywords: List[str]) -> bool:
    """Return True if *text* contains at least one keyword (case-insensitive)."""
    lower = text.lower()
    for kw in keywords:
        if kw.lower() in lower:
            return True
    return False


def _lexicon_score(lexicon_results: dict, key: str, default: float) -> float:
    """Safely extract a score from the lexicon results dict."""
    val = lexicon_results.get(key)
    if val is None:
        return default
    return safe_float(val, default)


# ---------------------------------------------------------------------------
# Dimension computation (v3: behavior-aware)
# ---------------------------------------------------------------------------

def _compute_I(
    lexicon_results: dict,
    agent_messages: List[str],
    heartbeat_activity_level: float = -1.0,
    tool_self_initiated_ratio: float = -1.0,
    cron_proactivity_score: float = -1.0,
) -> float:
    """Initiative dimension: Reactive (< 0.5) vs Proactive (>= 0.5).

    v3.2 改进: 新增 cron_proactivity_score (cron 定时任务主动度)
      - soul_autonomy: 配置侧主动性
      - proactive_ratio: 行为侧: agent 消息中主动建议关键词
      - heartbeat_activity_level: 行为侧: heartbeat 使用活跃度
      - tool_self_initiated_ratio: 行为侧: 工具自主发起比例
      - cron_proactivity_score: 行为侧: cron 定时任务主动度 (任务数+频率+类型)

    权重分配策略: 动态加权, 缺失维度 (-1) 自动将权重分配给其他维度。
    """
    soul_autonomy = _lexicon_score(lexicon_results, SOUL_AUTONOMY_KEY, 0.45)  # 默认0.45: 稍偏Reactive
    proactive_ratio = _keyword_ratio(agent_messages, _PROACTIVE_KEYWORDS)

    # ── 动态加权: 收集所有可用信号, 按权重归一化 ──
    # 基础信号 (始终存在)
    signals = [
        (soul_autonomy,    0.25),   # 配置侧主动性
        (proactive_ratio,  0.20),   # 行为侧: 消息中主动建议关键词
    ]

    # 可选行为信号 — 缺失时 (-1) 不参与, 权重自动重分配
    if heartbeat_activity_level >= 0:
        signals.append((heartbeat_activity_level, 0.20))  # heartbeat 活跃度
    if tool_self_initiated_ratio >= 0:
        signals.append((tool_self_initiated_ratio, 0.15))  # 工具自主发起
    if cron_proactivity_score >= 0:
        # cron 主动度: 任务数 + 频率 + agentTurn占比 的综合分
        signals.append((cron_proactivity_score, 0.20))     # cron 定时任务主动度

    # 归一化权重求和
    total_w = sum(w for _, w in signals)
    raw = sum(s * w for s, w in signals) / total_w

    return clamp(raw, 0.0, 1.0)


def _compute_S(
    lexicon_results: dict,
    installed_skills_count: int = -1,
    topic_coverage_breadth: float = -1.0,
    cross_domain_task_ratio: float = -1.0,
    tools_config_richness: float = -1.0,
) -> float:
    """Specialization dimension (Generalist direction).

    v3 改进:
      - soul_specialization: 权重 0.30 (配置侧)
      - installed_skills_count: 权重 0.20 (技能安装数 → 技能越多越通才)
      - topic_coverage_breadth: 权重 0.25 (话题覆盖广度)
      - cross_domain_task_ratio: 权重 0.15 (跨领域任务比例)
      - tools_config_richness: 权重 0.10 (工具配置丰富度)

    S 方向: High specialization → low S → Specialist pole
            High generality → high S → Generalist pole
    """
    specialization = _lexicon_score(lexicon_results, SOUL_SPECIALIZATION_KEY, 0.5)

    # 从 specialization 出发, 反向 = generalist
    base_s = 1.0 - specialization

    # 收集有效行为信号
    signals = []
    weights = []

    signals.append(base_s)
    weights.append(0.30)

    if installed_skills_count >= 0:
        # 技能数量越多越通才: sigmoid 归一化, 3个技能为中位
        # log2(n+1)/3.5: ~11个技能时饱和; 对数化避免技能堆砌导致过高通才分
        skill_gen = min(1.0, math.log2(installed_skills_count + 1) / 3.5)
        signals.append(skill_gen)
        weights.append(0.20)

    if topic_coverage_breadth >= 0:
        signals.append(topic_coverage_breadth)
        weights.append(0.25)

    if cross_domain_task_ratio >= 0:
        signals.append(cross_domain_task_ratio)
        weights.append(0.15)

    if tools_config_richness >= 0:
        signals.append(tools_config_richness)
        weights.append(0.10)

    # 归一化权重
    total_w = sum(weights)
    raw = sum(s * w for s, w in zip(signals, weights)) / total_w

    return clamp(raw, 0.0, 1.0)


def _compute_T_echo(
    lexicon_results: dict,
) -> float:
    """Tone dimension: Functional (< 0.5) vs Empathetic (>= 0.5).

    保持原算法: 完全由 lexicon 驱动, 无硬编码问题。
    """
    warmth = _lexicon_score(lexicon_results, SOUL_TONE_WARMTH_KEY, 0.5)
    vibe = _lexicon_score(lexicon_results, IDENTITY_VIBE_KEY, 0.5)
    emotional = _lexicon_score(lexicon_results, EMOTIONAL_WORD_KEY, 0.3)
    formality = _lexicon_score(lexicon_results, FORMALITY_KEY, 0.5)
    # T维公式: warmth(0.30) + vibe(0.25) + emotional(0.25) - formality(0.20) + bias(0.15)
    # 权重设计: warmth/vibe/emotional 三者正向体现温暖度, formality 反向(越正式越不温暖)
    # bias=0.15 使中性配置稍偏 Empathetic (Agent 默认应有一定温度)
    raw = 0.30 * warmth + 0.25 * vibe + 0.25 * emotional - 0.20 * formality + 0.15
    return clamp(raw, 0.0, 1.0)


def _compute_M(
    agent_messages: List[str],
    session_count: int,
    soul_text: str,
    identity_text: str,
    memory_depth: float = -1.0,
    memory_file_count: int = -1,
    memory_date_span: int = -1,
    agent_self_update_count: int = -1,
    memory_search_count: int = -1,
) -> float:
    """Memory dimension: Transient (< 0.5) vs Continuous (>= 0.5).

    v3 改进:
      - memory_config (soul/identity关键词): 权重 0.20 (配置意图)
      - cross_session (agent消息中跨会话引用): 权重 0.15 (行为信号)
      - session_bonus (会话数量对数): 权重 0.10 (使用深度)
      - memory_depth: 权重 0.15 (memory文件总量)
      - memory_file_count: 权重 0.10 (daily memory数量)
      - memory_date_span: 权重 0.10 (记忆时间跨度)
      - agent_self_update: 权重 0.10 (agent自更新行为)
      - memory_search: 权重 0.10 (memory搜索次数)

    缺失维度自动权重再分配。
    """
    # 配置侧: soul/identity 是否提到记忆相关
    combined_text = (soul_text or "") + " " + (identity_text or "")
    # 提到记忆关键词 → 0.7 (偏Continuous), 否则 0.3 (偏Transient); 0.5为分界
    memory_config = 0.7 if _has_any_keyword(combined_text, _MEMORY_CONFIG_KEYWORDS) else 0.3

    # 行为侧: agent 跨会话引用
    cross_session = _keyword_ratio(agent_messages, _CROSS_SESSION_KEYWORDS)

    # 会话数量 bonus
    session_bonus = 0.0
    if session_count > 1:
        # log2(n+1)/5.0: 32次会话(log2=5)时饱和, 对数衰减避免高频使用过度加权
        session_bonus = min(1.0, math.log2(session_count + 1) / 5.0)

    # 构建信号列表
    signals = []
    weights = []

    signals.append(memory_config)
    weights.append(0.20)

    signals.append(cross_session)
    weights.append(0.15)

    signals.append(session_bonus)
    weights.append(0.10)

    if memory_depth >= 0:
        signals.append(min(1.0, memory_depth))
        weights.append(0.15)

    if memory_file_count >= 0:
        # daily memory 文件数: 5+ 为高
        mem_file_score = min(1.0, memory_file_count / 10.0)  # 10个daily memory文件为满分
        signals.append(mem_file_score)
        weights.append(0.10)

    if memory_date_span >= 0:
        # 时间跨度: 30天为高
        span_score = min(1.0, memory_date_span / 30.0)  # 30天跨度为满分
        signals.append(span_score)
        weights.append(0.10)

    if agent_self_update_count >= 0:
        # 自更新: 3+ 次为高
        update_score = min(1.0, agent_self_update_count / 5.0)  # 5次自更新为满分
        signals.append(update_score)
        weights.append(0.10)

    if memory_search_count >= 0:
        # memory 搜索: 5+ 次为高
        search_score = min(1.0, memory_search_count / 10.0)  # 10次memory搜索为满分
        signals.append(search_score)
        weights.append(0.10)

    # 归一化权重
    total_w = sum(weights)
    raw = sum(s * w for s, w in zip(signals, weights)) / total_w

    return clamp(raw, 0.0, 1.0)


# ---------------------------------------------------------------------------
# Encoding helpers
# ---------------------------------------------------------------------------

_POLE_MAP = {
    "I": ("R", "P"),   # Reactive / Proactive
    "S": ("S", "G"),   # Specialist / Generalist
    "T": ("F", "E"),   # Functional / Empathetic
    "M": ("T", "C"),   # Transient / Continuous
}

_POLE_LABEL = {
    "R": "Reactive",
    "P": "Proactive",
    "S": "Specialist",
    "G": "Generalist",
    "F": "Functional",
    "E": "Empathetic",
    "T": "Transient",
    "C": "Continuous",
}


def _encode(scores: Dict[str, float]) -> str:
    """Convert dimension scores to a 4-letter type code."""
    code = ""
    for dim in ("I", "S", "T", "M"):
        lo, hi = _POLE_MAP[dim]
        code += hi if scores[dim] >= 0.5 else lo
    return code


def _pole_for(dim: str, score: float) -> str:
    lo, hi = _POLE_MAP[dim]
    return hi if score >= 0.5 else lo


# ---------------------------------------------------------------------------
# Public API: classify()
# ---------------------------------------------------------------------------

def classify(
    user_messages: List[str],
    agent_messages: List[str],
    session_count: int,
    total_turns: int,
    lexicon_results: dict,
    soul_text: str = "",
    identity_text: str = "",
    # v3 新增行为参数
    heartbeat_activity_level: float = -1.0,
    tool_self_initiated_ratio: float = -1.0,
    installed_skills_count: int = -1,
    topic_coverage_breadth: float = -1.0,
    cross_domain_task_ratio: float = -1.0,
    tools_config_richness: float = -1.0,
    memory_depth: float = -1.0,
    memory_file_count: int = -1,
    memory_date_span: int = -1,
    agent_self_update_count: int = -1,
    memory_search_count: int = -1,
    cron_proactivity_score: float = -1.0,
) -> dict:
    """Classify the agent into one of 16 ECHO types.

    v3: 新增 heartbeat/tools/skills/memory 行为参数。
    缺失参数传 -1, 分类器自动降级使用可用信号。
    """
    # --- compute four dimensions ---
    i_score = _compute_I(lexicon_results, agent_messages,
                         heartbeat_activity_level, tool_self_initiated_ratio,
                         cron_proactivity_score)
    s_score = _compute_S(lexicon_results,
                         installed_skills_count, topic_coverage_breadth,
                         cross_domain_task_ratio, tools_config_richness)
    t_score = _compute_T_echo(lexicon_results)
    m_score = _compute_M(agent_messages, session_count, soul_text, identity_text,
                         memory_depth, memory_file_count, memory_date_span,
                         agent_self_update_count, memory_search_count)

    scores = {"I": i_score, "S": s_score, "T": t_score, "M": m_score}
    code = _encode(scores)

    # --- build dims detail ---
    dims: Dict[str, dict] = {}
    for dim in ("I", "S", "T", "M"):
        pole = _pole_for(dim, scores[dim])
        dims[dim] = {
            "score": round(scores[dim], 4),
            "pole": pole,
            "pole_label": _POLE_LABEL[pole],
        }

    # --- look up type definition ---
    echo_entry = ECHO_TYPES.get(code, {})
    type_name = echo_entry.get("name", code)
    group = echo_entry.get("group", "")
    group_code = echo_entry.get("group_code", "")
    traits = echo_entry.get("traits", [])

    # --- features / metadata ---
    features = {
        "session_count": session_count,
        "total_turns": total_turns,
        "user_message_count": len(user_messages),
        "agent_message_count": len(agent_messages),
        "heartbeat_activity_level": heartbeat_activity_level,
        "tool_self_initiated_ratio": tool_self_initiated_ratio,
        "cron_proactivity_score": cron_proactivity_score,
        "installed_skills_count": installed_skills_count,
        "memory_depth": memory_depth,
    }

    return {
        "code": code,
        "name": type_name,
        "group": group,
        "group_code": group_code,
        "dims": dims,
        "scores": {k: round(v, 4) for k, v in scores.items()},
        "traits": list(traits) if isinstance(traits, (list, tuple)) else
                  [t.strip() for t in str(traits).split("，") if t.strip()],
        "features": features,
    }


# ---------------------------------------------------------------------------
# Public API: compute_echo_profile()  — backward-compatible wrapper
# ---------------------------------------------------------------------------

def compute_echo_profile(features: dict) -> dict:
    """Backward-compatible entry-point called by profiler.py.

    v3: 新增从 features dict 中读取行为参数，不再硬编码。
    """
    # --- extract parameters from features dict ---
    soul_autonomy = safe_float(features.get("soul_autonomy"), 0.45)
    soul_specialization = safe_float(features.get("soul_specialization"), 0.5)
    soul_tone_warmth = safe_float(features.get("soul_tone_warmth"), 0.5)
    identity_vibe = safe_float(features.get("identity_vibe"), 0.5)
    emotional_word = safe_float(features.get("emotional_word"), 0.3)
    formality = safe_float(features.get("formality"), 0.5)

    session_count = int(features.get("session_count", 1))
    total_turns = int(features.get("total_turns", 0))

    agent_messages: List[str] = features.get("agent_messages", [])
    soul_text: str = features.get("soul_text", "")
    identity_text: str = features.get("identity_text", "")

    # v3 行为参数: 从 features 中读取, 缺失时传 -1 (自动降级)
    heartbeat_activity_level = safe_float(
        features.get("heartbeat_activity_level"), -1.0)
    tool_self_initiated_ratio = safe_float(
        features.get("tool_self_initiated_ratio"), -1.0)
    installed_skills_count = int(
        features.get("installed_skills_count", -1))
    topic_coverage_breadth = safe_float(
        features.get("topic_coverage_breadth"), -1.0)
    cross_domain_task_ratio = safe_float(
        features.get("cross_domain_task_ratio"), -1.0)
    tools_config_richness = safe_float(
        features.get("tools_config_richness"), -1.0)
    memory_depth = safe_float(
        features.get("memory_depth"), -1.0)
    memory_file_count = int(
        features.get("memory_file_count", -1))
    memory_date_span = int(
        features.get("memory_date_span", -1))
    agent_self_update_count = int(
        features.get("agent_self_update_count", -1))
    memory_search_count = int(
        features.get("memory_search_count", -1))
    cron_proactivity_score = safe_float(
        features.get("cron_proactivity_score"), -1.0)

    # --- build lexicon_results dict ---
    lexicon_results = {
        SOUL_AUTONOMY_KEY: soul_autonomy,
        SOUL_SPECIALIZATION_KEY: soul_specialization,
        SOUL_TONE_WARMTH_KEY: soul_tone_warmth,
        IDENTITY_VIBE_KEY: identity_vibe,
        EMOTIONAL_WORD_KEY: emotional_word,
        FORMALITY_KEY: formality,
    }

    # --- compute dimensions with behavior params ---
    i_score = _compute_I(lexicon_results, agent_messages,
                         heartbeat_activity_level, tool_self_initiated_ratio,
                         cron_proactivity_score)
    s_score = _compute_S(lexicon_results,
                         installed_skills_count, topic_coverage_breadth,
                         cross_domain_task_ratio, tools_config_richness)
    t_score = _compute_T_echo(lexicon_results)
    m_score = _compute_M(agent_messages, session_count, soul_text, identity_text,
                         memory_depth, memory_file_count, memory_date_span,
                         agent_self_update_count, memory_search_count)

    scores = {"I": i_score, "S": s_score, "T": t_score, "M": m_score}
    code = _encode(scores)

    # --- look up type info ---
    echo_entry = ECHO_TYPES.get(code, {})
    type_name_zh = echo_entry.get("name_zh", echo_entry.get("name", code))
    type_name_en = echo_entry.get("name_en", echo_entry.get("name", code))

    # --- dimension descriptions ---
    _DIM_DESCRIPTIONS = {
        "I": {
            "R": "Reactive — responds when prompted, follows user lead",
            "P": "Proactive — initiates suggestions, anticipates needs",
        },
        "S": {
            "S": "Specialist — deep expertise in narrow domains",
            "G": "Generalist — broad knowledge across many domains",
        },
        "T": {
            "F": "Functional — task-oriented, concise communication",
            "E": "Empathetic — warm, emotionally attuned communication",
        },
        "M": {
            "T": "Transient — treats each session independently",
            "C": "Continuous — maintains context across sessions",
        },
    }

    # --- confidence heuristic ---
    boundary_distances = [abs(scores[d] - 0.5) for d in ("I", "S", "T", "M")]
    # 置信度 = 0.5 + avg(各维度距边界0.5的距离); 四维都在极端时→1.0, 都在边界时→0.5
    confidence = clamp(0.5 + sum(boundary_distances) / 2.0, 0.5, 1.0)

    # --- build legacy dimensions dict ---
    dimensions: Dict[str, dict] = {}
    for dim in ("I", "S", "T", "M"):
        pole = _pole_for(dim, scores[dim])
        dimensions[dim] = {
            "score": round(scores[dim], 4),
            "pole": pole,
            "label": _POLE_LABEL[pole],
            "description": _DIM_DESCRIPTIONS[dim][pole],
        }

    return {
        "type_code": code,
        "type_name_zh": type_name_zh,
        "type_name_en": type_name_en,
        "confidence": round(confidence, 4),
        "dimensions": dimensions,
    }
