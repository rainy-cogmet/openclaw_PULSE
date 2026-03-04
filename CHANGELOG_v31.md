# OpenClaw PARTS Spectrum Profiler — v3.1 Changelog

## v3.1

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

### 测试

- **test_e2e_v31.py**: 116 项端到端测试，覆盖:
  - 3 个 Mock 场景 (companion_luna / commander_codeforge / copilot_atlas)
  - 5 种 JSON 输入格式 (单 session / OpenClaw bundle / 简易消息 / 带 tool_calls / v3 records)
  - DataParser.parse_bundle() 直接测试
  - SessionParser(dict) 直接测试
  - JSON 文件 load_from_bundle 测试
  - 目录结构 (标准目录 + .openclaw/ 子目录)
  - 边界情况 (空 sessions / soul only / key alias)

### 文件清单 (scripts/)

| 文件 | 行数 | 变更类型 |
|------|------|----------|
| profiler.py | ~605 | 完全重写 |
| data_parser.py | ~1260 | 6项补丁 + 新方法 |
| echo_classifier.py | ~555 | 权重注释 (10处) |
| feature_extractor.py | ~750 | 常量提升 + import兼容 |
| bond_classifier.py | ~935 | import兼容层 |
| sync_matcher.py | ~420 | import兼容层 |
| card_generator.py | ~580 | import兼容层 |
| test_e2e_v31.py | ~280 | 新增 |
| CHANGELOG_v31.md | - | 新增 |