# -*- coding: utf-8 -*-
"""
SYNC Spectrum 匹配器 — 人机关系分类 (10 种类型)

根据 BOND Profile 和 ECHO Matrix 的分类结果，计算 RTAPS 五维评分
（Resonance, Tempo, Agency Balance, Precision Mesh, Synergy Index），
然后与 10 种理想关系类型做余弦相似度匹配。

纯 Python stdlib，零外部依赖。
"""
import math
from typing import Dict, List, Optional, Tuple

try:
    from .utils import clamp
except ImportError:
    from utils import clamp
try:
    from .type_definitions import SYNC_TYPES
except ImportError:
    from type_definitions import SYNC_TYPES


# ===================================================================
# 10 种关系类型的理想 RTAPS 向量
# ===================================================================
# 每个类型对应 (R, T, A, P, S) 五维理想值，值域 [0, 1]

IDEAL_RTAPS = {
    # ── 高共鸣区 ──────────────────────────────────────────────
    "Kindred Spirit": {          # 知己：深度情感共振 + 高同步 + 中等任务
        "R": 0.95, "T": 0.85, "A": 0.50, "P": 0.55, "S": 0.90,
    },
    "Confidant": {               # 知心密友：高共鸣但节奏更私密、任务性低
        "R": 0.80, "T": 0.60, "A": 0.50, "P": 0.45, "S": 0.65,
    },

    # ── 高协作区 ──────────────────────────────────────────────
    "Co-pilot": {                # 联合驾驶：双向协作、高精度、高同步
        "R": 0.55, "T": 0.70, "A": 0.50, "P": 0.80, "S": 0.80,
    },
    "Trusted Advisor": {         # 可信顾问：专业权威、高精度、较高主导
        "R": 0.45, "T": 0.65, "A": 0.70, "P": 0.90, "S": 0.70,
    },
    "Commander & Lieutenant": {  # 指挥官与副官：强主导、高精度执行
        "R": 0.30, "T": 0.70, "A": 0.85, "P": 0.85, "S": 0.75,
    },

    # ── 中间张力区 ─────────────────────────────────────────────
    "Mirror Rival": {            # 镜像对手：对等博弈、中等各维度
        "R": 0.50, "T": 0.55, "A": 0.40, "P": 0.60, "S": 0.65,
    },
    "Guardian": {                # 守护者：Agent 高度主导保护、低共鸣
        "R": 0.25, "T": 0.55, "A": 0.80, "P": 0.90, "S": 0.55,
    },
    "Expedition Partner": {      # 探险伙伴：好奇探索、中共鸣、低结构
        "R": 0.60, "T": 0.40, "A": 0.30, "P": 0.45, "S": 0.65,
    },

    # ── 低能量区 ──────────────────────────────────────────────
    "Passerby": {                # 过客：浅层接触、全维度低
        "R": 0.20, "T": 0.20, "A": 0.30, "P": 0.35, "S": 0.30,
    },
    "Hidden Reef": {             # 暗礁：潜在摩擦、精度低、同步差
        "R": 0.40, "T": 0.45, "A": 0.35, "P": 0.25, "S": 0.30,
    },
}

# RTAPS 维度全称（用于报告）
RTAPS_DIM_NAMES: Dict[str, str] = {
    "R": "Resonance (共振度)",
    "T": "Tempo (节奏度)",
    "A": "Agency Balance (主导权平衡)",
    "P": "Precision Mesh (精度啮合)",
    "S": "Synergy Index (协同涌现)",
}


# ===================================================================
# RTAPS 五维评分计算
# ===================================================================

def _extract_bond_scores(bond_result: Dict) -> Dict[str, float]:
    """
    从 bond_classifier 的输出中提取四维连续得分。

    bond_result['dimensions'] 包含 T / E / C / F 四个维度，
    每个维度有 'score' 字段，值域 [0, 1]。
    """
    dims = bond_result.get("dimensions", {})
    return {
        "T": dims.get("T", {}).get("score", 0.5),
        "E": dims.get("E", {}).get("score", 0.5),
        "C": dims.get("C", {}).get("score", 0.5),
        "F": dims.get("F", {}).get("score", 0.5),
    }


def _extract_echo_scores(echo_result: Dict) -> Dict[str, float]:
    """
    从 echo_classifier 的输出中提取四维连续得分。

    echo_result['dimensions'] 包含 I / S / T / M 四个维度，
    每个维度有 'score' 字段，值域 [0, 1]。
    """
    dims = echo_result.get("dimensions", {})
    return {
        "I": dims.get("I", {}).get("score", 0.5),
        "S": dims.get("S", {}).get("score", 0.5),
        "T": dims.get("T", {}).get("score", 0.5),
        "M": dims.get("M", {}).get("score", 0.5),
    }


def compute_rtaps(bond_result: Dict, echo_result: Dict) -> Dict[str, float]:
    """
    根据 BOND 和 ECHO 分类结果计算 RTAPS 五维评分。

    BOND 维度 (值域 [0, 1]):
        T: 0=Sprint, 1=Marathon
        E: 0=Utility, 1=Companion
        C: 0=Preview(高控制), 1=Review(低控制)
        F: 0=High-level(意图导向), 1=Detailed(精确指令)

    ECHO 维度 (值域 [0, 1]):
        I: 0=Reactive(被动), 1=Proactive(主动)
        S: 0=Specialist(专精), 1=Generalist(通才)
        T: 0=Functional(功能), 1=Empathetic(共情)
        M: 0=Transient(瞬时), 1=Continuous(持续)

    返回:
        dict of {R, T, A, P, S} -> float, 每个值域 [0, 1]
    """
    bond = _extract_bond_scores(bond_result)
    echo = _extract_echo_scores(echo_result)

    bond_E = bond["E"]  # 0=Utility, 1=Companion
    echo_T = echo["T"]  # 0=Functional, 1=Empathetic
    bond_T = bond["T"]  # 0=Sprint, 1=Marathon
    echo_M = echo["M"]  # 0=Transient, 1=Continuous
    bond_C = bond["C"]  # 0=Preview(高控制), 1=Review(低控制)
    echo_I = echo["I"]  # 0=Reactive(被动), 1=Proactive(主动)
    bond_F = bond["F"]  # 0=High-level, 1=Detailed
    echo_S = echo["S"]  # 0=Specialist, 1=Generalist

    # ------------------------------------------------------------------
    # R (Resonance 共振度) — 情感温度匹配
    #   bond_E 和 echo_T 的接近程度, 同时考虑强度
    #   "双高"匹配 (两边都有情感) 比 "双低" (两边都冷) 得分更高
    # ------------------------------------------------------------------
    proximity_R = 1.0 - abs(bond_E - echo_T)
    intensity_R = (bond_E + echo_T) / 2.0      # 双高=高, 双低=低
    R = clamp(0.6 * proximity_R + 0.4 * intensity_R)

    # ------------------------------------------------------------------
    # T (Tempo 节奏度) — 时间投入匹配
    #   bond_T 和 echo_M 的接近程度, 加入强度因子
    #   "双长期"匹配比"双短期"得分更高
    # ------------------------------------------------------------------
    proximity_T = 1.0 - abs(bond_T - echo_M) * 0.8
    intensity_T = (bond_T + echo_M) / 2.0
    T = clamp(0.65 * proximity_T + 0.35 * intensity_T)

    # ------------------------------------------------------------------
    # A (Agency Balance 主导权平衡) — 权力分配
    #   bond_C 和 echo_I 的互补程度
    #   用户想控制(C低=Preview) + agent被动(I低) = 好匹配
    #   用户放手(C高=Review) + agent主动(I高) = 好匹配
    # ------------------------------------------------------------------
    complementarity_A = 1.0 - abs(bond_C - (1.0 - echo_I))
    clarity_A = max(abs(bond_C - 0.5), abs(echo_I - 0.5)) * 0.5  # 清晰度奖励
    A = clamp(0.75 * complementarity_A + 0.25 * clarity_A)

    # ------------------------------------------------------------------
    # P (Precision Mesh 精度啮合) — 认知对接
    #   详细用户配专精agent, 概括用户配通才agent
    #   bond_F 高(Detailed) 配 echo_S 低(Specialist)
    #   bond_F 低(High-level) 配 echo_S 高(Generalist)
    # ------------------------------------------------------------------
    complementarity_P = 1.0 - abs(bond_F - (1.0 - echo_S)) * 0.9
    clarity_P = max(abs(bond_F - 0.5), abs(echo_S - 0.5)) * 0.4
    P = clamp(0.7 * complementarity_P + 0.3 * clarity_P)

    # ------------------------------------------------------------------
    # S (Synergy Index 协同涌现) — 整体关系质量
    #   前四维的加权平均
    # ------------------------------------------------------------------
    S = clamp(0.3 * R + 0.25 * T + 0.2 * A + 0.25 * P)

    return {
        "R": round(R, 4),
        "T": round(T, 4),
        "A": round(A, 4),
        "P": round(P, 4),
        "S": round(S, 4),
    }


# ===================================================================
# 余弦相似度匹配
# ===================================================================

def _cosine_similarity(vec_a: Dict[str, float],
                       vec_b: Dict[str, float]) -> float:
    """
    计算两个 RTAPS 向量之间的余弦相似度。

    使用 math.sqrt，纯 stdlib 实现。
    """
    keys = ["R", "T", "A", "P", "S"]

    dot = 0.0
    norm_a = 0.0
    norm_b = 0.0

    for k in keys:
        a = vec_a.get(k, 0.0)
        b = vec_b.get(k, 0.0)
        dot += a * b
        norm_a += a * a
        norm_b += b * b

    denom = math.sqrt(norm_a) * math.sqrt(norm_b)

    if denom < 1e-12:
        return 0.0

    return dot / denom


def _euclidean_similarity(vec_a: Dict[str, float], vec_b: Dict[str, float]) -> float:
    """欧氏距离转相似度: sim = 1 / (1 + dist)"""
    dims = set(vec_a.keys()) | set(vec_b.keys())
    sq_sum = sum((vec_a.get(d, 0) - vec_b.get(d, 0)) ** 2 for d in dims)
    return 1.0 / (1.0 + math.sqrt(sq_sum))


def _rank_all_types(rtaps: Dict[str, float]) -> List[Tuple[str, float]]:
    """
    对所有 10 种关系类型计算余弦相似度，按降序排列。

    返回:
        [(type_code, similarity), ...] 长度 10，从高到低排序
    """
    rankings = []
    for code, ideal_vec in IDEAL_RTAPS.items():
        cos_sim = _cosine_similarity(rtaps, ideal_vec)
        euc_sim = _euclidean_similarity(rtaps, ideal_vec)
        # 混合评分: 余弦相似度(方向) + 欧氏相似度(绝对距离), 偏重欧氏
        hybrid = 0.4 * cos_sim + 0.6 * euc_sim
        rankings.append((code, round(hybrid, 4)))

    rankings.sort(key=lambda x: x[1], reverse=True)
    return rankings


# ===================================================================
# 类型信息组装
# ===================================================================

def _build_type_info(code: str, similarity: float) -> Dict:
    """
    从 type_definitions.SYNC_TYPES 获取类型详细信息并组装输出结构。

    SYNC_TYPES[code] 的可用字段:
        name      — 中文名 (如 "知己")
        en_name   — 英文名 (如 "Confidant")
        desc      — 描述
        keywords  — 关键词/特质标签

    输出:
        {
            code, name, name_en, similarity,
            description, quote, traits
        }

    其中 quote 取自 desc (作为引言摘要)，traits 取自 keywords。
    """
    type_def = SYNC_TYPES.get(code)

    if type_def is None:
        return {
            "code": code,
            "name": code,
            "name_en": code,
            "similarity": similarity,
            "description": "",
            "quote": "",
            "traits": "",
        }

    return {
        "code": code,
        "name": type_def.get("name", code),
        "name_en": type_def.get("en_name", code),
        "similarity": similarity,
        "description": type_def.get("desc", ""),
        "quote": type_def.get("desc", ""),
        "traits": type_def.get("keywords", ""),
    }


# ===================================================================
# 主分类入口
# ===================================================================

def classify(bond_result: Dict, echo_result: Dict) -> Dict:
    """
    SYNC Spectrum 完整分类流程。

    输入:
        bond_result: bond_classifier 的输出 dict
            须含 'dimensions' -> {T, E, C, F} -> {'score': float}
        echo_result: echo_classifier 的输出 dict
            须含 'dimensions' -> {I, S, T, M} -> {'score': float}

    输出:
        {
            "rtaps": {R, T, A, P, S} -> float,
            "primary": {
                code, name, name_en, similarity,
                description, quote, traits
            },
            "secondary": {... same structure ...} or None,
            "rankings": [(code, name, similarity), ...] top 5
        }
    """
    # 1. 计算 RTAPS 五维评分
    rtaps = compute_rtaps(bond_result, echo_result)

    # 2. 余弦相似度排序
    all_rankings = _rank_all_types(rtaps)

    # 3. 组装 primary
    primary_code, primary_sim = all_rankings[0]
    primary = _build_type_info(primary_code, primary_sim)

    # 4. 组装 secondary（如果存在第二名）
    secondary = None
    if len(all_rankings) > 1:
        sec_code, sec_sim = all_rankings[1]
        secondary = _build_type_info(sec_code, sec_sim)

    # 5. 组装 top-5 rankings: [(code, name, similarity), ...]
    top5 = []
    for code, sim in all_rankings[:5]:
        type_def = SYNC_TYPES.get(code, {})
        name = type_def.get("name", code)
        top5.append((code, name, sim))

    return {
        "rtaps": rtaps,
        "primary": primary,
        "secondary": secondary,
        "rankings": top5,
    }


# ===================================================================
# 兼容入口: run_sync_spectrum
# ===================================================================
# 保持与 profiler.py 中 `from sync_matcher import run_sync_spectrum`
# 调用方式的兼容性。

def run_sync_spectrum(bond_profile: Dict, echo_profile: Dict) -> Dict:
    """
    完整的 SYNC Spectrum 分析（兼容旧接口）。

    参数:
        bond_profile: compute_bond_profile() 的返回值
        echo_profile: compute_echo_profile() 的返回值

    返回:
        与 classify() 相同的结构，额外附带:
            bond_type: str  — BOND 四字母编码
            echo_type: str  — ECHO 四字母编码
            primary_type: dict  — 兼容旧接口的 primary 信息
            secondary_type: dict or None
            all_fits: list  — 兼容旧接口的排名列表
            warnings: list  — 维度预警列表
    """
    result = classify(bond_profile, echo_profile)

    rtaps = result["rtaps"]

    # 兼容旧接口字段
    primary = result["primary"]
    primary_type = {
        "code": primary["code"],
        "name_zh": primary["name"],
        "name_en": primary["name_en"],
        "fit_score": primary["similarity"],
        "quote": primary["quote"],
        "description": primary["description"],
        "traits": primary["traits"],
    }

    secondary_type = None
    if result["secondary"] is not None:
        sec = result["secondary"]
        secondary_type = {
            "code": sec["code"],
            "name_zh": sec["name"],
            "name_en": sec["name_en"],
            "fit_score": sec["similarity"],
            "quote": sec["quote"],
        }

    all_fits = []
    for code, name, sim in result["rankings"]:
        all_fits.append({
            "code": code,
            "name_zh": name,
            "fit_score": sim,
        })

    # 生成预警
    warnings = []
    dim_labels = {
        "R": "共振度",
        "T": "节奏度",
        "A": "主导权平衡",
        "P": "精度啮合",
    }
    for dim in ["R", "T", "A", "P"]:
        val = rtaps[dim]
        if val < 0.4:
            warnings.append(_generate_warning(dim, dim_labels[dim], val))

    return {
        "rtaps": rtaps,
        "primary": result["primary"],
        "secondary": result["secondary"],
        "rankings": result["rankings"],
        "primary_type": primary_type,
        "secondary_type": secondary_type,
        "all_fits": all_fits,
        "bond_type": bond_profile.get("type_code", ""),
        "echo_type": echo_profile.get("type_code", ""),
        "warnings": warnings,
    }


def _generate_warning(dim: str, label: str, value: float) -> str:
    """生成维度预警信息"""
    msgs = {
        "R": "情感温度不匹配 -- 这个Agent可能无法满足你的情感需求，建议看看共情型Agent。",
        "T": "时间节奏不匹配 -- 想积累长期关系需要换延续记忆的Agent。",
        "A": "主导权分配不清晰 -- 你们可能会在\"谁主导\"上产生摩擦。",
        "P": "认知精度不对接 -- 你的指令风格和Agent能力范围有偏差，调整指令抽象度或换Agent。",
    }
    return "[!] {} ({:.2f}): {}".format(label, value, msgs.get(dim, ""))
