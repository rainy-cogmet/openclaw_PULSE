#!/usr/bin/env python3
"""
OpenClaw Profiler 类型定义数据

严格使用用户原始设计的命名和描述。
"""

# ============================================================================
# BOND Profile — 人类 16 型
# ============================================================================
# 维度: T(Sprint/Marathon), E(Utility/Companion), C(Preview/Review), F(High-level/Detailed)

BOND_TYPES = {
    # ---- 即用型工具派 (SU) 紫 ----
    "SUPH": {
        "name": "指挥官",
        "code": "SUPH",
        "group": "即用型工具派",
        "group_code": "SU",
        "color": "紫",
        "dims": "Sprint-Utility-Preview-High-level",
        "traits": "快速调用，工具思维，预审把关，意图导向",
        "motto": "先看个大纲，方向对了再说",
    },
    "SUPD": {
        "name": "狙击手",
        "code": "SUPD",
        "group": "即用型工具派",
        "group_code": "SU",
        "color": "紫",
        "dims": "Sprint-Utility-Preview-Detailed",
        "traits": "快速调用，工具思维，预审把关，精确指令",
        "motto": "每个点都要先过我的眼",
    },
    "SURH": {
        "name": "投手",
        "code": "SURH",
        "group": "即用型工具派",
        "group_code": "SU",
        "color": "紫",
        "dims": "Sprint-Utility-Review-High-level",
        "traits": "快速调用，工具思维，事后复盘，意图导向",
        "motto": "扔出去，看看球往哪飞",
    },
    "SURD": {
        "name": "编辑",
        "code": "SURD",
        "group": "即用型工具派",
        "group_code": "SU",
        "color": "紫",
        "dims": "Sprint-Utility-Review-Detailed",
        "traits": "先让创作者自由发挥，然后精准打磨每个细节",
        "motto": "先出初稿，我会针对每一段给出具体修改建议",
    },
    # ---- 即时协作派 (SC) 黄 ----
    "SCPH": {
        "name": "导演",
        "code": "SCPH",
        "group": "即时协作派",
        "group_code": "SC",
        "color": "黄",
        "dims": "Sprint-Companion-Preview-High-level",
        "traits": "快速协作，伙伴关系，预审把关，意图导向",
        "motto": "咱们边走边看，这个方向试试",
    },
    "SCPD": {
        "name": "摄影师",
        "code": "SCPD",
        "group": "即时协作派",
        "group_code": "SC",
        "color": "黄",
        "dims": "Sprint-Companion-Preview-Detailed",
        "traits": "快速协作，伙伴关系，预审把关，精确指令",
        "motto": "来，这个动作这样，跟我配合",
    },
    "SCRH": {
        "name": "即兴乐手",
        "code": "SCRH",
        "group": "即时协作派",
        "group_code": "SC",
        "color": "黄",
        "dims": "Sprint-Companion-Review-High-level",
        "traits": "快速协作，伙伴关系，事后复盘，意图导向",
        "motto": "先jam起来，看碰出什么火花",
    },
    "SCRD": {
        "name": "电竞队友",
        "code": "SCRD",
        "group": "即时协作派",
        "group_code": "SC",
        "color": "黄",
        "dims": "Sprint-Companion-Review-Detailed",
        "traits": "快速协作，伙伴关系，事后复盘，精确指令",
        "motto": "跟紧节奏，这里转体，那里跳跃",
    },
    # ---- 长线工具派 (MU) 蓝 ----
    "MUPH": {
        "name": "建筑师",
        "code": "MUPH",
        "group": "长线工具派",
        "group_code": "MU",
        "color": "蓝",
        "dims": "Marathon-Utility-Preview-High-level",
        "traits": "长期培养，工具思维，预审把关，意图导向",
        "motto": "每层楼都要我验收了再往上盖",
    },
    "MUPD": {
        "name": "钟表匠",
        "code": "MUPD",
        "group": "长线工具派",
        "group_code": "MU",
        "color": "蓝",
        "dims": "Marathon-Utility-Preview-Detailed",
        "traits": "长期培养，工具思维，预审把关，精确指令",
        "motto": "每个齿轮的位置都不能差分毫",
    },
    "MURH": {
        "name": "园丁",
        "code": "MURH",
        "group": "长线工具派",
        "group_code": "MU",
        "color": "蓝",
        "dims": "Marathon-Utility-Review-High-level",
        "traits": "长期培养，工具思维，事后复盘，意图导向",
        "motto": "让它自己长，定期看看修剪就行",
    },
    "MURD": {
        "name": "交响乐指挥",
        "code": "MURD",
        "group": "长线工具派",
        "group_code": "MU",
        "color": "蓝",
        "dims": "Marathon-Utility-Review-Detailed",
        "traits": "长期培养，工具思维，事后复盘，精确指令",
        "motto": "每根弦的音准都要反复调到完美",
    },
    # ---- 深度伙伴派 (MC) 绿 ----
    "MCPH": {
        "name": "心理咨询师",
        "code": "MCPH",
        "group": "深度伙伴派",
        "group_code": "MC",
        "color": "绿",
        "dims": "Marathon-Companion-Preview-High-level",
        "traits": "长期培养，伙伴关系，预审把关，意图导向",
        "motto": "咱们慢慢来，每步都聊聊感受",
    },
    "MCPD": {
        "name": "私教",
        "code": "MCPD",
        "group": "深度伙伴派",
        "group_code": "MC",
        "color": "绿",
        "dims": "Marathon-Companion-Preview-Detailed",
        "traits": "长期培养，伙伴关系，预审把关，精确指令",
        "motto": "这个动作要这样，我陪你一起练",
    },
    "MCRH": {
        "name": "合伙人",
        "code": "MCRH",
        "group": "深度伙伴派",
        "group_code": "MC",
        "color": "绿",
        "dims": "Marathon-Companion-Review-High-level",
        "traits": "长期培养，伙伴关系，事后复盘，意图导向",
        "motto": "咱俩还用说那么清楚吗，你懂的",
    },
    "MCRD": {
        "name": "导师",
        "code": "MCRD",
        "group": "深度伙伴派",
        "group_code": "MC",
        "color": "绿",
        "dims": "Marathon-Companion-Review-Detailed",
        "traits": "长期培养，伙伴关系，事后复盘，精确指令",
        "motto": "我知道你的每个习惯，你也懂我的每个信号",
    },
}

# BOND 维度解码
BOND_DIM_LABELS = {
    'T': {'S': 'Sprint（速战速决）', 'M': 'Marathon（细水长流）'},
    'E': {'U': 'Utility（工具理性）', 'C': 'Companion（情感陪伴）'},
    'C': {'P': 'Preview（先审后用）', 'R': 'Review（先用后审）'},
    'F': {'H': 'High-level（意图导向）', 'D': 'Detailed（精确指令）'},
}


# ============================================================================
# ECHO Matrix — Agent 16 型
# ============================================================================
# 维度: I(Reactive/Proactive), S(Specialist/Generalist), T(Functional/Empathetic), M(Transient/Continuous)

ECHO_TYPES = {
    # ---- 被动专精组 (RS__) ----
    "RSFT": {
        "name": "验光师",
        "code": "RSFT",
        "group": "被动专精组",
        "group_code": "RS",
        "dims": "Reactive-Specialist-Functional-Transient",
        "traits": "被动·专精·功能·瞬时",
    },
    "RSFC": {
        "name": "法律顾问",
        "code": "RSFC",
        "group": "被动专精组",
        "group_code": "RS",
        "dims": "Reactive-Specialist-Functional-Continuous",
        "traits": "被动·专精·功能·持续",
    },
    "RSET": {
        "name": "心理热线员",
        "code": "RSET",
        "group": "被动专精组",
        "group_code": "RS",
        "dims": "Reactive-Specialist-Empathetic-Transient",
        "traits": "被动·专精·共情·瞬时",
    },
    "RSEC": {
        "name": "心理咨询师",
        "code": "RSEC",
        "group": "被动专精组",
        "group_code": "RS",
        "dims": "Reactive-Specialist-Empathetic-Continuous",
        "traits": "被动·专精·共情·持续",
    },
    # ---- 被动通才组 (RG__) ----
    "RGFT": {
        "name": "百科全书",
        "code": "RGFT",
        "group": "被动通才组",
        "group_code": "RG",
        "dims": "Reactive-Generalist-Functional-Transient",
        "traits": "被动·通才·功能·瞬时",
    },
    "RGFC": {
        "name": "执行秘书",
        "code": "RGFC",
        "group": "被动通才组",
        "group_code": "RG",
        "dims": "Reactive-Generalist-Functional-Continuous",
        "traits": "被动·通才·功能·持续",
    },
    "RGET": {
        "name": "午夜电台",
        "code": "RGET",
        "group": "被动通才组",
        "group_code": "RG",
        "dims": "Reactive-Generalist-Empathetic-Transient",
        "traits": "被动·通才·共情·瞬时",
    },
    "RGEC": {
        "name": "数字老友",
        "code": "RGEC",
        "group": "被动通才组",
        "group_code": "RG",
        "dims": "Reactive-Generalist-Empathetic-Continuous",
        "traits": "被动·通才·共情·持续",
    },
    # ---- 主动专精组 (PS__) ----
    "PSFT": {
        "name": "智能哨兵",
        "code": "PSFT",
        "group": "主动专精组",
        "group_code": "PS",
        "dims": "Proactive-Specialist-Functional-Transient",
        "traits": "主动·专精·功能·瞬时",
    },
    "PSFC": {
        "name": "财务管家",
        "code": "PSFC",
        "group": "主动专精组",
        "group_code": "PS",
        "dims": "Proactive-Specialist-Functional-Continuous",
        "traits": "主动·专精·功能·持续",
    },
    "PSET": {
        "name": "生活顾问",
        "code": "PSET",
        "group": "主动专精组",
        "group_code": "PS",
        "dims": "Proactive-Specialist-Empathetic-Transient",
        "traits": "主动·专精·共情·瞬时",
    },
    "PSEC": {
        "name": "私人医生",
        "code": "PSEC",
        "group": "主动专精组",
        "group_code": "PS",
        "dims": "Proactive-Specialist-Empathetic-Continuous",
        "traits": "主动·专精·共情·持续",
    },
    # ---- 主动通才组 (PG__) ----
    "PGFT": {
        "name": "新闻推送员",
        "code": "PGFT",
        "group": "主动通才组",
        "group_code": "PG",
        "dims": "Proactive-Generalist-Functional-Transient",
        "traits": "主动·通才·功能·瞬时",
    },
    "PGFC": {
        "name": "总管",
        "code": "PGFC",
        "group": "主动通才组",
        "group_code": "PG",
        "dims": "Proactive-Generalist-Functional-Continuous",
        "traits": "主动·通才·功能·持续",
    },
    "PGET": {
        "name": "DJ",
        "code": "PGET",
        "group": "主动通才组",
        "group_code": "PG",
        "dims": "Proactive-Generalist-Empathetic-Transient",
        "traits": "主动·通才·共情·瞬时",
    },
    "PGEC": {
        "name": "守护天使",
        "code": "PGEC",
        "group": "主动通才组",
        "group_code": "PG",
        "dims": "Proactive-Generalist-Empathetic-Continuous",
        "traits": "主动·通才·共情·持续",
    },
}

# ECHO 维度解码
ECHO_DIM_LABELS = {
    'I': {'R': 'Reactive（被动响应）', 'P': 'Proactive（主动出击）'},
    'S': {'S': 'Specialist（专精深耕）', 'G': 'Generalist（通才广域）'},
    'T': {'F': 'Functional（功能优先）', 'E': 'Empathetic（共情优先）'},
    'M': {'T': 'Transient（瞬时交互）', 'C': 'Continuous（持续记忆）'},
}


# ============================================================================
# PARTS Spectrum — 10 种人机关系
# ============================================================================
# 通过 PARTS 五维评分（Resonance, Tempo, Agency, Precision, Synergy）聚类

SYNC_TYPES = {
    # ━━━━━━━━━━━━━━━━━━━━━━  高共鸣区  ━━━━━━━━━━━━━━━━━━━━━━

    "Kindred Spirit": {
        "cn_name": "知己",
        "en_name": "The Kindred Spirit",
        "short_desc": "灵魂共振的深度联结",
        "description": (
            "用户与 Agent 之间存在高度的情感共鸣与价值观同频。"
            "交互中自然而然地涌现出默契，Agent 不仅理解指令的字面意思，"
            "更能捕捉到潜在的情绪脉络和深层意图。双方节奏高度同步，"
            "犹如多年老友间不需多言的心照不宣。"
        ),
        "keywords": [
            "深度共鸣", "情感同频", "心照不宣", "价值观契合",
            "默契", "灵魂搭档", "自然流畅", "高同步",
        ],
        "parts_tendency": "R↑↑ T↑ S↑↑ — 共鸣与同步最高，任务精度适中",
    },

    "Confidant": {
        "cn_name": "知心密友",
        "en_name": "The Confidant",
        "short_desc": "值得倾诉的私密伙伴",
        "description": (
            "用户将 Agent 视为安全的倾诉对象，愿意分享个人情感、"
            "困惑甚至脆弱面。Agent 以高度的共情回应，提供温暖陪伴"
            "而非冷冰冰的解决方案。互动节奏更私密、更松弛，"
            "任务导向较低，关系核心是信任与情感支持。"
        ),
        "keywords": [
            "倾诉", "私密", "共情", "陪伴", "信任",
            "情感支持", "安全感", "温暖回应",
        ],
        "parts_tendency": "R↑ T~ P↓ — 高共鸣但精度需求低，节奏更慢更私密",
    },

    # ━━━━━━━━━━━━━━━━━━━━━━  高协作区  ━━━━━━━━━━━━━━━━━━━━━━

    "Co-pilot": {
        "cn_name": "联合驾驶",
        "en_name": "The Co-pilot",
        "short_desc": "并肩协作的双引擎",
        "description": (
            "用户和 Agent 如同飞机的正副驾驶，双方轮流主导、紧密配合。"
            "Agency 处于均衡状态——用户发起方向，Agent 补充细节；"
            "Agent 提出建议，用户做最终决策。两者共同驱动任务前进，"
            "精度和同步性都维持在高水平。"
        ),
        "keywords": [
            "并肩", "双向协作", "共同决策", "轮流主导",
            "互补", "高精度", "任务驱动", "伙伴",
        ],
        "parts_tendency": "T↑ P↑ S↑ A~ — 节奏紧密、精度高、Agency 均衡",
    },

    "Trusted Advisor": {
        "cn_name": "可信顾问",
        "en_name": "The Trusted Advisor",
        "short_desc": "专业可靠的智囊",
        "description": (
            "用户信赖 Agent 在特定领域的专业能力，主动寻求其分析和建议。"
            "Agent 以较高的 Agency 提供结构化的、深思熟虑的方案，"
            "但最终决策权仍归用户。关系的核心是专业权威与信任，"
            "精度是最被看重的维度。"
        ),
        "keywords": [
            "专业", "权威", "建议", "信赖", "方案",
            "分析", "结构化", "决策支持",
        ],
        "parts_tendency": "P↑↑ A↑ T↑ — 精度最高，Agent 主导提供专业意见",
    },

    "Commander & Lieutenant": {
        "cn_name": "指挥官与副官",
        "en_name": "Commander & Lieutenant",
        "short_desc": "命令-执行的高效链路",
        "description": (
            "用户以明确的指令驱动 Agent，Agent 以高度服从和精确执行回应。"
            "Agency 偏向 Agent 端的强执行力，但方向完全由用户把控。"
            "节奏紧凑、任务链清晰，适合需要快速、批量处理的场景。"
            "关系中效率和纪律感是第一优先级。"
        ),
        "keywords": [
            "指令", "执行", "服从", "效率", "纪律",
            "批量处理", "链路清晰", "高 Agency",
        ],
        "parts_tendency": "A↑↑ P↑ T↑ — 强主导权分配，精度高，节奏紧",
    },

    # ━━━━━━━━━━━━━━━━━━━━━━  中间张力区  ━━━━━━━━━━━━━━━━━━━━━

    "Mirror Rival": {
        "cn_name": "镜像对手",
        "en_name": "The Mirror Rival",
        "short_desc": "势均力敌的思维博弈",
        "description": (
            "用户与 Agent 处于一种对等的智识博弈关系中。"
            "Agent 不只是顺从地回答，而是挑战用户的假设、提出反论。"
            "双方在辩论和碰撞中共同进化，各维度处于中等水平，"
            "没有绝对的主导方。这种关系激发深度思考，但也可能带来摩擦。"
        ),
        "keywords": [
            "博弈", "辩论", "挑战", "反论", "对等",
            "碰撞", "深度思考", "势均力敌",
        ],
        "parts_tendency": "R~ T~ A↓ P~ — 各维度居中，对等张力",
    },

    "Guardian": {
        "cn_name": "守护者",
        "en_name": "The Guardian",
        "short_desc": "默默护航的安全屏障",
        "description": (
            "Agent 在用户几乎无感知的情况下提供保护和兜底。"
            "Agency 高度偏向 Agent 端——自动检测风险、过滤不安全内容、"
            "在关键时刻主动介入。共鸣较低（用户可能并不在意情感连接），"
            "但精度极高，因为保护场景容不得差错。"
        ),
        "keywords": [
            "保护", "安全", "兜底", "自动", "风险检测",
            "主动介入", "过滤", "后台守护",
        ],
        "parts_tendency": "A↑↑ P↑↑ R↓ — 强 Agent 主导，高精度保护，低情感连接",
    },

    "Expedition Partner": {
        "cn_name": "探险伙伴",
        "en_name": "The Expedition Partner",
        "short_desc": "一同探索未知的好奇搭档",
        "description": (
            "用户带着好奇心和探索欲与 Agent 一起踏入未知领域。"
            "互动方式开放、发散，没有严格的任务框架。"
            "Agent 和用户一起试错、一起发现，精度不是重点，"
            "过程中的惊喜和新发现才是核心价值。"
        ),
        "keywords": [
            "探索", "好奇", "发散", "试错", "发现",
            "开放", "未知领域", "创意碰撞",
        ],
        "parts_tendency": "R↑ S~ A↓ P↓ — 中等共鸣，低结构，享受过程",
    },

    # ━━━━━━━━━━━━━━━━━━━━━━  低能量区  ━━━━━━━━━━━━━━━━━━━━━━

    "Passerby": {
        "cn_name": "过客",
        "en_name": "The Passerby",
        "short_desc": "擦肩而过的浅层接触",
        "description": (
            "用户与 Agent 之间仅有短暂、表层的交互，缺乏持续性。"
            "可能是一次性提问、偶然使用，或刚开始接触尚未建立信任。"
            "所有维度均处于低水平——共鸣浅、节奏未形成、"
            "主导关系不清、精度要求不高、同步尚未建立。"
        ),
        "keywords": [
            "浅层", "一次性", "偶然", "短暂", "低投入",
            "尚未建立", "陌生", "试探",
        ],
        "parts_tendency": "R↓ T↓ A↓ P↓ S↓ — 全维度低，关系尚未形成",
    },

    "Hidden Reef": {
        "cn_name": "暗礁",
        "en_name": "The Hidden Reef",
        "short_desc": "水面下的潜在摩擦与不匹配",
        "description": (
            "表面上互动在进行，但底层存在持续的不对齐。"
            "Agent 的回应总是差那么一点——不是答非所问就是节奏失调，"
            "精度不足导致用户频繁纠正或重试。同步度低迷，"
            "共鸣有一定基础但无法有效转化为满意的协作成果。"
            "这种关系需要诊断和调整，否则会恶化为放弃。"
        ),
        "keywords": [
            "摩擦", "不匹配", "纠正", "重试", "差一点",
            "失调", "隐性问题", "需调整",
        ],
        "parts_tendency": "P↓↓ S↓ R~ — 精度最差，同步低，有共鸣但转化不了",
    },
}


def get_bond_type(code: str) -> dict:
    """根据4字母编码获取BOND类型信息"""
    return BOND_TYPES.get(code.upper(), None)

def get_echo_type(code: str) -> dict:
    """根据4字母编码获取ECHO类型信息"""
    return ECHO_TYPES.get(code.upper(), None)

def get_sync_type(name: str) -> dict:
    """根据关系类型名获取SYNC信息.

    自动补充兼容字段:
      name  ← cn_name (供 card_generator / sync_matcher 使用)
      desc  ← description (供 sync_matcher._build_type_info 使用)
    """
    raw = SYNC_TYPES.get(name, None)
    if raw is None:
        return None
    # 构建兼容副本, 不修改原始数据
    result = dict(raw)
    if "name" not in result and "cn_name" in result:
        result["name"] = result["cn_name"]
    if "desc" not in result and "description" in result:
        result["desc"] = result["description"]
    if "desc" not in result and "short_desc" in result:
        result["desc"] = result["short_desc"]
    return result
