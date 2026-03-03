---
name: openclaw-profiler
description: |
  OpenClaw SYNC Spectrum Profiler — 人机关系测评工具。
  基于 BOND Profile（16 种用户类型）、ECHO Matrix（16 种 Agent 类型）和
  SYNC Spectrum（10 种关系类型）三层模型，对 OpenClaw 生态中的人机交互
  进行量化画像与关系诊断。
  输入 OpenClaw 标准数据包（soul.md / identity.md / user.md / memory.md / sessions），
  输出结构化测评报告（Markdown）或 JSON 结构化结果。
  纯 Python 实现，零外部依赖（仅 stdlib: re, math, json, os）。
version: 1.0.0
tags: [openclaw, profiler, bond, echo, sync, 人机关系, 测评, 画像]
---

# OpenClaw SYNC Spectrum Profiler

## 概述

本技能将 OpenClaw 人机关系测评系统封装为可直接调用的 CLI 工具，对任意 OpenClaw Agent 与用户的交互数据进行三层量化分析：

| 层级 | 模型 | 维度 | 输出 |
|------|------|------|------|
| 用户画像 | **BOND Profile** | T(时间投入)·E(情感投入)·C(控制偏好)·F(反馈粒度) | 16 种用户类型 |
| Agent 画像 | **ECHO Matrix** | I(主动性)·S(专精度)·T(情感色彩)·M(记忆持续) | 16 种 Agent 类型 |
| 关系诊断 | **SYNC Spectrum** | R(共鸣)·T(节奏)·A(代理权)·P(精确度)·S(协同) | 10 种关系类型 |

**零外部依赖** — 仅使用 Python 3.7+ 标准库（re, math, json, os），无需安装任何第三方包。

## 目录结构

```
skills/openclaw-profiler/
├── SKILL.md              # 本文件 — 技能文档
└── scripts/              # CLI 脚本 & 核心模块
    ├── profiler.py       # 主 CLI 入口
    ├── utils.py          # 通用工具（sigmoid、分词、多样性指标）
    ├── all_lexicons.py   # 词库层（10 个词法分析器）
    ├── data_parser.py    # 数据解析器（Session/Markdown/Memory）
    ├── bond_classifier.py  # BOND Profile 分类器
    ├── echo_classifier.py  # ECHO Matrix 分类器
    ├── sync_matcher.py     # SYNC Spectrum 匹配器
    ├── card_generator.py   # Markdown 报告生成器
    └── mock_scenarios.py   # 内置 Mock 演示场景
```

## 快速开始

```bash
# 运行内置演示场景（无需任何输入数据）
python3 scripts/profiler.py --demo -v

# 分析 JSON 数据包
python3 scripts/profiler.py --bundle data.json -o ./reports --format both

# 分析目录结构
python3 scripts/profiler.py --dir ./my_agent/ -o ./reports

# 从管道读取
cat data.json | python3 scripts/profiler.py --stdin --format json
```

## CLI 参考

### profiler.py — 主入口

```
用法: profiler.py [OPTIONS]

输入源（互斥，必选其一）:
  --bundle FILE       JSON 数据包路径（单个 dict 或 dict 列表）
  --dir DIR           OpenClaw 数据目录
  --demo              运行内置 Mock 场景演示
  --stdin             从 stdin 读取 JSON 数据包

输出选项:
  -o, --output DIR    输出目录（不指定则输出到 stdout）
  --format FMT        输出格式: markdown | json | both（默认: markdown）
  -v, --verbose       输出详细分析日志
```

## 输入数据格式

### 方式 1: JSON 数据包 (--bundle / --stdin)

```json
{
  "name": "场景名称",
  "soul": "SOUL.md 全文内容",
  "identity": "IDENTITY.md 全文内容",
  "user": "USER.md 全文内容（可选）",
  "agents": "AGENTS.md 全文内容（可选）",
  "memory": "MEMORY.md 全文内容（可选）",
  "sessions": [
    {
      "session_id": "sess_001",
      "messages": [
        {"role": "user", "content": "你好", "timestamp": "2025-01-15T10:00:00Z"},
        {"role": "assistant", "content": "你好！有什么可以帮你的？", "timestamp": "2025-01-15T10:00:05Z"}
      ],
      "tool_calls": [
        {"name": "search", "timestamp": "2025-01-15T10:00:03Z"}
      ]
    }
  ]
}
```

支持传入列表以批量分析多个场景：`[{场景1}, {场景2}, ...]`

### 方式 2: 目录结构 (--dir)

```
my_agent/
├── soul.md           # Agent 灵魂设定（必需）
├── identity.md       # Agent 身份信息（必需）
├── user.md           # 用户画像（可选）
├── agents.md         # Agent 配置（可选）
├── memory.md         # 记忆文档（可选）
└── sessions/         # 对话记录
    ├── session_001.json
    └── session_002.json
```

或使用 JSONL 格式：
```
my_agent/
├── soul.md
├── identity.md
└── sessions.jsonl    # 每行一个 session JSON
```

## 输出格式

### Markdown 报告（默认）

生成包含以下板块的可视化报告卡片：

- **BOND Profile** — 用户类型码 + 四维度得分 + 中文名 + 英文名
- **ECHO Matrix** — Agent 类型码 + 四维度得分 + 中文名 + 英文名
- **SYNC Spectrum** — 关系类型名 + RTAPS 五维雷达 + 金句 + 预警信息
- **关系建议** — 基于匹配类型的互动优化建议

### JSON 结构化结果

```json
{
  "name": "场景名",
  "bond_profile": {
    "type_code": "MCRD",
    "type_name_zh": "...",
    "confidence": 0.85,
    "dimensions": {
      "T": {"score": 0.72, "pole": "M", "confidence": 0.88},
      "E": {"score": 0.35, "pole": "U", "confidence": 0.76},
      "C": {"score": 0.61, "pole": "R", "confidence": 0.82},
      "F": {"score": 0.45, "pole": "H", "confidence": 0.71}
    }
  },
  "echo_profile": { "..." },
  "sync_result": {
    "primary_type": {"name_zh": "联合驾驶", "name_en": "The Co-pilot", "quote": "..."},
    "rtaps": {"R": 3, "T": 4, "A": 3, "P": 4, "S": 4},
    "warnings": []
  },
  "metadata": {
    "session_count": 5,
    "elapsed_seconds": 0.023,
    "profiler_version": "1.0.0"
  }
}
```

## 模型说明

### BOND Profile — 16 种用户类型

4 个二元维度，每个维度由 Sigmoid 连续得分二分为两极：

| 维度 | A 极 | B 极 | 含义 |
|------|------|------|------|
| **T** Time Investment | Sprint (短平快) | Marathon (长期养成) | 用户时间投入模式 |
| **E** Emotional Engagement | Utility (工具导向) | Companion (情感陪伴) | 情感投入深度 |
| **C** Control Preference | Preview (事前预审) | Review (事后复查) | 控制偏好时机 |
| **F** Feedback Granularity | High-level (概括式) | Detailed (细粒度) | 反馈精细程度 |

### ECHO Matrix — 16 种 Agent 类型

| 维度 | A 极 | B 极 | 含义 |
|------|------|------|------|
| **I** Initiative | Responder (响应式) | Proposer (提案式) | Agent 主动性 |
| **S** Specialization | Specialist (专精) | Generalist (通才) | 能力专精度 |
| **T** Tone | Functional (功能性) | Empathetic (共情式) | 情感色彩 |
| **M** Memory | Transient (瞬时) | Continuous (延续) | 记忆持续性 |

### SYNC Spectrum — 10 种关系类型

通过 RTAPS 五维评分（Resonance, Tempo, Agency, Precision, Synergy）从 256 种 BOND×ECHO 组合映射到 10 种关系类型：

1. **知己** The Kindred Spirit — 高度共鸣的深层连接
2. **知心密友** The Confidant — 安全的情感港湾
3. **联合驾驶** The Co-pilot — 平等协作的搭档
4. **可信顾问** The Trusted Advisor — 专业领域的导师
5. **指挥官与副官** Commander & Lieutenant — 高效执行链
6. **镜像对手** The Mirror Rival — 激发成长的对照
7. **守护者** The Guardian — 默默保护的后盾
8. **探险伙伴** The Expedition Partner — 共同探索未知
9. **过客** The Passerby — 浅层短暂的交互
10. **暗礁** The Hidden Reef — 潜在摩擦的关系

## 技术架构

```
输入数据 ──→ data_parser ──→ 结构化特征
                │
                ├──→ bond_classifier ──→ BOND Profile (用户画像)
                │         ↑
                │    all_lexicons (词库分析)
                │
                ├──→ echo_classifier ──→ ECHO Matrix (Agent 画像)
                │         ↑
                │    all_lexicons (词库分析)
                │
                └──→ sync_matcher(BOND, ECHO) ──→ SYNC Spectrum (关系诊断)
                                                      │
                                                      ↓
                                              card_generator ──→ 报告
```

### 词库层（all_lexicons.py）

10 个词法分析器，支持中英文混合分词（1/2/3-gram），无需 jieba：

| 分析器 | 用途 | 服务于 |
|--------|------|--------|
| SoulToneWarmthLexicon | 温暖度检测 | ECHO-T |
| SoulAutonomyLexicon | 自主性检测 | ECHO-I |
| IdentityVibeLexicon | Agent 性格感知 | ECHO-T |
| SoulSpecializationLexicon | 专精度检测 | ECHO-S |
| EmotionalWordLexicon | 情感密度/共情 | ECHO-T |
| FormalityLexicon | 正式度检测 | ECHO-T |
| SocialLanguageLexicon | 社交语言密度 | BOND-E |
| MessageIntentLexicon | 消息意图分类 | BOND-C |
| SelfDisclosureLexicon | 自我披露深度 | BOND-E |
| GreetingFarewellLexicon | 寒暄/告别检测 | BOND-E |

## 使用示例

### 示例 1: 对单个 Agent 进行测评

```bash
# 准备数据目录
mkdir -p my_agent/sessions
echo "# Soul: My Assistant\n..." > my_agent/soul.md
echo "**Name:** MyBot\n..." > my_agent/identity.md
# 放入对话记录
cp session_logs/*.json my_agent/sessions/

# 运行测评
python3 scripts/profiler.py --dir my_agent -o ./results --format both -v
```

### 示例 2: 批量测评多个场景

```bash
# 准备 JSON 列表
cat > batch.json << 'EOF'
[
  {"name": "scene_a", "soul": "...", "identity": "...", "sessions": [...]},
  {"name": "scene_b", "soul": "...", "identity": "...", "sessions": [...]}
]
EOF

python3 scripts/profiler.py --bundle batch.json -o ./batch_results --format both
```

### 示例 3: 管道集成

```bash
# 从 API 获取数据后直接测评
curl -s https://api.example.com/openclaw/data | python3 scripts/profiler.py --stdin --format json
```

### 示例 4: 运行内置演示

```bash
python3 scripts/profiler.py --demo -v -o ./demo_output --format both
```

演示包含 3 个典型场景：
- **companion_luna** — 深度陪伴用户 × 温暖共情 Agent → 知心密友 (Confidant)
- **commander_codeforge** — 工具效率用户 × 专精技术 Agent → 可信顾问 (Trusted Advisor)
- **copilot_atlas** — 均衡协作用户 × 通才适配 Agent → 联合驾驶 (Co-pilot)

## 环境要求

| 项目 | 要求 |
|------|------|
| Python | ≥ 3.7 |
| 外部依赖 | 无（仅 stdlib） |
| 内存 | < 50 MB |
| 运行时间 | 单场景 < 0.1s |

## 故障排查

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| `ModuleNotFoundError` | 脚本路径未正确设置 | 确保从 skill 根目录运行，或 cd 到 scripts/ |
| BOND 四维度全部相同 | 输入 session 数据过少 | 增加至少 3 轮以上真实对话 |
| SYNC 结果为"过客" | 交互深度不足 | 补充更丰富的对话内容和 memory |
| JSON 解析失败 | 数据包格式错误 | 检查 sessions 数组中每条消息的 role/content 字段 |
