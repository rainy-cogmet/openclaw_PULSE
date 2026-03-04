# -*- coding: utf-8 -*-
"""
OpenClaw PARTS Spectrum Profiler — CLI 入口
==========================================
v3.1: 原生兼容 OpenClaw 标准 session JSON 格式

支持 4 种输入模式:
  --bundle FILE    读取 JSON bundle 文件 (自动检测 OpenClaw 标准格式/v3格式/简易格式)
  --dir PATH       读取目录结构 (OpenClaw 标准格式, 兼容 .openclaw/ 子目录)
  --demo [NAME]    运行 mock 场景 (companion_luna / commander_codeforge / copilot_atlas / all)
  --stdin          从标准输入读 JSON
  --list-scenes    列出所有可用的 demo 场景

输出格式:
  --format markdown|json|both   (默认 markdown)
  -o DIR                        输出目录 (默认当前目录)

用法:
  python3 -m openclaw_skill.scripts.profiler --demo all
  python3 -m openclaw_skill.scripts.profiler --bundle data.json --format both -o output/
  python3 -m openclaw_skill.scripts.profiler --dir ./my_agent/ --format json
  cat session.json | python3 -m openclaw_skill.scripts.profiler --stdin
  cd scripts && python3 profiler.py --list-scenes

兼容的 JSON 格式:
  1. OpenClaw 标准 session:
     {"session_id": "s1", "messages": [{"role": "user", "content": "..."}]}
  2. OpenClaw 标准 bundle:
     {"soul": "...", "sessions": [{"session_id": "s1", "messages": [...]}]}
  3. v3 record 数组 bundle:
     {"soul": "...", "sessions": [[{"type": "message", "role": "user", ...}]]}
  4. 简易消息 bundle:
     {"user_messages": ["..."], "agent_messages": ["..."]}
"""

import sys
import os
import argparse
import json

# ---------------------------------------------------------------------------
# Import compatibility layer: 支持 -m 模块运行 和 直接 python3 profiler.py
# ---------------------------------------------------------------------------
_scripts_dir = os.path.dirname(os.path.abspath(__file__))
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)

try:
    from .all_lexicons import (
        SocialLanguageLexicon, SelfDisclosureLexicon,
        GreetingFarewellLexicon, MessageIntentLexicon,
        SoulAutonomyLexicon, SoulSpecializationLexicon,
        SoulToneWarmthLexicon, IdentityVibeLexicon,
        EmotionalWordLexicon, FormalityLexicon,
    )
    from .bond_classifier import compute_bond_profile
    from .echo_classifier import compute_echo_profile
    from .sync_matcher import run_parts_spectrum
    from .card_generator import generate_markdown_report
    from .mock_scenarios import get_all_scenarios
    from .feature_extractor import FeatureExtractor
    from .data_parser import DataParser
except ImportError:
    from all_lexicons import (
        SocialLanguageLexicon, SelfDisclosureLexicon,
        GreetingFarewellLexicon, MessageIntentLexicon,
        SoulAutonomyLexicon, SoulSpecializationLexicon,
        SoulToneWarmthLexicon, IdentityVibeLexicon,
        EmotionalWordLexicon, FormalityLexicon,
    )
    from bond_classifier import compute_bond_profile
    from echo_classifier import compute_echo_profile
    from sync_matcher import run_parts_spectrum
    from card_generator import generate_markdown_report
    from mock_scenarios import get_all_scenarios
    from feature_extractor import FeatureExtractor
    from data_parser import DataParser


# ===================================================================
# 数据验证
# ===================================================================

class ProfilerError(Exception):
    """Profiler 专用异常."""
    pass


def validate_bundle(data):
    """验证输入数据基本完整性, 返回验证结果和警告列表.

    不抛异常 — 允许部分缺失 (graceful degradation), 但会返回 warnings.
    """
    warnings = []

    if not isinstance(data, dict):
        raise ProfilerError("输入数据必须是 dict 类型, 收到 {}".format(type(data).__name__))

    # 检查是否有可用的消息来源
    has_sessions = bool(data.get('sessions'))
    has_user_msgs = bool(data.get('user_messages'))
    has_messages = bool(data.get('messages'))  # 单个 session 对象

    if not has_sessions and not has_user_msgs and not has_messages:
        warnings.append("⚠ 未检测到 sessions / user_messages / messages, 分类结果可能不准确")

    if not data.get('soul_text') and not data.get('soul'):
        warnings.append("⚠ 缺少 soul_text / SOUL.md, 配置侧 lexicon 将使用默认值")

    if not data.get('identity_text') and not data.get('identity'):
        warnings.append("⚠ 缺少 identity_text / IDENTITY.md, identity_vibe 将使用默认值")

    return warnings


# ===================================================================
# Lexicon 计算
# ===================================================================

def compute_lexicons(user_msgs, agent_msgs, soul_text="", identity_text=""):
    """
    对原始消息文本运行全部 10 个 lexicon, 返回标准化的分数 dict.

    分为三组:
      A组 (配置侧) — 分析 soul.md / identity.md
      B组 (行为侧) — 分析 agent 消息
      C组 (用户侧) — 分析 user 消息
    """
    results = {}

    # ---- A组: 配置侧 (soul / identity) ----
    results["soul_tone_warmth_score"] = SoulToneWarmthLexicon().score(soul_text)
    results["soul_autonomy_score"] = SoulAutonomyLexicon().score(soul_text)
    results["identity_vibe_score"] = IdentityVibeLexicon().score(identity_text)
    results["soul_specialization_score"] = SoulSpecializationLexicon().score(soul_text)

    # ---- B组: 行为侧 (agent messages) ----
    agent_text = " ".join(agent_msgs) if agent_msgs else ""
    results["emotional_word_score"] = EmotionalWordLexicon().score(agent_text)
    results["formality_score"] = FormalityLexicon().score(agent_text)

    # ---- C组: 用户侧 (user messages) ----
    user_text = " ".join(user_msgs) if user_msgs else ""
    results["social_language_score"] = SocialLanguageLexicon().score(user_text)
    results["self_disclosure_score"] = SelfDisclosureLexicon().score(user_text)
    results["greeting_farewell_score"] = GreetingFarewellLexicon().score(user_text)

    # MessageIntentLexicon.score() returns a dict: {task, chat, emotional, feedback}
    mi = MessageIntentLexicon()
    mi_result = mi.score(user_text)
    results["message_intent_task_ratio"] = mi_result.get("task", 0.5)
    results["message_intent_question_ratio"] = mi_result.get("chat", 0.0)
    results["message_intent_feedback_ratio"] = mi_result.get("feedback", 0.0)

    return results


# ===================================================================
# 自动格式检测 + 标准化
# ===================================================================

def _detect_and_normalize(raw_data):
    """自动检测输入格式并通过 DataParser 标准化为内部 bundle.

    支持的格式:
      A. OpenClaw 标准 bundle:   {"soul": "...", "sessions": [{"session_id":..., "messages":[...]}]}
      B. v3 record 数组 bundle:  {"soul": "...", "sessions": [[{type:message,...}]]}
      C. 简易 bundle:            {"user_messages": [...], "agent_messages": [...]}
      D. 单个 session 对象:      {"session_id": "s1", "messages": [...]}
      E. session 数组:           [{"session_id": "s1", "messages": [...]}, ...]
      F. mock 场景 dict:         含 sessions (MockSessionParser 对象列表) — 直接透传

    返回标准化的 dict, 可直接传给 run_profile().
    """
    if not isinstance(raw_data, dict):
        # 格式 E: 顶层是数组 — session 对象列表
        if isinstance(raw_data, list) and raw_data:
            if isinstance(raw_data[0], dict) and ('messages' in raw_data[0] or 'session_id' in raw_data[0]):
                raw_data = {'sessions': raw_data}
            else:
                raise ProfilerError("无法识别的输入格式: 顶层数组中的元素不是 session 对象")
        else:
            raise ProfilerError("无法识别的输入格式: 期望 dict 或 list, 收到 {}".format(type(raw_data).__name__))

    # 检查是否是 mock 场景 (sessions 中包含 Mock 对象而非原始 dict/list)
    sessions = raw_data.get('sessions', [])
    if sessions and hasattr(sessions[0], 'messages') and not isinstance(sessions[0], dict):
        # 格式 F: mock 场景 — 已经是解析好的对象, 直接返回
        return raw_data

    # 使用 DataParser 统一解析 (自动处理格式 A/B/C/D)
    try:
        parsed = DataParser.parse_bundle(raw_data)
        return parsed
    except Exception as e:
        # 解析失败 — 尝试原样返回让 run_profile 做 fallback
        import traceback
        print("⚠ DataParser.parse_bundle() 解析失败: {}".format(e), file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return raw_data


# ===================================================================
# run_profile — v3.1: 统一特征提取管线
# ===================================================================

def run_profile(data):
    """
    端到端 Profile 计算.

    v3.1 改进:
      - 自动检测输入格式 (OpenClaw标准/v3/简易/单session)
      - 通过 DataParser 统一标准化, 消除格式兼容复杂度
      - 使用 FeatureExtractor 从真实数据提取全部行为特征
      - 零硬编码默认值

    参数 data (dict): 任何支持的格式, 详见 _detect_and_normalize()

    返回 dict:
        bond:       BOND Profile 结果
        echo:       ECHO Matrix 结果
        sync:       PARTS Spectrum 结果
        report_md:  完整 Markdown 报告
        warnings:   验证警告列表
    """
    # 0. 验证
    warnings = validate_bundle(data)

    # 1. 自动格式检测 + 标准化
    data = _detect_and_normalize(data)

    # 2. 提取基础字段
    user_messages = data.get("user_messages", [])
    agent_messages = data.get("agent_messages", [])
    soul_text = data.get("soul_text", data.get("soul", ""))
    identity_text = data.get("identity_text", data.get("identity", ""))
    user_name = data.get("user_name", "用户")
    agent_name = data.get("agent_name", "Agent")

    # 3. 计算 lexicon 分数 (如果没有预计算的结果)
    lexicon_results = data.get("lexicon_results")
    if not lexicon_results:
        lexicon_results = compute_lexicons(
            user_messages, agent_messages, soul_text, identity_text
        )

    # 4. 构建 FeatureExtractor 输入 bundle
    bundle = {
        "sessions": data.get("sessions", []),
        "markdown": data.get("markdown", None),
        "memory": data.get("memory", None),
        "heartbeat": data.get("heartbeat", None),
        "tools_config": data.get("tools_config", None),
        "skills": data.get("skills", None),
        "user_messages": user_messages,
        "agent_messages": agent_messages,
        "session_count": data.get("session_count", max(1, len(data.get("sessions", [])))),
        "total_turns": data.get("total_turns", len(user_messages) + len(agent_messages)),
        "all_tool_calls": data.get("all_tool_calls", []),
        "soul_text": soul_text,
        "identity_text": identity_text,
        "lexicon_results": lexicon_results,
    }

    # 5. 使用 FeatureExtractor 提取真实特征
    extractor = FeatureExtractor(bundle)
    bond_features, echo_features = extractor.extract_all()

    # 6. 三层分类
    bond_result = compute_bond_profile(bond_features)
    echo_result = compute_echo_profile(echo_features)
    sync_result = run_parts_spectrum(bond_result, echo_result)

    # 7. 生成本地图表 (chart_dir=None 时跳过)
    chart_dir = data.get("chart_dir")
    local_images = {}
    relative_images = {}

    if chart_dir:
        try:
            try:
                from .image_generator import generate_all_charts
            except ImportError:
                from image_generator import generate_all_charts
            local_images = generate_all_charts(
                bond_result, echo_result, sync_result, chart_dir)
            # 转换为相对路径 (假设 chart_dir 是报告所在目录的子目录)
            chart_dir_name = os.path.basename(os.path.normpath(chart_dir))
            relative_images = {
                k: os.path.join(chart_dir_name, os.path.basename(v))
                for k, v in local_images.items()
            }
        except Exception as e:
            print("⚠ 图表生成失败 (matplotlib 未安装?): {}".format(e),
                  file=sys.stderr)
            warnings.append("⚠ 图表生成失败: {}".format(e))

    # 8. 生成完整报告
    report_md = generate_markdown_report(
        bond_result, echo_result, sync_result, user_name, agent_name,
        local_images=relative_images if relative_images else None,
    )

    return {
        "bond": bond_result,
        "echo": echo_result,
        "sync": sync_result,
        "report_md": report_md,
        "warnings": warnings,
    }


# ===================================================================
# 数据加载
# ===================================================================

def load_from_bundle(filepath):
    """从 JSON bundle 文件加载并通过 DataParser 解析.

    自动检测文件内容格式:
      - 单个 session JSON: {"session_id": "...", "messages": [...]}
      - 完整 bundle JSON:  {"soul": "...", "sessions": [...]}
      - session 数组 JSON: [{"session_id": "...", "messages": [...]}, ...]
      - 简易 bundle JSON:  {"user_messages": [...], "agent_messages": [...]}
    """
    with open(filepath, "r", encoding="utf-8") as f:
        raw = json.load(f)

    # _detect_and_normalize 会在 run_profile 中调用
    # 这里只返回原始数据, 让 run_profile 统一处理
    return raw


def load_from_dir(dirpath):
    """
    从目录结构加载数据.

    兼容多种目录结构:
      标准 OpenClaw:           .openclaw/ 下的 md 和 sessions
      扁平结构:                SOUL.md + sessions/ 在同一级
      大小写不敏感:            SOUL.md / soul.md 均可
    """
    try:
        parsed = DataParser.parse_directory(dirpath)
        return parsed
    except Exception as e:
        print("⚠ DataParser.parse_directory() 失败: {}, 尝试简易解析".format(e), file=sys.stderr)

    # Fallback: 简易解析 (原有逻辑)
    data = {}

    for name, key in [('SOUL.md', 'soul_text'), ('soul.md', 'soul_text'),
                       ('IDENTITY.md', 'identity_text'), ('identity.md', 'identity_text')]:
        fpath = os.path.join(dirpath, name)
        if os.path.isfile(fpath) and key not in data:
            with open(fpath, "r", encoding="utf-8") as f:
                data[key] = f.read()

    # 解析 session 文件
    # 按优先级查找 sessions 目录:
    #   1. dirpath/sessions/
    #   2. dirpath/.openclaw/sessions/
    #   3. dirpath/.openclaw/agents/*/sessions/  (OpenClaw 标准路径)
    sessions_dir = os.path.join(dirpath, "sessions")
    if not os.path.isdir(sessions_dir):
        sessions_dir = os.path.join(dirpath, ".openclaw", "sessions")
        if not os.path.isdir(sessions_dir):
            agents_base = os.path.join(dirpath, ".openclaw", "agents")
            if os.path.isdir(agents_base):
                for agent_name in sorted(os.listdir(agents_base)):
                    candidate = os.path.join(agents_base, agent_name, "sessions")
                    if os.path.isdir(candidate):
                        sessions_dir = candidate
                        break

    user_messages = []
    agent_messages = []
    session_count = 0
    total_turns = 0

    if os.path.isdir(sessions_dir):
        session_files = sorted(
            f for f in os.listdir(sessions_dir)
            if f.endswith(".jsonl") or f.endswith(".json")
        )
        session_count = len(session_files)

        for fname in session_files:
            fpath = os.path.join(sessions_dir, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                raw_text = f.read().strip()

            if not raw_text:
                continue

            # 尝试 JSON 对象/数组
            if raw_text.startswith('{') or raw_text.startswith('['):
                try:
                    obj = json.loads(raw_text)
                    if isinstance(obj, dict) and 'messages' in obj:
                        # OpenClaw 标准 session JSON
                        for msg in obj['messages']:
                            role = msg.get('role', '')
                            content = msg.get('content', '')
                            if isinstance(content, list):
                                content = " ".join(
                                    b.get("text", "") for b in content
                                    if isinstance(b, dict) and b.get("type") == "text"
                                )
                            if role == 'user':
                                user_messages.append(content)
                                total_turns += 1
                            elif role == 'assistant':
                                agent_messages.append(content)
                                total_turns += 1
                        continue
                except json.JSONDecodeError:
                    pass

            # JSONL fallback
            for line in raw_text.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                msg = rec.get("message", rec)
                role = msg.get("role", "")
                content = msg.get("content", "")
                if isinstance(content, list):
                    content = " ".join(
                        b.get("text", "") for b in content
                        if isinstance(b, dict) and b.get("type") == "text"
                    )
                if role == "user":
                    user_messages.append(content)
                    total_turns += 1
                elif role == "assistant":
                    agent_messages.append(content)
                    total_turns += 1

    data["user_messages"] = user_messages
    data["agent_messages"] = agent_messages
    data["session_count"] = max(session_count, 1)
    data["total_turns"] = total_turns

    return data


def load_from_stdin():
    """从标准输入读取 JSON."""
    raw = sys.stdin.read()
    return json.loads(raw)


# ===================================================================
# 输出
# ===================================================================

def write_output(result, name, fmt, outdir):
    """将结果写入文件或打印到 stdout."""
    os.makedirs(outdir, exist_ok=True)

    if fmt in ("markdown", "both"):
        md_path = os.path.join(outdir, "{}.md".format(name))
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(result["report_md"])
        print("[OK] Markdown -> {}".format(md_path))

    if fmt in ("json", "both"):
        json_data = {
            "bond": result["bond"],
            "echo": result["echo"],
            "sync": result["sync"],
        }
        json_path = os.path.join(outdir, "{}.json".format(name))
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        print("[OK] JSON -> {}".format(json_path))


def _print_summary(result):
    """打印分类结果简要摘要."""
    bond = result["bond"]
    echo = result["echo"]
    sync = result["sync"]

    bc = bond.get("type_code", "?")
    bn = bond.get("type_name_zh", bond.get("type_name", ""))
    ec = echo.get("type_code", "?")
    en = echo.get("type_name_zh", echo.get("type_name", ""))

    # SYNC 结果结构兼容
    if "primary" in sync:
        sp = sync["primary"]
        sync_name = sp.get("name", "?")
        sync_score = sp.get("similarity", 0.0)
    elif "primary_type" in sync:
        sp = sync["primary_type"]
        sync_name = sp.get("name_zh", sp.get("name", "?"))
        sync_score = sp.get("fit_score", 0.0)
    else:
        sync_name = "?"
        sync_score = 0.0

    print("\n  BOND: {} ({})".format(bc, bn))
    print("  ECHO: {} ({})".format(ec, en))
    print("  SYNC: {} [score={:.3f}]".format(sync_name, sync_score))

    # 打印警告
    for w in result.get("warnings", []):
        print("  {}".format(w))


# ===================================================================
# CLI 入口
# ===================================================================

def main():
    parser = argparse.ArgumentParser(
        description="OpenClaw PARTS Spectrum Profiler v3.1",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            "  python3 profiler.py --demo all\n"
            "  python3 profiler.py --demo companion_luna --format both\n"
            "  python3 profiler.py --bundle session.json -o output/\n"
            "  python3 profiler.py --dir ./my_agent/ --format json\n"
            "  cat data.json | python3 profiler.py --stdin\n"
            "  python3 profiler.py --list-scenes\n"
            "\nsupported JSON formats:\n"
            "  OpenClaw session:  {\"session_id\": \"s1\", \"messages\": [...]}\n"
            "  OpenClaw bundle:   {\"soul\": \"...\", \"sessions\": [{...}]}\n"
            "  Simple bundle:     {\"user_messages\": [...], \"agent_messages\": [...]}\n"
        ),
    )

    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument(
        "--bundle", metavar="FILE",
        help="读取 JSON bundle 文件 (自动检测格式)",
    )
    group.add_argument(
        "--dir", metavar="PATH",
        help="读取目录结构 (兼容 OpenClaw 标准格式)",
    )
    group.add_argument(
        "--demo", nargs="?", const="all", metavar="NAME",
        help="运行 mock 场景 (companion_luna / commander_codeforge / copilot_atlas / all)",
    )
    group.add_argument(
        "--stdin", action="store_true",
        help="从标准输入读取 JSON",
    )
    group.add_argument(
        "--list-scenes", action="store_true",
        help="列出所有可用的 demo 场景",
    )

    parser.add_argument(
        "--format", choices=["markdown", "json", "both"], default="markdown",
        help="输出格式 (默认: markdown)",
    )
    parser.add_argument(
        "-o", "--outdir", default=".",
        help="输出目录 (默认: 当前目录)",
    )
    parser.add_argument(
        "--no-charts", action="store_true",
        help="不生成图片报告",
    )

    args = parser.parse_args()

    # 如果没有任何参数, 打印帮助
    if not any([args.bundle, args.dir, args.demo, args.stdin, args.list_scenes]):
        parser.print_help()
        sys.exit(0)

    # ---- --list-scenes ----
    if args.list_scenes:
        scenarios = get_all_scenarios()
        print("可用的 demo 场景:")
        for name, fn in scenarios.items():
            doc = fn.__doc__ or ""
            first_line = doc.strip().split('\n')[0] if doc.strip() else ""
            print("  - {:<25s} {}".format(name, first_line))
        sys.exit(0)

    # ---- --demo ----
    if args.demo:
        scenarios = get_all_scenarios()
        if args.demo == "all":
            names = list(scenarios.keys())
        elif args.demo in scenarios:
            names = [args.demo]
        else:
            print("错误: 未知场景 '{}'. 可用场景: {}".format(
                args.demo, ", ".join(scenarios.keys())))
            sys.exit(1)

        for name in names:
            print("\n" + "=" * 60)
            print("场景: {}".format(name))
            print("=" * 60)
            data = scenarios[name]()
            if not args.no_charts:
                 data["chart_dir"] = os.path.join(args.outdir, "charts")
            result = run_profile(data)
            write_output(result, name, args.format, args.outdir)
            _print_summary(result)

    # ---- --bundle ----
    elif args.bundle:
        if not os.path.isfile(args.bundle):
            print("错误: 文件不存在 '{}'".format(args.bundle))
            sys.exit(1)
        data = load_from_bundle(args.bundle)
        # 如果 load_from_bundle 返回 list (session数组), 包装为 dict
        if isinstance(data, list):
            data = {"sessions": data}
        if not args.no_charts:
             data["chart_dir"] = os.path.join(args.outdir, "charts")
        result = run_profile(data)
        name = os.path.splitext(os.path.basename(args.bundle))[0]
        write_output(result, name, args.format, args.outdir)
        _print_summary(result)

    # ---- --dir ----
    elif args.dir:
        if not os.path.isdir(args.dir):
            print("错误: 目录不存在 '{}'".format(args.dir))
            sys.exit(1)
        data = load_from_dir(args.dir)
        if not args.no_charts:
             data["chart_dir"] = os.path.join(args.outdir, "charts")
        result = run_profile(data)
        name = os.path.basename(os.path.abspath(args.dir))
        write_output(result, name, args.format, args.outdir)
        _print_summary(result)

    # ---- --stdin ----
    elif args.stdin:
        data = load_from_stdin()
        # 如果输入是 list (session数组), 包装为 dict
        if isinstance(data, list):
            data = {"sessions": data}
        if not args.no_charts:
             data["chart_dir"] = os.path.join(args.outdir, "charts")
        result = run_profile(data)
        write_output(result, "stdin_profile", args.format, args.outdir)
        _print_summary(result)

    print("\n完成.")


if __name__ == "__main__":
    main()
