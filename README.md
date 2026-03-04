# OpenClaw PARTS Spectrum Profiler

## 概述

OpenClaw PARTS Spectrum Profiler — 人机关系测评工具。

基于 **BOND Profile**（16 种用户类型）、**ECHO Matrix**（16 种 Agent 类型）和 **PARTS Spectrum**（10 种关系类型）三层模型，对 OpenClaw 生态中的人机交互进行量化画像与关系诊断。

| 层级 | 模型 | 维度 | 输出 |
|------|------|------|------|
| 用户画像 | **BOND Profile** | T(时间投入)·E(情感投入)·C(控制偏好)·F(反馈粒度) | 16 种用户类型 |
| Agent 画像 | **ECHO Matrix** | I(主动性)·S(专精度)·T(情感色彩)·M(记忆持续) | 16 种 Agent 类型 |
| 关系诊断 | **PARTS Spectrum** | P(精度啮合)·A(主导权)·R(共振度)·T(节奏度)·S(协同涌现) | 10 种关系类型 |

**核心零外部依赖** — 分类与匹配引擎仅使用 Python 3.7+ 标准库（re, math, json, os）。图表生成功能依赖 matplotlib + numpy（可选，通过 `--no-charts` 跳过）。

---

## 快速开始

```bash
# 列出可用的演示场景
python3 profiler.py --list-scenes

# 运行单个演示场景
python3 profiler.py --demo companion_luna

# 运行所有演示场景
python3 profiler.py --demo all

# 运行所有演示（不生成图表，跳过 matplotlib 依赖）
python3 profiler.py --demo all --no-charts

# 分析 JSON 数据包
python3 profiler.py --bundle data.json -o ./reports --format both

# 分析 OpenClaw 标准目录结构
python3 profiler.py --dir /root/.openclaw/agents/main/ --format both

# 从管道读取
cat data.json | python3 profiler.py --stdin --format json
```

---

## CLI 参考

### profiler.py — 主入口

```
用法: profiler.py [OPTIONS]

输入源（互斥，必选其一）:
  --bundle FILE       JSON 数据包路径（自动检测格式）
  --dir PATH          读取目录结构（兼容 OpenClaw 标准格式）
  --demo [NAME]       运行 mock 场景（companion_luna / commander_codeforge / copilot_atlas / all）
  --stdin             从标准输入读取 JSON
  --list-scenes       列出所有可用的 demo 场景

输出选项:
  --format {markdown,json,both}   输出格式（默认: markdown）
  -o OUTDIR, --outdir OUTDIR      输出目录（默认: 当前目录）
  --no-charts                     不生成图表（跳过 matplotlib 依赖）

示例:
  python3 profiler.py --demo all
  python3 profiler.py --demo companion_luna --format both
  python3 profiler.py --bundle session.json -o output/
  python3 profiler.py --dir /root/.openclaw/agents/main/ --format json
  cat data.json | python3 profiler.py --stdin
```

---

## 输入数据格式

### 方式 1: JSON 数据包 (--bundle / --stdin)

支持 **5 种格式自动识别**：

#### 格式 A: OpenClaw 标准 Session
```json
{
  "session_id": "sess_001",
  "messages": [
    {"role": "user", "content": "你好", "timestamp": "2025-01-15T10:00:00Z"},
    {"role": "assistant", "content": "你好！有什么可以帮你的？"}
  ],
  "tool_calls": [{"name": "search", "timestamp": "2025-01-15T10:00:03Z"}]
}
```

#### 格式 B: OpenClaw Bundle
```json
{
  "name": "场景名称",
  "soul": "SOUL.md 全文内容",
  "identity": "IDENTITY.md 全文内容",
  "user": "USER.md 全文内容（可选）",
  "agents": "AGENTS.md 全文内容（可选）",
  "memory": "MEMORY.md 全文内容（可选）",
  "sessions": [
    {"session_id": "sess_001", "messages": [...], "tool_calls": [...]}
  ]
}
```

#### 格式 C: 简易消息列表
```json
{
  "user_messages": ["你好", "帮我个忙"],
  "agent_messages": ["你好！", "好的！"],
  "soul": "SOUL.md 内容（可选）",
  "identity": "IDENTITY.md 内容（可选）"
}
```

#### 格式 D: v3 Records 数组
```json
{
  "soul": "...",
  "sessions": [
    [
      {"type": "message", "role": "user", "content": "..."},
      {"type": "message", "role": "assistant", "content": "..."}
    ]
  ]
}
```

#### 格式 E: Session 数组（顶层为 list）
```json
[
  {"session_id": "s1", "messages": [...]},
  {"session_id": "s2", "messages": [...]}
]
```

---

### 方式 2: 目录结构 (--dir)

支持多种目录布局，按优先级自动查找。

#### 布局 A: 扁平结构

```
my_agent/
├── SOUL.md              # Agent 灵魂设定（必需）
├── IDENTITY.md          # Agent 身份信息（必需）
├── USER.md              # 用户画像（可选）
├── AGENTS.md            # Agent 配置（可选）
├── HEARTBEAT.md         # 心跳配置（可选）
├── TOOLS.md             # 工具配置（可选）
├── MEMORY.md            # 记忆文档（可选）
├── memory/              # 记忆文件目录（可选）
│   └── YYYY-MM-DD.md
├── skills/              # 已安装 skills（可选）
│   └── skill_name/
│       └── SKILL.md
└── sessions/            # 对话记录
    ├── session_001.json
    └── session_002.jsonl
```

#### 布局 B: OpenClaw 标准路径

```
/root/.openclaw/
└── agents/
    └── main/            # ← --dir 可指向这里，或指向包含 .openclaw/ 的父目录
        ├── SOUL.md
        ├── IDENTITY.md
        └── sessions/
            ├── sess_001.json
            └── sess_002.json
```

**路径查找优先级：**

| 优先级 | sessions 路径 | 说明 |
|--------|--------------|------|
| 1 | `<dirpath>/sessions/` | 扁平结构 |
| 2 | `<dirpath>/.openclaw/sessions/` | .openclaw 子目录 |
| 3 | `<dirpath>/.openclaw/agents/*/sessions/` | OpenClaw 标准路径（自动扫描） |

Markdown 配置文件（SOUL.md 等）同理：先查根目录 → `.openclaw/` → `.openclaw/agents/*/`。

---

## 输出格式

### Markdown 报告（默认）

生成包含以下板块的可视化报告卡片：

- **BOND Profile** — 用户类型码 + 四维度得分 + 进度条 + 特征洞察
- **ECHO Matrix** — Agent 类型码 + 四维度得分 + 进度条 + 画像描述
- **PARTS Spectrum** — 关系类型名 + PARTS 五维雷达 + 金句 + 预警信息
- **图表** — BOND/ECHO 维度柱状图 + PARTS 雷达图（需 matplotlib，可通过 `--no-charts` 跳过）

### JSON 结构化结果

```json
{
  "bond": {
    "type_code": "MCRD",
    "type_name_zh": "导师",
    "confidence": 0.85,
    "dimensions": {
      "T": {"score": 0.72, "pole": "M", "confidence": 0.88},
      "E": {"score": 0.35, "pole": "U", "confidence": 0.76},
      "C": {"score": 0.61, "pole": "R", "confidence": 0.82},
      "F": {"score": 0.45, "pole": "H", "confidence": 0.71}
    }
  },
  "echo": {
    "type_code": "PGEC",
    "type_name_zh": "守护天使",
    "dimensions": {
      "I": {"score": 0.82, "pole": "P"},
      "S": {"score": 0.65, "pole": "G"},
      "T": {"score": 0.78, "pole": "E"},
      "M": {"score": 0.71, "pole": "C"}
    }
  },
  "sync": {
    "parts": {"R": 0.78, "T": 0.85, "A": 0.67, "P": 0.64, "S": 0.74},
    "primary": {
      "code": "Co-pilot",
      "name": "联合驾驶",
      "name_en": "The Co-pilot",
      "similarity": 0.86,
      "description": "...",
      "quote": "...",
      "traits": "..."
    },
    "secondary": {"..."},
    "rankings": [["Co-pilot", "联合驾驶", 0.86], ["Kindred Spirit", "知己", 0.82], "..."],
    "warnings": []
  }
}
```

---

## 模型说明

### BOND Profile — 16 种用户类型

4 个二元维度，每个维度由 Sigmoid 连续得分 [0,1] 二分为两极：

| 维度 | A 极 (→0) | B 极 (→1) | 含义 |
|------|-----------|-----------|------|
| **T** Time | Sprint (短平快) | Marathon (长期养成) | 用户时间投入模式 |
| **E** Emotion | Utility (工具导向) | Companion (情感陪伴) | 情感投入深度 |
| **C** Control | Preview (事前预审) | Review (事后复查) | 控制偏好时机 |
| **F** Feedback | High-level (概括式) | Detailed (细粒度) | 反馈精细程度 |

**4 大族群（16 型）：**

| 族群 | 编码 | 色彩 | 特征 |
|------|------|------|------|
| 即用型工具派 | SU** | 💜 紫 | Sprint + Utility：快速调用、工具思维 |
| 即时协作派 | SC** | 💛 黄 | Sprint + Companion：快速协作、伙伴关系 |
| 长线工具派 | MU** | 💙 蓝 | Marathon + Utility：长期培养、系统构建 |
| 深度伙伴派 | MC** | 💚 绿 | Marathon + Companion：长期深度、伙伴关系 |

### ECHO Matrix — 16 种 Agent 类型

| 维度 | A 极 (→0) | B 极 (→1) | 含义 |
|------|-----------|-----------|------|
| **I** Initiative | Reactive (被动响应) | Proactive (主动出击) | Agent 主动性 |
| **S** Specialization | Specialist (专精深耕) | Generalist (通才广域) | 能力专精度 |
| **T** Tone | Functional (功能优先) | Empathetic (共情优先) | 情感色彩 |
| **M** Memory | Transient (瞬时交互) | Continuous (持续记忆) | 记忆持续性 |

**4 大族群（16 型）：** 被动专精组(RS**)、被动通才组(RG**)、主动专精组(PS**)、主动通才组(PG**)。

### PARTS Spectrum — BOND × ECHO → 10 种关系类型

**PARTS 是 BOND 与 ECHO 的关系映射层。** 将用户画像和 Agent 画像的 8 个维度交叉计算为 5 个关系维度，再与 10 种理想关系向量匹配。

#### 五维定义与计算公式

**P — Precision Mesh 精度啮合**

认知对接效率。详细用户配专精 Agent，概括用户配通才 Agent。

```
complementarity = 1.0 - |BOND_F - (1 - ECHO_S)| × 0.9
clarity = max(|BOND_F - 0.5|, |ECHO_S - 0.5|) × 0.4
P = clamp(0.7 × complementarity + 0.3 × clarity)
```

核心逻辑：BOND-F 和 ECHO-S 形成互补关系。Detailed(F→1) 配 Specialist(S→0)，High-level(F→0) 配 Generalist(S→1)。偏离中线越远，clarity 奖励越高。

**A — Agency Balance 主导权平衡**

人与 Agent 控制权分配是否清晰舒适。

```
complementarity = 1.0 - |BOND_C - (1 - ECHO_I)|
clarity = max(|BOND_C - 0.5|, |ECHO_I - 0.5|) × 0.5
A = clamp(0.75 × complementarity + 0.25 × clarity)
```

核心逻辑：用户 Preview(C→0，想控制) + Agent Reactive(I→0，被动) = 好匹配；用户 Review(C→1，放手) + Agent Proactive(I→1，主动) = 好匹配。

**R — Resonance 共振度**

情感温度与沟通语境的契合。

```
proximity = 1.0 - |BOND_E - ECHO_T|
intensity = (BOND_E + ECHO_T) / 2
R = clamp(0.6 × proximity + 0.4 × intensity)
```

核心逻辑：不仅要求 BOND-E 和 ECHO-T 接近（proximity），还奖励双方同时为高情感投入（intensity）。"双高"匹配比"双低"匹配得分更高。

**T — Tempo 节奏度**

时间投入与记忆持续的匹配。

```
proximity = 1.0 - |BOND_T - ECHO_M| × 0.8
intensity = (BOND_T + ECHO_M) / 2
T = clamp(0.65 × proximity + 0.35 × intensity)
```

核心逻辑：与 R 维度类似的匹配+强度模型。差值系数为 0.8（比 R 更宽容），"双长期"匹配比"双短期"得分更高。

**S — Synergy Index 协同涌现**

整体关系质量的加权合成。

```
S = clamp(0.3 × R + 0.25 × T + 0.2 × A + 0.25 × P)
```

权重分配：共振度(R)最高 30%，节奏度(T)和精度(P)各 25%，主导权(A)占 20%。

#### 关系匹配算法

每种关系类型定义了一个五维理想向量。匹配使用**余弦+欧氏混合相似度**：

```
hybrid = 0.4 × cosine_similarity(parts, ideal) + 0.6 × euclidean_similarity(parts, ideal)
euclidean_similarity = 1 / (1 + euclidean_distance)
```

偏重欧氏距离（60%），确保不仅方向一致，绝对距离也要接近。按 hybrid_score 降序排列，Top-1 为主关系类型，Top-2 为副关系类型。

#### 10 种关系类型

| 区域 | 关系类型 | 中文名 | PARTS 特征 | 核心语义 |
|------|---------|--------|-----------|---------|
| 高共鸣 | Kindred Spirit | 知己 | R↑↑ T↑ S↑↑ | 灵魂共振的深度联结 |
| 高共鸣 | Confidant | 知心密友 | R↑ T~ P↓ | 值得倾诉的私密伙伴 |
| 高协作 | Co-pilot | 联合驾驶 | T↑ P↑ S↑ A~ | 并肩协作的双引擎 |
| 高协作 | Trusted Advisor | 可信顾问 | P↑↑ A↑ T↑ | 专业可靠的智囊 |
| 高协作 | Commander & Lieutenant | 指挥官与副官 | A↑↑ P↑ T↑ | 命令-执行的高效链路 |
| 中间张力 | Mirror Rival | 镜像对手 | R~ T~ A↓ P~ | 势均力敌的思维博弈 |
| 中间张力 | Guardian | 守护者 | A↑↑ P↑↑ R↓ | 默默护航的安全屏障 |
| 中间张力 | Expedition Partner | 探险伙伴 | R↑ S~ A↓ P↓ | 一同探索未知的好奇搭档 |
| 低能量 | Passerby | 过客 | 全维度↓ | 擦肩而过的浅层接触 |
| 低能量 | Hidden Reef | 暗礁 | P↓↓ S↓ R~ | 水面下的潜在摩擦 |

#### 10 种关系类型的理想 PARTS 向量

```
                      P     A     R     T     S
Kindred Spirit       0.55  0.50  0.95  0.85  0.90
Confidant            0.45  0.50  0.80  0.60  0.65
Co-pilot             0.80  0.50  0.55  0.70  0.80
Trusted Advisor      0.90  0.70  0.45  0.65  0.70
Commander & Lt.      0.85  0.85  0.30  0.70  0.75
Mirror Rival         0.60  0.40  0.50  0.55  0.65
Guardian             0.90  0.80  0.25  0.55  0.55
Expedition Partner   0.45  0.30  0.60  0.40  0.65
Passerby             0.35  0.30  0.20  0.20  0.30
Hidden Reef          0.25  0.35  0.40  0.45  0.30
```

---

## 技术架构

```
输入数据 ──→ DataParser ──→ 结构化 bundle
                │
                ├──→ FeatureExtractor ──→ bond_features + echo_features
                │         ↑
                │    all_lexicons (10 个词库分析器)
                │
                ├──→ bond_classifier(bond_features) ──→ BOND Profile (用户 16 型)
                │
                ├──→ echo_classifier(echo_features) ──→ ECHO Matrix (Agent 16 型)
                │
                └──→ sync_matcher(BOND, ECHO)
                            │
                            ├── compute_parts(): BOND 4 维 × ECHO 4 维 → PARTS 5 维
                            └── _rank_all_types(): 余弦+欧氏混合匹配 → 关系 10 型
                                                      │
                                                      ↓
                                              card_generator ──→ Markdown 报告
                                              image_generator ──→ 图表 (可选)
```

### 数据流水线

1. **DataParser** 将 5 种输入格式统一标准化为内部 bundle
2. **FeatureExtractor** 从 bundle 中提取 BOND 和 ECHO 的行为特征
3. **all_lexicons** 提供 10 个词库分析器的评分（配置侧/行为侧/用户侧）
4. **bond_classifier** 将行为特征映射为 BOND 四维连续得分 → 16 型
5. **echo_classifier** 将行为特征映射为 ECHO 四维连续得分 → 16 型
6. **sync_matcher** 将 BOND+ECHO 交叉计算为 PARTS 五维 → 匹配 10 种关系类型
7. **card_generator** 将三层结果渲染为 Markdown 报告
8. **image_generator** 生成可视化图表（可选）

### 词库层（all_lexicons.py）

10 个词法分析器，支持中英文混合分词（1/2/3-gram），无需 jieba：

| 分析器 | 分析对象 | 服务于 |
|--------|---------|--------|
| SoulToneWarmthLexicon | SOUL.md | ECHO-T 情感温度 |
| SoulAutonomyLexicon | SOUL.md | ECHO-I 主动性 |
| IdentityVibeLexicon | IDENTITY.md | ECHO-T 性格感知 |
| SoulSpecializationLexicon | SOUL.md | ECHO-S 专精度 |
| EmotionalWordLexicon | Agent 消息 | ECHO-T 共情密度 |
| FormalityLexicon | Agent 消息 | ECHO-T 正式度 |
| SocialLanguageLexicon | 用户消息 | BOND-E 社交热度 |
| MessageIntentLexicon | 用户消息 | BOND-C 意图分类 |
| SelfDisclosureLexicon | 用户消息 | BOND-E 自我披露 |
| GreetingFarewellLexicon | 用户消息 | BOND-E 寒暄检测 |

---

## 文件清单

| 文件 | 说明 |
|------|------|
| profiler.py | 主 CLI 入口 |
| data_parser.py | 数据解析器（Session/Markdown/Memory/Heartbeat/Tools/Skills） |
| feature_extractor.py | 统一特征提取器 |
| bond_classifier.py | BOND Profile 分类器 |
| echo_classifier.py | ECHO Matrix 分类器 |
| sync_matcher.py | PARTS Spectrum 匹配器（含 `compute_parts()` 和 `run_parts_spectrum()`） |
| card_generator.py | Markdown 报告生成器 |
| image_generator.py | 图表生成器（matplotlib + numpy，可选） |
| all_lexicons.py | 词库层（10 个词法分析器） |
| type_definitions.py | 类型定义（BOND 16 型 / ECHO 16 型 / PARTS 10 型） |
| utils.py | 通用工具（sigmoid、分词、多样性指标） |
| mock_scenarios.py | 内置 Mock 演示场景 |
| \_\_init\_\_.py | 包入口（导出 run_profile, FeatureExtractor 等） |
| SKILL.md | OpenClaw Skill 格式文档 |
| CHANGELOG_v31.md | v3.1 更新日志 |
| README.md | 本文件 |
| images/ | 预生成的 BOND/ECHO 类型图片（32 张） |

---

## 环境要求

| 项目 | 要求 |
|------|------|
| Python | ≥ 3.7 |
| 核心依赖 | 无（仅 stdlib: re, math, json, os） |
| 图表依赖 | matplotlib, numpy（可选，`--no-charts` 跳过） |
| 内存 | < 50 MB |
| 运行时间 | 单场景 < 0.1s（不含图表生成） |

---

## 使用示例

### 示例 1: 分析 OpenClaw 标准目录

```bash
# 直接指向 agent 目录
python3 profiler.py --dir /root/.openclaw/agents/main/ -o ./results --format both

# 指向包含 .openclaw/ 的项目根目录（自动搜索 .openclaw/agents/*/sessions/）
python3 profiler.py --dir ~/my_project/ -o ./results --format both
```

### 示例 2: 管道集成

```bash
curl -s https://api.example.com/openclaw/data | python3 profiler.py --stdin --format json
```

### 示例 3: 运行内置演示

```bash
python3 profiler.py --demo all -o ./demo_output --format both
```

演示包含 3 个典型场景：

| 场景 | 用户风格 | Agent 风格 | 预期关系 |
|------|---------|-----------|---------|
| companion_luna | 深度伙伴派 (MC) | 温暖共情型 (PG\*E/C) | 知己 / 知心密友 |
| commander_codeforge | 工具效率派 (SU) | 专精技术型 (RS\*\*) | 可信顾问 / 镜像对手 |
| copilot_atlas | 均衡协作型 (MU) | 通才适配型 (RG\*\*) | 联合驾驶 / 可信顾问 |

---

## 故障排查

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| `ModuleNotFoundError: matplotlib` | 未安装图表依赖 | `pip install matplotlib numpy` 或使用 `--no-charts` |
| `ModuleNotFoundError` (其他) | 脚本路径未正确设置 | 确保从仓库根目录运行 |
| BOND 四维度全部相同 | 输入 session 数据过少 | 增加至少 3 轮以上真实对话 |
| PARTS 结果为"过客" | 交互深度不足 | 补充更丰富的对话内容和 memory |
| JSON 解析失败 | 数据包格式错误 | 检查 sessions 数组中每条消息的 role/content 字段 |
| sessions 未被加载 | 目录结构不匹配 | 确认 sessions 在 `sessions/`、`.openclaw/sessions/` 或 `.openclaw/agents/*/sessions/` 下 |

---

## 许可证

MIT License

---

*Powered by OpenClaw PARTS Spectrum v1.0*

*理论基础: Dryer & Horowitz (1997), Edwards (1991/2008), Fiske (1992/2002), Furr (2008)*
