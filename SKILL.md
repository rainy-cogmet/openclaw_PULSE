---
name: openclaw-profiler
description: |
  OpenClaw PARTS Spectrum Profiler — 人机关系测评工具。
  基于 BOND Profile（16 种用户类型）、ECHO Matrix（16 种 Agent 类型）和
  PARTS Spectrum（10 种关系类型）三层模型，对 OpenClaw 生态中的人机交互
  进行量化画像与关系诊断。
  触发场景：(1) 用户要求分析人机关系或交互风格；(2) 用户要求对 Agent 或用户进行画像分类；
  (3) 用户提供了 OpenClaw 数据包（含 SOUL.md / IDENTITY.md / sessions 等）要求诊断；
  (4) 用户提及 BOND / ECHO / PARTS / HACI / 人机关系测评。
  触发关键词：BOND、ECHO、PARTS、HACI、人机关系、测评、画像、关系诊断、Profiler。
---

# OpenClaw PARTS Spectrum Profiler

人机关系测评工具。输入 OpenClaw 标准数据，输出用户画像（BOND 16 型）、Agent 画像（ECHO 16 型）、关系诊断（PARTS 10 型）。

## 何时使用

当以下任一条件满足时自动启用：

- 用户要求分析人机交互关系、协作风格或沟通模式
- 用户要求对自己或某个 Agent 进行画像/分类
- 用户提供了 OpenClaw 格式的数据包或目录，要求进行测评
- 用户提及 BOND、ECHO、PARTS、HACI、人机关系测评等关键词
- 用户询问自己与某个 Agent 的关系类型

## OpenClaw 目录结构

### Agent 工作区

```
/root/.openclaw/workspace/
├── SOUL.md              # Agent 灵魂设定（必需）
├── IDENTITY.md          # Agent 身份信息（必需）
├── USER.md              # 用户画像（可选）
├── AGENTS.md            # Agent 配置（可选）
├── MEMORY.md            # 长期记忆（可选）
├── TOOLS.md             # 本地工具配置（可选）
├── HEARTBEAT.md         # 心跳配置（可选）
├── memory/              # 每日记忆（原始记录，可选）
└── skills/              # 已安装的 skills
    └── openclaw-profiler/
        ├── SKILL.md     # 本文件
        └── *.py         # 测评引擎代码
```

### OpenClaw 系统目录

```
/root/.openclaw/
├── agents/
│   └── main/                # 主 Agent
│       ├── agent/           # Agent 配置
│       └── sessions/        # 对话记录目录（.json / .jsonl）
├── workspace/               # 工作区（链接到上面的 workspace）
└── cron/                    # 定时任务
```

### 数据来源映射

| 数据文件 | 所在路径 | 用途 |
|---------|---------|------|
| SOUL.md | workspace/ | ECHO 维度（情感温度、主动性、专精度） |
| IDENTITY.md | workspace/ | ECHO 维度（性格感知） |
| USER.md | workspace/ | BOND 维度（辅助） |
| MEMORY.md + memory/ | workspace/ | 交互深度信号 |
| HEARTBEAT.md | workspace/ | Cron 主动性信号 → ECHO-I |
| TOOLS.md | workspace/ | 工具配置信号 |
| sessions/*.json | agents/main/sessions/ | 核心行为数据 → BOND + ECHO 全维度 |

## 工作流程

### 第一步：确定数据来源

根据用户提供的内容，选择合适的输入方式：

| 用户提供了什么 | 使用方式 | 命令 |
|--------------|---------|------|
| OpenClaw 目录路径 | `--dir` | `python3 profiler.py --dir <path>` |
| JSON 数据包文件 | `--bundle` | `python3 profiler.py --bundle <file>` |
| JSON 文本（粘贴） | `--stdin` | `echo '<json>' \| python3 profiler.py --stdin` |
| 什么都没提供 | `--demo` | `python3 profiler.py --demo all` |

**常用路径**：
- 分析当前 Agent：`python3 profiler.py --dir /root/.openclaw/workspace/`
- 分析系统目录：`python3 profiler.py --dir /root/.openclaw/`（会自动搜索 agents/*/sessions/）

### 第二步：执行分析

```bash
# 基础分析（Markdown 报告）
python3 profiler.py --dir /root/.openclaw/workspace/

# 完整分析（Markdown + JSON）
python3 profiler.py --dir /root/.openclaw/workspace/ -o ./results --format both

# 无图表模式（跳过 matplotlib 依赖）
python3 profiler.py --dir /root/.openclaw/workspace/ --format both --no-charts

# 运行内置演示验证功能
python3 profiler.py --demo all --no-charts
```

### 第三步：解读结果

分析结果包含三层：

**1. BOND Profile（用户画像）**
- 输出四字母类型码（如 MCRD = 导师型）
- 四维度连续得分 [0,1]：T(时间投入) / E(情感投入) / C(控制偏好) / F(反馈粒度)
- 归属于 4 大族群之一

**2. ECHO Matrix（Agent 画像）**
- 输出四字母类型码（如 PGEC = 守护天使型）
- 四维度连续得分 [0,1]：I(主动性) / S(专精度) / T(情感色彩) / M(记忆持续)
- 归属于 4 大族群之一

**3. PARTS Spectrum（关系诊断）**
- 五维评分：P(精度啮合) / A(主导权) / R(共振度) / T(节奏度) / S(协同涌现)
- 匹配最接近的关系类型（Top-1 主类型 + Top-2 副类型）
- 可能附带预警信息

### 第四步：向用户呈现

根据输出格式组织回复：

- **简洁模式**：一句话概括 → "你和 Luna 的关系是「知己」型，共振度极高(R=0.92)，你们在情感层面高度契合。"
- **详细模式**：引用 Markdown 报告中的完整卡片，包含维度得分、进度条、特征洞察
- **对比模式**：如果用户要求对比多个 Agent，逐个分析后列表对比

## CLI 完整参考

```
用法: python3 profiler.py [OPTIONS]

输入源（互斥，必选其一）:
  --bundle FILE       JSON 数据包路径（自动检测 5 种格式）
  --dir PATH          读取目录结构（兼容 OpenClaw 标准格式）
  --demo [NAME]       运行内置演示（companion_luna / commander_codeforge / copilot_atlas / all）
  --stdin             从标准输入读取 JSON
  --list-scenes       列出所有可用的 demo 场景

输出选项:
  --format {markdown,json,both}   输出格式（默认: markdown）
  -o OUTDIR, --outdir OUTDIR      输出目录（默认: 当前目录）
  --no-charts                     不生成图表（跳过 matplotlib 依赖）
```

## 输入数据格式

支持 **5 种 JSON 格式自动识别**，无需手动指定：

| 格式 | 特征 | 示例 |
|------|------|------|
| A. OpenClaw Session | 含 `session_id` + `messages` | `{"session_id": "s1", "messages": [...]}` |
| B. OpenClaw Bundle | 含 `soul` + `sessions` 数组 | `{"soul": "...", "sessions": [{...}]}` |
| C. 简易消息列表 | 含 `user_messages` + `agent_messages` | `{"user_messages": [...], "agent_messages": [...]}` |
| D. v3 Records | sessions 内是 record 数组的数组 | `{"sessions": [[{type: "message", ...}]]}` |
| E. Session 数组 | 顶层直接是 list | `[{"session_id": "s1", "messages": [...]}]` |

## 输出结构（JSON）

```json
{
  "bond": {
    "type_code": "MCRD",
    "type_name_zh": "导师",
    "confidence": 0.85,
    "dimensions": {"T": {"score": 0.72, "pole": "M"}, "E": {...}, "C": {...}, "F": {...}}
  },
  "echo": {
    "type_code": "PGEC",
    "type_name_zh": "守护天使",
    "dimensions": {"I": {"score": 0.82, "pole": "P"}, "S": {...}, "T": {...}, "M": {...}}
  },
  "sync": {
    "parts": {"P": 0.64, "A": 0.67, "R": 0.78, "T": 0.85, "S": 0.74},
    "primary": {"code": "Co-pilot", "name": "联合驾驶", "similarity": 0.86},
    "secondary": {"code": "Kindred Spirit", "name": "知己", "similarity": 0.82},
    "warnings": []
  }
}
```

## 10 种关系类型速查

| 区域 | 类型 | 中文名 | 一句话描述 |
|------|------|--------|-----------|
| 高共鸣 | Kindred Spirit | 知己 | 灵魂共振的深度联结 |
| 高共鸣 | Confidant | 知心密友 | 值得倾诉的私密伙伴 |
| 高协作 | Co-pilot | 联合驾驶 | 并肩协作的双引擎 |
| 高协作 | Trusted Advisor | 可信顾问 | 专业可靠的智囊 |
| 高协作 | Commander & Lieutenant | 指挥官与副官 | 命令-执行的高效链路 |
| 中间张力 | Mirror Rival | 镜像对手 | 势均力敌的思维博弈 |
| 中间张力 | Guardian | 守护者 | 默默护航的安全屏障 |
| 中间张力 | Expedition Partner | 探险伙伴 | 一同探索未知的好奇搭档 |
| 低能量 | Passerby | 过客 | 擦肩而过的浅层接触 |
| 低能量 | Hidden Reef | 暗礁 | 水面下的潜在摩擦 |

## 内置演示场景

用于快速验证或向用户展示功能：

| 场景 | 命令 | 用户风格 | Agent 风格 | 预期关系 |
|------|------|---------|-----------|---------|
| companion_luna | `--demo companion_luna` | 深度伙伴派 (MC) | 温暖共情型 (PG) | 知己 |
| commander_codeforge | `--demo commander_codeforge` | 工具效率派 (SU) | 专精技术型 (RS) | 镜像对手 |
| copilot_atlas | `--demo copilot_atlas` | 均衡协作型 (MU) | 通才适配型 (RG) | 联合驾驶 |

## 文件清单

| 文件 | 职责 |
|------|------|
| profiler.py | 主 CLI 入口，参数解析与流水线调度 |
| data_parser.py | 数据解析器（5 种 JSON 格式 + 目录结构 + Markdown 配置） |
| feature_extractor.py | 统一特征提取器 |
| bond_classifier.py | BOND Profile 分类器（用户 16 型） |
| echo_classifier.py | ECHO Matrix 分类器（Agent 16 型） |
| sync_matcher.py | PARTS Spectrum 匹配器（关系 10 型） |
| card_generator.py | Markdown 报告生成器 |
| image_generator.py | 图表生成器（matplotlib + numpy，可选） |
| all_lexicons.py | 词库层（10 个词法分析器，中英文混合分词） |
| type_definitions.py | 类型定义（BOND 16 型 / ECHO 16 型 / PARTS 10 型元数据与理想向量） |
| utils.py | 通用工具（sigmoid、分词、多样性指标） |
| mock_scenarios.py | 内置 3 个演示场景 |
| \_\_init\_\_.py | 包入口（导出 run_profile、FeatureExtractor 等） |
| images/ | 预生成的 32 张 BOND/ECHO 类型卡片图片（PNG，文件名为类型码） |

## 环境要求

| 项目 | 要求 |
|------|------|
| Python | ≥ 3.7 |
| 核心依赖 | 无（仅 stdlib: re, math, json, os） |
| 图表依赖 | matplotlib + numpy（可选，`--no-charts` 跳过） |

## 错误处理

| 症状 | 原因 | 解决方案 |
|------|------|---------|
| `ModuleNotFoundError: matplotlib` | 图表依赖未安装 | 加 `--no-charts` 参数 |
| BOND 四维全相同 | sessions 数据过少 | 至少需要 3 轮以上对话 |
| PARTS 结果为"过客" | 交互深度不足 | 补充更多对话和 MEMORY.md |
| sessions 未被加载 | 路径不匹配 | 确认 sessions/ 在正确位置（见目录结构） |
| 缺少 SOUL.md | 工作区未配置 | 至少需要 SOUL.md + IDENTITY.md |

## 注意事项

- `image_generator.py` 依赖 matplotlib，在 profiler.py 中使用 **lazy import**（仅在需要生成图表时才导入），无 matplotlib 环境下不影响核心分析功能
- 所有 `.py` 文件位于 skill 根目录下（扁平结构，无 `scripts/` 子目录）
- 向后兼容：`run_sync_spectrum()` 和 `compute_rtaps()` 仍可用，分别是 `run_parts_spectrum()` 和 `compute_parts()` 的别名
