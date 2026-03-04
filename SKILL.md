---
name: openclaw-profiler
description: |
  OpenClaw PARTS Spectrum Profiler — 人机关系测评工具。
  基于 BOND Profile（16 种用户类型）、ECHO Matrix（16 种 Agent 类型）和
  PARTS Spectrum（10 种关系类型）三层模型，对 OpenClaw 生态中的人机交互
  进行量化画像与关系诊断。
  输入 OpenClaw 标准数据包（soul.md / identity.md / user.md / memory.md / sessions），
  输出结构化测评报告（Markdown）或 JSON 结构化结果。
  纯 Python 实现，核心逻辑零外部依赖（仅 stdlib: re, math, json, os）。
  图表生成依赖 matplotlib + numpy（可选，通过 --no-charts 跳过）。
version: 1.0.0
tags: [openclaw, profiler, bond, echo, parts, 人机关系, 测评, 画像]
---

# OpenClaw PARTS Spectrum Profiler

## 概述

本技能将 OpenClaw 人机关系测评系统封装为可直接调用的 CLI 工具，对任意 OpenClaw Agent 与用户的交互数据进行三层量化分析：

| 层级 | 模型 | 维度 | 输出 |
|------|------|------|------|
| 用户画像 | **BOND Profile** | T(时间投入)·E(情感投入)·C(控制偏好)·F(反馈粒度) | 16 种用户类型 |
| Agent 画像 | **ECHO Matrix** | I(主动性)·S(专精度)·T(情感色彩)·M(记忆持续) | 16 种 Agent 类型 |
| 关系诊断 | **PARTS Spectrum** | P(精度啮合)·A(主导权平衡)·R(共振度)·T(节奏度)·S(协同涌现) | 10 种关系类型 |

### 核心流程

```
BOND Profile (用户 4 维) ──┐
                           ├──→ PARTS 五维评分 ──→ 10 种关系类型匹配
ECHO Matrix  (Agent 4 维) ─┘
```

PARTS 是 **BOND × ECHO** 的关系映射层 —— 将用户画像和 Agent 画像的 8 个维度交叉计算为 5 个关系维度，再通过余弦+欧氏混合相似度与 10 种理想关系向量匹配。

## 目录结构

```
openclaw_haci/
├── SKILL.md                # 本文件 — 技能文档
├── README.md               # 项目说明
├── CHANGELOG_v31.md        # v3.1 更新日志
├── __init__.py             # 包入口 (导出 run_profile, FeatureExtractor 等)
├── profiler.py             # 主 CLI 入口
├── utils.py                # 通用工具（sigmoid、分词、多样性指标）
├── all_lexicons.py         # 词库层（10 个词法分析器）
├── data_parser.py          # 数据解析器（Session/Markdown/Memory/Heartbeat/Tools/Skills）
├── feature_extractor.py    # 统一特征提取器
├── bond_classifier.py      # BOND Profile 分类器
├── echo_classifier.py      # ECHO Matrix 分类器
├── sync_matcher.py         # PARTS Spectrum 匹配器
├── card_generator.py       # Markdown 报告生成器
├── image_generator.py      # 图表生成器（依赖 matplotlib + numpy）
├── type_definitions.py     # 类型定义（BOND 16 型 / ECHO 16 型 / PARTS 10 型）
├── mock_scenarios.py       # 内置 Mock 演示场景
└── images/                 # 预生成的 BOND/ECHO 类型图片
    ├── bond/               # 16 张 BOND 类型卡片
    └── echo/               # 16 张 ECHO 类型卡片
```

## 快速开始

```bash
# 列出可用的演示场景
python3 profiler.py --list-scenes

# 运行单个演示场景
python3 profiler.py --demo companion_luna

# 运行所有演示场景（不生成图表，跳过 matplotlib 依赖）
python3 profiler.py --demo all --no-charts

# 分析 JSON 数据包，同时输出 Markdown + JSON
python3 profiler.py --bundle data.json -o ./reports --format both

# 分析 OpenClaw 标准目录结构
python3 profiler.py --dir /root/.openclaw/agents/main/ --format both

# 从管道读取
cat data.json | python3 profiler.py --stdin --format json
```

## 输出渠道建议

如果用户符合以下情况之一，建议直接以飞书文档的方式推送测评结果：

1. **已安装飞书相关插件**：用户配置了 Feishu 插件或 LarkOffice MCP
2. **频繁使用飞书文档**：从用户的历史交互中观察到经常需要处理飞书文档相关任务

**操作步骤**：
1. 先生成 Markdown 格式的测评报告
2. 使用 mcporter（或对应飞书工具）创建飞书文档
3. 将报告内容写入文档并分享给用户

## CLI 参考

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
```

## 输入数据格式

### 方式 1: JSON 数据包 (--bundle / --stdin)

支持 **5 种格式自动识别**：

**格式 A — OpenClaw 标准 Session**
```json
{"session_id": "sess_001", "messages": [
    {"role": "user", "content": "你好"},
    {"role": "assistant", "content": "你好！有什么可以帮你的？"}
]}
```

**格式 B — OpenClaw Bundle**
```json
{"soul": "SOUL.md 全文", "identity": "IDENTITY.md 全文",
 "sessions": [{"session_id": "sess_001", "messages": [...]}]}
```

**格式 C — 简易消息列表**
```json
{"user_messages": ["你好"], "agent_messages": ["你好！"]}
```

**格式 D — v3 Records 数组**
```json
{"soul": "...", "sessions": [[{"type": "message", "role": "user", "content": "..."}]]}
```

**格式 E — Session 数组**（顶层为 list）
```json
[{"session_id": "s1", "messages": [...]}, {"session_id": "s2", "messages": [...]}]
```

### 方式 2: 目录结构 (--dir)

Session 路径查找优先级：

| 优先级 | 路径 | 说明 |
|--------|------|------|
| 1 | `<dir>/sessions/` | 扁平结构 |
| 2 | `<dir>/.openclaw/sessions/` | .openclaw 子目录 |
| 3 | `<dir>/.openclaw/agents/*/sessions/` | OpenClaw 标准路径 |

Markdown 配置文件（SOUL.md / IDENTITY.md / MEMORY.md 等）同理遵循此优先级。

## 输出格式

### Markdown 报告

- **BOND Profile** — 用户四字母类型码 + 四维得分 + 可视化进度条
- **ECHO Matrix** — Agent 四字母类型码 + 四维得分 + 可视化进度条
- **PARTS Spectrum** — 关系类型名 + PARTS 五维雷达 + 金句 + 预警信息
- **图表** — BOND/ECHO 维度柱状图 + PARTS 雷达图（`--no-charts` 可跳过）

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
  "echo": { "..." },
  "sync": {
    "parts": {"R": 0.78, "T": 0.85, "A": 0.67, "P": 0.64, "S": 0.74},
    "primary": {"code": "Co-pilot", "name": "联合驾驶", "similarity": 0.86},
    "warnings": []
  }
}
```

## 模型说明

### BOND Profile — 用户 16 型

4 个二元维度（Sigmoid 连续得分 [0,1]），编码为四字母类型码：

| 维度 | A 极 (→0) | B 极 (→1) | 含义 |
|------|-----------|-----------|------|
| **T** | Sprint 速战速决 | Marathon 长期养成 | 时间投入模式 |
| **E** | Utility 工具理性 | Companion 情感陪伴 | 情感投入深度 |
| **C** | Preview 事前预审 | Review 事后复查 | 控制偏好时机 |
| **F** | High-level 意图导向 | Detailed 精确指令 | 指令精细程度 |

4 大族群（16 型）：即用型工具派(SU·紫)、即时协作派(SC·黄)、长线工具派(MU·蓝)、深度伙伴派(MC·绿)。

### ECHO Matrix — Agent 16 型

| 维度 | A 极 (→0) | B 极 (→1) | 含义 |
|------|-----------|-----------|------|
| **I** | Reactive 被动响应 | Proactive 主动出击 | Agent 主动性 |
| **S** | Specialist 专精深耕 | Generalist 通才广域 | 能力专精度 |
| **T** | Functional 功能优先 | Empathetic 共情优先 | 情感色彩 |
| **M** | Transient 瞬时交互 | Continuous 持续记忆 | 记忆持续性 |

4 大族群（16 型）：被动专精组(RS)、被动通才组(RG)、主动专精组(PS)、主动通才组(PG)。

### PARTS Spectrum — 关系 10 型

**PARTS = BOND × ECHO 的关系映射层**

将 BOND 四维 (T/E/C/F) 和 ECHO 四维 (I/S/T/M) 交叉计算为 5 个关系维度：

| PARTS 维度 | 全称 | 公式来源 | 核心语义 |
|-----------|------|---------|---------|
| **P** | Precision Mesh 精度啮合 | BOND-F × ECHO-S (互补) | 指令粒度与能力范围的对接效率 |
| **A** | Agency Balance 主导权平衡 | BOND-C × ECHO-I (互补) | 人与 Agent 控制权分配是否清晰 |
| **R** | Resonance 共振度 | BOND-E × ECHO-T (匹配+强度) | 情感温度与沟通语境的契合 |
| **T** | Tempo 节奏度 | BOND-T × ECHO-M (匹配+强度) | 时间投入与记忆持续的匹配 |
| **S** | Synergy Index 协同涌现 | 0.3R + 0.25T + 0.2A + 0.25P | 整体关系质量的加权合成 |

#### PARTS 五维计算公式（实际算法）

**R (共振度) — 情感温度匹配**
```
proximity = 1.0 - |BOND_E - ECHO_T|
intensity = (BOND_E + ECHO_T) / 2
R = clamp(0.6 × proximity + 0.4 × intensity)
```
"双高"匹配（两边都有情感）比"双低"（两边都冷）得分更高。

**T (节奏度) — 时间投入匹配**
```
proximity = 1.0 - |BOND_T - ECHO_M| × 0.8
intensity = (BOND_T + ECHO_M) / 2
T = clamp(0.65 × proximity + 0.35 × intensity)
```
"双长期"匹配比"双短期"得分更高。

**A (主导权平衡) — 权力分配**
```
complementarity = 1.0 - |BOND_C - (1 - ECHO_I)|
clarity = max(|BOND_C - 0.5|, |ECHO_I - 0.5|) × 0.5
A = clamp(0.75 × complementarity + 0.25 × clarity)
```
用户 Preview(C→0) + Agent 被动(I→0) = 好匹配；用户 Review(C→1) + Agent 主动(I→1) = 好匹配。

**P (精度啮合) — 认知对接**
```
complementarity = 1.0 - |BOND_F - (1 - ECHO_S)| × 0.9
clarity = max(|BOND_F - 0.5|, |ECHO_S - 0.5|) × 0.4
P = clamp(0.7 × complementarity + 0.3 × clarity)
```
Detailed 用户(F→1) 配 Specialist Agent(S→0)；High-level 用户(F→0) 配 Generalist Agent(S→1)。

**S (协同涌现) — 整体关系质量**
```
S = clamp(0.3 × R + 0.25 × T + 0.2 × A + 0.25 × P)
```

#### 关系匹配算法

每种关系类型有一个五维理想向量 (P,A,R,T,S)，通过**余弦+欧氏混合相似度**匹配：

```
hybrid_score = 0.4 × cosine_similarity(parts, ideal) + 0.6 × euclidean_similarity(parts, ideal)
```

其中 `euclidean_similarity = 1 / (1 + euclidean_distance)`。按 hybrid_score 降序排列，取 Top-1 为主关系类型。

#### 10 种关系类型

| 区域 | 类型 | 中文名 | PARTS 特征 |
|------|------|--------|-----------|
| 高共鸣 | Kindred Spirit | 知己 | R↑↑ T↑ S↑↑ |
| 高共鸣 | Confidant | 知心密友 | R↑ T~ P↓ |
| 高协作 | Co-pilot | 联合驾驶 | T↑ P↑ S↑ A~ |
| 高协作 | Trusted Advisor | 可信顾问 | P↑↑ A↑ T↑ |
| 高协作 | Commander & Lieutenant | 指挥官与副官 | A↑↑ P↑ T↑ |
| 中间张力 | Mirror Rival | 镜像对手 | R~ T~ A↓ P~ |
| 中间张力 | Guardian | 守护者 | A↑↑ P↑↑ R↓ |
| 中间张力 | Expedition Partner | 探险伙伴 | R↑ S~ A↓ P↓ |
| 低能量 | Passerby | 过客 | 全维度↓ |
| 低能量 | Hidden Reef | 暗礁 | P↓↓ S↓ R~ |

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
                └──→ sync_matcher(BOND, ECHO) ──→ PARTS Spectrum (关系 10 型)
                            │
                            ├── compute_parts(): BOND×ECHO → 五维评分
                            └── _rank_all_types(): 余弦+欧氏混合匹配
                                                      │
                                                      ↓
                                              card_generator ──→ Markdown 报告
                                              image_generator ──→ 图表 (可选)
```

### 词库层（all_lexicons.py）

10 个词法分析器，支持中英文混合分词（1/2/3-gram），无需 jieba：

| 分析器 | 分析对象 | 服务于 |
|--------|---------|--------|
| SoulToneWarmthLexicon | SOUL.md | ECHO-T |
| SoulAutonomyLexicon | SOUL.md | ECHO-I |
| IdentityVibeLexicon | IDENTITY.md | ECHO-T |
| SoulSpecializationLexicon | SOUL.md | ECHO-S |
| EmotionalWordLexicon | Agent 消息 | ECHO-T |
| FormalityLexicon | Agent 消息 | ECHO-T |
| SocialLanguageLexicon | 用户消息 | BOND-E |
| MessageIntentLexicon | 用户消息 | BOND-C |
| SelfDisclosureLexicon | 用户消息 | BOND-E |
| GreetingFarewellLexicon | 用户消息 | BOND-E |

## 环境要求

| 项目 | 要求 |
|------|------|
| Python | ≥ 3.7 |
| 核心依赖 | 无（仅 stdlib: re, math, json, os） |
| 图表依赖 | matplotlib, numpy（可选，`--no-charts` 跳过） |
| 内存 | < 50 MB |
| 运行时间 | 单场景 < 0.1s（不含图表生成） |
