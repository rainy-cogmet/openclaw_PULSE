# OpenClaw SYNC Spectrum Profiler

## 概述

OpenClaw SYNC Spectrum Profiler — 人机关系测评工具。

基于 **BOND Profile**（16 种用户类型）、**ECHO Matrix**（16 种 Agent 类型）和
**SYNC Spectrum**（10 种关系类型）三层模型，对 OpenClaw 生态中的人机交互
进行量化画像与关系诊断。

| 层级 | 模型 | 维度 | 输出 |
|------|------|------|------|
| 用户画像 | **BOND Profile** | T(时间投入)·E(情感投入)·C(控制偏好)·F(反馈粒度) | 16 种用户类型 |
| Agent 画像 | **ECHO Matrix** | I(主动性)·S(专精度)·T(情感色彩)·M(记忆持续) | 16 种 Agent 类型 |
| 关系诊断 | **SYNC Spectrum** | R(共鸣)·T(节奏)·A(代理权)·P(精确度)·S(协同) | 10 种关系类型 |

**零外部依赖** — 仅使用 Python 3.7+ 标准库（re, math, json, os），无需安装任何第三方包。

---

## 快速开始

```bash
# 列出可用的演示场景
python3 profiler.py --list-scenes

# 运行单个演示场景
python3 profiler.py --demo companion_luna

# 运行所有演示场景
python3 profiler.py --demo all

# 分析 JSON 数据包
python3 profiler.py --bundle data.json -o ./reports --format both

# 分析目录结构
python3 profiler.py --dir ./my_agent/ -o ./reports

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
  --format {markdown,json,both}
                      输出格式（默认: markdown）
  -o OUTDIR, --outdir OUTDIR
                      输出目录（默认: 当前目录）
  -h, --help          显示帮助信息

examples:
  python3 profiler.py --demo all
  python3 profiler.py --demo companion_luna --format both
  python3 profiler.py --bundle session.json -o output/
  python3 profiler.py --dir ./my_agent/ --format json
  cat data.json | python3 profiler.py --stdin
  python3 profiler.py --list-scenes

supported JSON formats:
  OpenClaw session:  {"session_id": "s1", "messages": [...]}
  OpenClaw bundle:   {"soul": "...", "sessions": [{...}]}
  Simple bundle:     {"user_messages": [...], "agent_messages": [...]}
```

---

## 输入数据格式

### 方式 1: JSON 数据包 (--bundle / --stdin)

支持 **4 种格式自动识别**：

#### 格式 A: OpenClaw 标准 Session
```json
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
    {
      "session_id": "sess_001",
      "messages": [...],
      "tool_calls": [...]
    }
  ]
}
```

#### 格式 C: 简易消息列表
```json
{
  "user_messages": ["你好", "帮我个忙"],
  "agent_messages": ["你好！", "好的！"],
  "session_count": 1,
  "total_turns": 4,
  "soul": "SOUL.md 内容（可选）",
  "identity": "IDENTITY.md 内容（可选）",
  "user_name": "用户（可选）",
  "agent_name": "Agent（可选）"
}
```

#### 格式 D: v3 Records 数组
```json
{
  "soul": "...",
  "identity": "...",
  "sessions": [
    [
      {"type": "message", "role": "user", "content": "..."},
      {"type": "message", "role": "assistant", "content": "..."}
    ]
  ]
}
```

---

### 方式 2: 目录结构 (--dir)

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
├── sessions/            # 对话记录
│   ├── session_001.json   # JSON 格式
│   ├── session_002.jsonl  # JSONL 格式
│   └── ...
└── .openclaw/          # OpenClaw 配置目录（可选）
    └── ...
```

---

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
  "bond": {
    "type_code": "MCRD",
    "type_name_zh": "...",
    "type_name_en": "...",
    "confidence": 0.85,
    "dimensions": {
      "T": {"score": 0.72, "pole": "M", "confidence": 0.88},
      "E": {"score": 0.35, "pole": "U", "confidence": 0.76},
      "C": {"score": 0.61, "pole": "R", "confidence": 0.82},
      "F": {"score": 0.45, "pole": "H", "confidence": 0.71}
    }
  },
  "echo": { ... },
  "sync": {
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

---

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

---

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

---

## 环境要求

| 项目 | 要求 |
|------|------|
| Python | ≥ 3.7 |
| 外部依赖 | 无（仅 stdlib） |
| 内存 | < 50 MB |
| 运行时间 | 单场景 < 0.1s |

---

## 测试

```bash
# 运行端到端测试（116 项）
python3 test_e2e_v31.py
```

测试覆盖：
- 3 个 Mock 场景
- 5 种 JSON 输入格式
- DataParser.parse_bundle() 直接测试
- SessionParser(dict) 直接测试
- JSON 文件 load_from_bundle 测试
- 目录结构（标准目录 + .openclaw/ 子目录）
- 边界情况（空 sessions / soul only / key alias）

---

## v3.1 更新日志

### P0 修复: OpenClaw 标准格式兼容

- **SessionParser 支持 dict 输入**: 直接接受 OpenClaw 标准 session JSON 对象
  `{"session_id": "...", "messages": [{"role": "user", "content": "..."}]}`
- **SessionParser._parse_file() JSON 自动检测**: 支持 JSON object / JSON array / JSONL 三种格式自动识别
- **新增 _parse_openclaw_session()**: 将 OpenClaw 标准 session 转换为内部 record 格式，正确处理 messages 和 tool_calls
- **DataParser.parse_bundle() 多格式支持**: 自动识别 4 种 bundle 结构:
  - A: OpenClaw 标准 `{sessions: [{session_id, messages: [...]}]}`
  - B: v3 record 数组 `{sessions: [[{type: "message", ...}]]}`
  - C: 简易消息 `{user_messages: [...], agent_messages: [...]}`
  - D: 单 session 对象 `{session_id: "...", messages: [...]}`
- **Key alias**: `soul` / `soul_text` 透明互认

### P1 修复: Profiler 全链路集成

- **profiler.py 完全重写**: run_profile() 使用 _detect_and_normalize() 统一入口
- **load_from_bundle()**: 简化为纯 JSON 加载，格式处理委托给 run_profile
- **load_from_dir()**: 优先使用 DataParser.parse_directory()，支持 .json session 文件 + .openclaw/ 子目录
- **新增 validate_bundle()**: 数据完整性验证，返回 warnings（不抛异常）
- **新增 ProfilerError**: Profiler 专用异常类
- **CLI 增强**: 新增 --list-scenes 参数，无参数时显示帮助

### 代码质量

- **Import 兼容层**: bond_classifier, sync_matcher, card_generator, feature_extractor
  均添加 try/except 支持直接运行和 -m 模块运行
- **feature_extractor.py**: `_DOMAIN_KW` 提升为模块级常量 `_DOMAIN_KEYWORDS`
- **echo_classifier.py**: 全部 magic number 添加权重来源/设计依据注释
  - EchoClassifierConfig 类 docstring 增加完整权重设计文档
  - _compute_I/S/T/M 内的归一化阈值、sigmoid 参数均添加行内注释

### 文件清单

| 文件 | 说明 |
|------|------|
| profiler.py | 主 CLI 入口 |
| data_parser.py | 数据解析器（Session/Markdown/Memory/Heartbeat/Tools/Skills） |
| bond_classifier.py | BOND Profile 分类器 |
| echo_classifier.py | ECHO Matrix 分类器 |
| sync_matcher.py | SYNC Spectrum 匹配器 |
| feature_extractor.py | 统一特征提取器 |
| card_generator.py | Markdown 报告生成器 |
| all_lexicons.py | 词库层（10 个词法分析器） |
| type_definitions.py | 类型定义 |
| utils.py | 通用工具（sigmoid、分词、多样性指标） |
| mock_scenarios.py | 内置 Mock 演示场景 |
| test_e2e_v31.py | 端到端测试（116 项） |
| SKILL.md | OpenClaw Skill 格式文档 |
| CHANGELOG_v31.md | v3.1 更新日志 |
| README.md | 本文件 |

---

## 许可证

MIT License

---

## 作者

孟昊宇

---

*Powered by OpenClaw SYNC Spectrum v1.0*

*理论基础: Dryer & Horowitz (1997), Edwards (1991/2008), Fiske (1992/2002), Furr (2008)*