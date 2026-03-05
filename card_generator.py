# -*- coding: utf-8 -*-
"""
OpenClaw PULSE Spectrum Profiler — Markdown 报告生成器（支持图片）

从 type_definitions 获取权威类型名称和描述，
将 BOND / ECHO / SYNC 三层分类结果渲染为美观的 Markdown 测评报告。
支持 GitHub raw URL 图片引用。
"""
import datetime
from typing import Dict, Optional

try:
    from .type_definitions import (
    BOND_TYPES, ECHO_TYPES, SYNC_TYPES,
    get_bond_type, get_echo_type, get_sync_type,
    )
except ImportError:
    from type_definitions import (
    BOND_TYPES, ECHO_TYPES, SYNC_TYPES,
    get_bond_type, get_echo_type, get_sync_type,
    )

# ===================================================================
# 图片 URL 映射
# ===================================================================

# GitHub raw URL 基础路径
GITHUB_RAW_BASE = "https://raw.githubusercontent.com/rainy-cogmet/openclaw_haci/main"

# BOND 类型图片映射 (按类型码)
BOND_IMAGE_URLS = {
    # 即用型工具派 (SU) 紫
    "SUPH": f"{GITHUB_RAW_BASE}/images/SUPH.png",
    "SUPD": f"{GITHUB_RAW_BASE}/images/SUPD.png",
    "SURH": f"{GITHUB_RAW_BASE}/images/SURH.png",
    "SURD": f"{GITHUB_RAW_BASE}/images/SURD.png",
    # 即时协作派 (SC) 黄
    "SCPH": f"{GITHUB_RAW_BASE}/images/SCPH.png",
    "SCPD": f"{GITHUB_RAW_BASE}/images/SCPD.png",
    "SCRH": f"{GITHUB_RAW_BASE}/images/SCRH.png",
    "SCRD": f"{GITHUB_RAW_BASE}/images/SCRD.png",
    # 长线工具派 (MU) 蓝
    "MUPH": f"{GITHUB_RAW_BASE}/images/MUPH.png",
    "MUPD": f"{GITHUB_RAW_BASE}/images/MUPD.png",
    "MURH": f"{GITHUB_RAW_BASE}/images/MURH.png",
    "MURD": f"{GITHUB_RAW_BASE}/images/MURD.png",
    # 深度伙伴派 (MC) 绿
    "MCPH": f"{GITHUB_RAW_BASE}/images/MCPH.png",
    "MCPD": f"{GITHUB_RAW_BASE}/images/MCPD.png",
    "MCRH": f"{GITHUB_RAW_BASE}/images/MCRH.png",
    "MCRD": f"{GITHUB_RAW_BASE}/images/MCRD.png",
}

# ECHO 类型图片映射 (按类型码)
ECHO_IMAGE_URLS = {
    # RSxx 被动专精组
    "RSFT": f"{GITHUB_RAW_BASE}/images/RSFT.png",
    "RSFC": f"{GITHUB_RAW_BASE}/images/RSFC.png",
    "RSET": f"{GITHUB_RAW_BASE}/images/RSET.png",
    "RSEC": f"{GITHUB_RAW_BASE}/images/RSEC.png",
    # RGxx 被动通才组
    "RGFT": f"{GITHUB_RAW_BASE}/images/RGFT.png",
    "RGFC": f"{GITHUB_RAW_BASE}/images/RGFC.png",
    "RGET": f"{GITHUB_RAW_BASE}/images/RGET.png",
    "RGEC": f"{GITHUB_RAW_BASE}/images/RGEC.png",
    # PSxx 主动专精组
    "PSFT": f"{GITHUB_RAW_BASE}/images/PSFT.png",
    "PSFC": f"{GITHUB_RAW_BASE}/images/PSFC.png",
    "PSET": f"{GITHUB_RAW_BASE}/images/PSET.png",
    "PSEC": f"{GITHUB_RAW_BASE}/images/PSEC.png",
    # PGxx 主动通才组
    "PGFT": f"{GITHUB_RAW_BASE}/images/PGFT.png",
    "PGFC": f"{GITHUB_RAW_BASE}/images/PGFC.png",
    "PGET": f"{GITHUB_RAW_BASE}/images/PGET.png",
    "PGEC": f"{GITHUB_RAW_BASE}/images/PGEC.png",
}

def _get_bond_image(code: str) -> str:
    """获取 BOND 类型图片 URL，找不到返回空串。"""
    return BOND_IMAGE_URLS.get(code, "")

def _get_echo_image(code: str) -> str:
    """获取 ECHO 类型图片 URL，找不到返回空串。"""
    return ECHO_IMAGE_URLS.get(code, "")

def _render_image(url: str, alt: str = "图片", width: int = 400) -> str:
    """渲染 Markdown 图片标签。"""
    if not url:
        return ""
    return f'![{alt}]({url} "{alt}")'

# ===================================================================
# 格式兼容层: 旧版 profiler 传入的 dict 用 type_code/type_name_zh/dimensions 等 key,
# 新版 classify() 用 code/name/dims 等 key. 这里统一转换.
# ===================================================================

def _normalize_bond(raw: Dict) -> Dict:
    """将旧版 compute_bond_profile() 输出转换为 classify() 格式."""
    if "code" in raw:
        return raw  # 已经是新格式
    result = dict(raw)
    result["code"] = raw.get("type_code", "????")
    result["name"] = raw.get("type_name_zh", raw.get("type_code", ""))
    # 转换 dimensions -> dims (从 {T: {score:0.3, pole:'S'}} 变成 {T: 0.3} 或保持)
    old_dims = raw.get("dimensions", {})
    if old_dims and isinstance(next(iter(old_dims.values()), None), dict):
        result["dims"] = old_dims  # card_generator 的 _get_dim_score 能处理 dict
        result["scores"] = {k: v.get("score", 0.5) for k, v in old_dims.items()}
    return result


def _normalize_echo(raw: Dict) -> Dict:
    """将旧版 compute_echo_profile() 输出转换为 classify() 格式."""
    if "code" in raw:
        return raw
    result = dict(raw)
    result["code"] = raw.get("type_code", "????")
    result["name"] = raw.get("type_name_zh", raw.get("type_code", ""))
    old_dims = raw.get("dimensions", {})
    if old_dims and isinstance(next(iter(old_dims.values()), None), dict):
        result["dims"] = old_dims
        result["scores"] = {k: v.get("score", 0.5) for k, v in old_dims.items()}
    return result


def _normalize_sync(raw: Dict) -> Dict:
    """将旧版 run_PULSE_spectrum() 输出转换为 classify() 格式."""
    if "primary" in raw and "PULSE" in raw:
        # 可能已经是新格式, 但 primary_type 也可能存在
        result = dict(raw)
        if "primary" not in raw and "primary_type" in raw:
            pt = raw["primary_type"]
            result["primary"] = {
                "code": pt.get("code", ""),
                "name": pt.get("name_zh", ""),
                "name_en": pt.get("name_en", ""),
                "similarity": pt.get("fit_score", 0.0),
                "description": pt.get("description", ""),
                "quote": pt.get("quote", ""),
                "traits": pt.get("traits", ""),
            }
        return result
    # 旧格式: 只有 primary_type
    result = dict(raw)
    if "primary_type" in raw and "primary" not in raw:
        pt = raw["primary_type"]
        result["primary"] = {
            "code": pt.get("code", ""),
            "name": pt.get("name_zh", ""),
            "name_en": pt.get("name_en", ""),
            "similarity": pt.get("fit_score", 0.0),
            "description": pt.get("description", ""),
            "quote": pt.get("quote", ""),
            "traits": pt.get("traits", ""),
        }
    return result

# ===================================================================
# 常量 & 映射
# ===================================================================

# 颜色 -> Emoji
COLOR_EMOJI = {
    "紫": "💜", "purple": "💜",
    "黄": "💛", "yellow": "💛",
    "蓝": "💙", "blue": "💙",
    "绿": "💚", "green": "💚",
}

# BOND 维度全称 & 解读（双极描述）
BOND_DIM_META = {
    "T": {
        "full": "节奏偏好",
        "poles": {
            "S": ("Sprint 速战速决", "⚡", "你追求快速获得结果，偏好短平快的交互节奏"),
            "M": ("Marathon 长期养成", "🏃", "你愿意投入时间培养 Agent，看重长期协作价值"),
        },
    },
    "E": {
        "full": "关系定位",
        "poles": {
            "U": ("Utility 工具理性", "🔧", "Agent 在你眼里是精密的生产力工具"),
            "C": ("Companion 情感陪伴", "💗", "你把 Agent 当作可以倾诉、深度交流的伙伴"),
        },
    },
    "C": {
        "full": "审查节点",
        "poles": {
            "P": ("Preview 先审后用", "🔍", "你喜欢在行动前先看方案、确认方向"),
            "R": ("Review 先用后审", "📋", "你更愿意让 Agent 先跑起来，再根据结果修正"),
        },
    },
    "F": {
        "full": "指令粒度",
        "poles": {
            "H": ("High-level 意图导向", "🎯", "你倾向给出大方向，让 Agent 自由发挥细节"),
            "D": ("Detailed 精确指令", "🔬", "你习惯给出具体、精确的指令和约束条件"),
        },
    },
}

# ECHO 维度全称 & 解读（双极描述）
ECHO_DIM_META = {
    "I": {
        "full": "互动主动性",
        "poles": {
            "R": ("Reactive 被动响应", "📡", "只在收到指令时行动，忠实执行不越界"),
            "P": ("Proactive 主动出击", "🚀", "会主动建议、预判需求、补充你没想到的"),
        },
    },
    "S": {
        "full": "能力范围",
        "poles": {
            "S": ("Specialist 专精深耕", "🎯", "在特定领域有深厚积累，垂直能力突出"),
            "G": ("Generalist 通才广域", "🌐", "跨领域都能接住，广度优先于深度"),
        },
    },
    "T": {
        "full": "情感温度",
        "poles": {
            "F": ("Functional 功能优先", "⚙️", "回复简洁高效，不带多余情感色彩"),
            "E": ("Empathetic 共情优先", "💗", "能感知情绪、带有温度地回应你"),
        },
    },
    "M": {
        "full": "记忆模式",
        "poles": {
            "T": ("Transient 瞬时交互", "💨", "每次对话从零开始，不保留历史上下文"),
            "C": ("Continuous 持续记忆", "🧠", "记得你们之前聊过什么，对话之间有连贯性"),
        },
    },
}

# PULSE 五维含义
PULSE_META = {
    "R": {"full": "共振度", "desc": "情感温度与沟通语境的契合"},
    "T": {"full": "节奏感", "desc": "交互节奏与时间投入偏好的匹配"},
    "A": {"full": "主导权", "desc": "人与 Agent 控制权分配是否清晰舒适"},
    "P": {"full": "精度啮合", "desc": "指令粒度与输出精度的对接效率"},
    "S": {"full": "协同涌现", "desc": "1+1>2 合作效果的强度"},
}

# ===================================================================
# 内部工具函数
# ===================================================================

def _bar(value: float, width: int = 16) -> str:
    """将 [0, 1] 区间的分数渲染为 █░ 进度条。"""
    clamped = max(0.0, min(1.0, value))
    filled = round(clamped * width)
    return "█" * filled + "░" * (width - filled)


def _score_tag(score: float) -> str:
    """将 [0, 1] 分数转为简短文字标签。"""
    if score >= 0.8:
        return "极强"
    if score >= 0.6:
        return "偏强"
    if score >= 0.4:
        return "中等"
    if score >= 0.2:
        return "偏弱"
    return "极弱"


def _color_emoji(color: str) -> str:
    """颜色标签转 Emoji，不识别则返回空串。"""
    return COLOR_EMOJI.get(color, COLOR_EMOJI.get(str(color).lower(), ""))


def _get_dim_score(dims: Dict, key: str) -> float:
    """安全地从 dims dict 取得某维度的得分 (0-1)。"""
    val = dims.get(key, 0.5)
    if isinstance(val, dict):
        return float(val.get("score", val.get("value", 0.5)))
    return float(val)

# ===================================================================
# BOND Profile 区块
# ===================================================================

def _render_bond_section(bond_result: Dict, local_image: Optional[str] = None) -> str:
    """渲染 BOND Profile 区块（支持图片）。"""
    code = bond_result.get("code", "????")

    # 从 type_definitions 获取权威信息
    typedef = get_bond_type(code)
    if typedef:
        name = typedef["name"]
        group = typedef["group"]
        motto = typedef["motto"]
        color = typedef.get("color", "")
        traits_str = typedef.get("traits", "")
    else:
        name = bond_result.get("name", code)
        group = bond_result.get("group", "")
        motto = bond_result.get("motto", "")
        color = bond_result.get("color", "")
        traits_str = ""

    color_em = _color_emoji(color)
    dims = bond_result.get("dims", bond_result.get("scores", {}))
    input_traits = bond_result.get("traits", [])
    input_features = bond_result.get("features", [])
    
    # 获取图片
    if local_image:
        image_md = _render_image(local_image, f"{name} ({code})")
    else:
        image_url = _get_bond_image(code)
        image_md = _render_image(image_url, f"{name} ({code})")

    lines = [
        "## 🧬 你的 BOND Profile: {name} ({code}) {ce}".format(
            name=name, code=code, ce=color_em,
        ),
        "",
    ]
    
    # 添加图片（如果有）
    if image_md:
        lines.append(image_md)
        lines.append("")

    lines.append("> *{motto}*".format(motto=motto) if motto else "")
    lines.append("")

    # 维度表格
    dim_order = [("T", 0), ("E", 1), ("C", 2), ("F", 3)]
    lines.append("| 维度 | 你的倾向 | 得分 | 图示 |")
    lines.append("|:---:|:---:|:---:|:---|")

    for dim_key, idx in dim_order:
        meta = BOND_DIM_META[dim_key]
        score = _get_dim_score(dims, dim_key)

        # 从编码读取实际极性
        pole_letter = code[idx].upper()
        pole_info = meta["poles"].get(pole_letter)
        if pole_info is None:
            pole_letter = list(meta["poles"].keys())[0]
            pole_info = meta["poles"][pole_letter]

        pole_label, pole_icon, _ = pole_info
        bar = _bar(score)
        lines.append(
            "| {icon} **{full}** | {label} | `{pct:.0f}%` | {bar} |".format(
                icon=pole_icon,
                full=meta["full"],
                label=pole_label,
                pct=score * 100,
                bar=bar,
            )
        )

    # 特征描述 — 自然语言段落，不用列表
    lines.append("")
    lines.append("**你的特征**")
    lines.append("")

    feature_PULSE = []
    if traits_str:
        feature_PULSE.append(traits_str)
    if input_traits:
        feature_PULSE.append("、".join(input_traits))
    if input_features:
        feature_PULSE.append("；".join(input_features))

    if feature_PULSE:
        lines.append("你属于「{group}」——{desc}。".format(
            group=group,
            desc="。".join(feature_PULSE),
        ))
    else:
        lines.append("你属于「{group}」。".format(group=group))

    # 维度洞察段落
    lines.append("")
    for dim_key, idx in dim_order:
        meta = BOND_DIM_META[dim_key]
        pole_letter = code[idx].upper()
        pole_info = meta["poles"].get(pole_letter)
        if pole_info:
            _, _, insight = pole_info
            lines.append(insight + "。")
    lines.append("")

    return "\n".join(lines)

# ===================================================================
# ECHO Matrix 区块
# ===================================================================

def _render_echo_section(echo_result: Dict, local_image: Optional[str] = None) -> str:
    """渲染 ECHO Matrix 区块（支持图片）。"""
    code = echo_result.get("code", "????")

    typedef = get_echo_type(code)
    if typedef:
        name = typedef["name"]
        group = typedef["group"]
        traits_str = typedef.get("traits", "")
    else:
        name = echo_result.get("name", code)
        group = echo_result.get("group", "")
        traits_str = ""
    
    # 获取图片
    if local_image:
        image_md = _render_image(local_image, f"{name} ({code})")
    else:
        image_url = _get_echo_image(code)
        image_md = _render_image(image_url, f"{name} ({code})")

    dims = echo_result.get("dims", echo_result.get("scores", {}))
    input_traits = echo_result.get("traits", [])

    lines = [
        "## 🤖 Agent 的 ECHO Matrix: {name} ({code})".format(
            name=name, code=code,
        ),
        "",
    ]
    
    # 添加图片（如果有）
    if image_md:
        lines.append(image_md)
        lines.append("")

    # 维度表格
    dim_order = [("I", 0), ("S", 1), ("T", 2), ("M", 3)]
    lines.append("| 维度 | Agent 的倾向 | 得分 | 图示 |")
    lines.append("|:---:|:---:|:---:|:---|")

    for dim_key, idx in dim_order:
        meta = ECHO_DIM_META[dim_key]
        score = _get_dim_score(dims, dim_key)

        # 从编码读取实际极性
        pole_letter = code[idx].upper()
        pole_info = meta["poles"].get(pole_letter)
        if pole_info is None:
            pole_letter = list(meta["poles"].keys())[0]
            pole_info = meta["poles"][pole_letter]

        pole_label, pole_icon, _ = pole_info
        bar = _bar(score)
        lines.append(
            "| {icon} **{full}** | {label} | `{pct:.0f}%` | {bar} |".format(
                icon=pole_icon,
                full=meta["full"],
                label=pole_label,
                pct=score * 100,
                bar=bar,
            )
        )

    # 特征描述
    lines.append("")
    lines.append("**Agent 画像**")
    lines.append("")

    feature_PULSE = []
    if traits_str:
        feature_PULSE.append(traits_str)
    if input_traits:
        feature_PULSE.append("、".join(input_traits))

    if feature_PULSE:
        lines.append("这个 Agent 属于「{group}」——{desc}。".format(
            group=group,
            desc="——".join(feature_PULSE),
        ))
    else:
        lines.append("这个 Agent 属于「{group}」。".format(group=group))

    # 维度洞察
    lines.append("")
    for dim_key, idx in dim_order:
        meta = ECHO_DIM_META[dim_key]
        pole_letter = code[idx].upper()
        pole_info = meta["poles"].get(pole_letter)
        if pole_info:
            _, _, insight = pole_info
            lines.append(insight + "。")
    lines.append("")

    return "\n".join(lines)

# ===================================================================
# PULSE Spectrum 区块
# ===================================================================

def _render_sync_section(sync_result: Dict, local_image: Optional[str] = None) -> str:
    """渲染 PULSE Spectrum 区块。"""
    primary = sync_result.get("primary", sync_result.get("primary_type", {}))
    PULSE = sync_result.get("PULSE", sync_result.get("parts", {}))
    warnings = sync_result.get("warnings", [])

    sync_name = primary.get("name", primary.get("name_zh", ""))
    sync_name_en = primary.get("name_en", "")
    sync_quote = primary.get("quote", "")
    sync_desc = primary.get("description", "")
    sync_score = primary.get("similarity", primary.get("fit_score", 0.0))

    lines = [
        "## ✨ 你们的 SYNC 关系: {name}".format(name=sync_name),
        "",
    ]

    if local_image:
        image_md = _render_image(local_image, f"SYNC Relationship: {sync_name}")
        lines.append(image_md)
        lines.append("")

    if sync_quote:
        lines.append("> *{q}*".format(q=sync_quote))
        lines.append("")

    # PULSE 五维雷达（文字版）
    lines.append("### PULSE 五维雷达")
    lines.append("")
    lines.append("| 维度 | 得分 | 图示 | 含义 |")
    lines.append("|:---:|:---:|:---|:---|")

    for key in ["R", "T", "A", "P", "S"]:
        score = PULSE.get(key, 0.5)
        pct = int(score * 100)
        bar = _bar(score, 15)
        meta = PULSE_META.get(key, {})
        full = meta.get("full", key)
        desc = meta.get("desc", "")
        lines.append(
            "| **{k}** {f} | `{p}%` | {b} | {d} |".format(
                k=key, f=full, p=pct, b=bar, d=desc
            )
        )

    lines.append("")

    # 关系洞察
    lines.append("**关系洞察**")
    lines.append("")
    if sync_desc:
        lines.append(sync_desc)
        lines.append("")
    else:
        # 简单生成洞察
        lines.append(f"你们的关系是「{sync_name}」。")
        lines.append("")

    # 预警
    if warnings:
        lines.append("**⚠️ 注意事项**")
        lines.append("")
        for w in warnings:
            lines.append(f"- {w}")
        lines.append("")

    return "\n".join(lines)

# ===================================================================
# 生成完整报告
# ===================================================================

def generate_markdown_report(
    bond_result: Dict,
    echo_result: Dict,
    sync_result: Dict,
    user_name: Optional[str] = None,
    agent_name: Optional[str] = None,
    title: Optional[str] = None,
    local_images: Optional[Dict[str, str]] = None,
) -> str:
    """
    生成完整的 Markdown 测评报告。

    Args:
        bond_result: BOND Profile 分类结果
        echo_result: ECHO Matrix 分类结果
        sync_result: PULSE Spectrum 匹配结果
        user_name: 用户名称（可选）
        agent_name: Agent 名称（可选）
        title: 报告标题（可选）
        local_images: 本地图片路径字典 (可选, keys: 'bond', 'echo', 'sync')

    Returns:
        完整的 Markdown 报告字符串
    """
    # 标准化输入格式
    bond_norm = _normalize_bond(bond_result)
    echo_norm = _normalize_echo(echo_result)
    sync_norm = _normalize_sync(sync_result)

    # 标题
    if title is None:
        u = user_name or "你"
        a = agent_name or "你的 Agent"
        title = f"{u} × {a} | {datetime.date.today().isoformat()}"
    
    images = local_images or {}

    lines = [
        "# 🔮 OpenClaw PULSE Spectrum 测评报告",
        "",
        f"> {title}",
        "",
        "---",
        "",
    ]

    # 各区块
    lines.append(_render_bond_section(bond_norm, local_image=images.get('bond')))
    lines.append("---")
    lines.append("")
    lines.append(_render_echo_section(echo_norm, local_image=images.get('echo')))
    lines.append("---")
    lines.append("")
    lines.append(_render_sync_section(sync_norm, local_image=images.get('sync')))
    lines.append("---")
    lines.append("")

    # 页脚
    bond_code = bond_norm.get("code", "????")
    bond_name = bond_norm.get("name", bond_code)
    echo_code = echo_norm.get("code", "????")
    echo_name = echo_norm.get("name", echo_code)
    sync_name = sync_norm.get("primary", {}).get("name", "")

    lines.append(
        "> 你是**{b}**，你的 Agent 是**{e}**，你们之间是**{s}**般的默契。".format(
            b=bond_name, e=echo_name, s=sync_name
        )
    )
    lines.append(">")
    lines.append("> *Powered by OpenClaw PULSE Spectrum v1.0*")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("想查看更详细的解读和人格画像？看这里：https://github.com/rainy-cogmet/openclaw_PULSE/blob/main/docs/PULSE.md")

    return "\n".join(lines)

# ===================================================================
# 兼容性别名（旧版调用）
# ===================================================================

render_full_report = generate_markdown_report
