# -*- coding: utf-8 -*-
"""
OpenClaw SYNC Spectrum Profiler v3.2 — Cron 全链路 E2E Test
覆盖: CronParser 单元 → FeatureExtractor cron 特征 → ECHO I 维度 cron 信号 →
      Mock 场景全流程 → 目录结构 cron/ 加载 → 无 cron 降级 → 边界情况
"""
import json, os, sys, tempfile, shutil, traceback

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from data_parser import CronParser, DataParser
from feature_extractor import FeatureExtractor
import echo_classifier
from profiler import run_profile, load_from_dir
from mock_scenarios import get_all_scenarios

_PASS = 0
_FAIL = 0
_ERRORS = []

def _ok(name, msg=""):
    global _PASS; _PASS += 1
    print(f"  ✓  {name}" + (f" — {msg}" if msg else ""))

def _fail(name, msg=""):
    global _FAIL; _FAIL += 1
    _ERRORS.append(f"{name}: {msg}")
    print(f"  ✗  {name}" + (f" — {msg}" if msg else ""))

def _check(cond, name, msg=""):
    (_ok if cond else _fail)(name, msg)

def _approx(a, b, tol=0.01):
    return abs(a - b) < tol


# =====================================================================
# TEST 1: CronParser 单元测试
# =====================================================================
def test_cron_parser_unit():
    print("\n" + "=" * 70)
    print("TEST 1: CronParser 单元测试")
    print("=" * 70)

    # 1a: 空构造
    print("\n  --- 1a: 空 CronParser ---")
    cp0 = CronParser()
    _check(not cp0.has_cron(), "1a: empty has_cron=False")
    _check(cp0.get_job_count() == 0, "1a: job_count=0")
    _check(cp0.get_proactivity_score() == 0.0, "1a: proactivity=0.0")
    _check(cp0.get_frequency_score() == 0.0, "1a: frequency=0.0")
    _check(cp0.get_recurring_ratio() == 0.0, "1a: recurring_ratio=0.0")

    # 1b: 单个 every 任务
    print("\n  --- 1b: 单个 every 任务 ---")
    cp1 = CronParser(jobs=[{
        "jobId": "j1", "name": "test",
        "schedule": {"kind": "every", "everyMs": 300000},  # 5分钟
        "sessionTarget": "isolated",
        "payload": {"kind": "agentTurn", "text": "check"},
        "enabled": True,
    }])
    _check(cp1.has_cron(), "1b: has_cron=True")
    _check(cp1.get_job_count() == 1, "1b: job_count=1")
    _check(cp1.get_enabled_count() == 1, "1b: enabled=1")
    _check(cp1.get_recurring_count() == 1, "1b: recurring=1")
    _check(cp1.get_isolated_count() == 1, "1b: isolated=1")
    _check(cp1.get_agent_turn_count() == 1, "1b: agentTurn=1")
    _check(cp1.get_recurring_ratio() == 1.0, "1b: recurring_ratio=1.0")
    _check(cp1.get_isolated_ratio() == 1.0, "1b: isolated_ratio=1.0")
    _check(cp1.get_frequency_score() == 1.0, "1b: 5min→freq=1.0", f"got {cp1.get_frequency_score()}")

    # 1c: 单个 at 单次任务
    print("\n  --- 1c: 单个 at 单次任务 ---")
    cp2 = CronParser(jobs=[{
        "jobId": "j2", "name": "once",
        "schedule": {"kind": "at", "atMs": 1700000000000},
        "sessionTarget": "main",
        "payload": {"kind": "systemEvent", "text": "trigger"},
        "enabled": True,
    }])
    _check(cp2.get_recurring_count() == 0, "1c: recurring=0")
    _check(cp2.get_agent_turn_count() == 0, "1c: agentTurn=0")
    _check(cp2.get_system_event_count() == 1, "1c: systemEvent=1")
    _check(cp2.get_frequency_score() == 0.0, "1c: at→freq=0.0", f"got {cp2.get_frequency_score()}")

    # 1d: cron 表达式解析
    print("\n  --- 1d: cron 表达式频率 ---")
    cp3 = CronParser(jobs=[{
        "jobId": "j3", "name": "hourly",
        "schedule": {"kind": "cron", "expr": "0 * * * *"},
        "sessionTarget": "isolated",
        "payload": {"kind": "agentTurn", "text": "hourly check"},
        "enabled": True,
    }])
    freq = cp3.get_frequency_score()
    _check(0.6 <= freq <= 0.8, "1d: hourly cron→freq≈0.7", f"got {freq:.3f}")

    # 1e: 常见 cron 表达式 (每5分钟)
    print("\n  --- 1e: 每5分钟 cron ---")
    cp4 = CronParser(jobs=[{
        "jobId": "j4", "name": "freq",
        "schedule": {"kind": "cron", "expr": "*/5 * * * *"},
        "sessionTarget": "isolated",
        "payload": {"kind": "agentTurn", "text": "check"},
        "enabled": True,
    }])
    freq4 = cp4.get_frequency_score()
    _check(freq4 == 1.0, "1e: 5min cron→freq=1.0", f"got {freq4:.3f}")

    # 1f: 禁用任务处理
    print("\n  --- 1f: 禁用任务 ---")
    cp5 = CronParser(jobs=[
        {"jobId": "j5a", "schedule": {"kind": "every", "everyMs": 60000},
         "sessionTarget": "main", "payload": {"kind": "agentTurn"}, "enabled": True},
        {"jobId": "j5b", "schedule": {"kind": "every", "everyMs": 60000},
         "sessionTarget": "main", "payload": {"kind": "agentTurn"}, "enabled": False},
    ])
    _check(cp5.get_job_count() == 2, "1f: total=2")
    _check(cp5.get_enabled_count() == 1, "1f: enabled=1")

    # 1g: 混合任务 proactivity 合理性
    print("\n  --- 1g: 混合任务 proactivity ---")
    cp6 = CronParser(jobs=[
        {"jobId": "a", "schedule": {"kind": "every", "everyMs": 300000},
         "sessionTarget": "isolated", "payload": {"kind": "agentTurn"}, "enabled": True},
        {"jobId": "b", "schedule": {"kind": "at", "atMs": 9999999999999},
         "sessionTarget": "main", "payload": {"kind": "systemEvent"}, "enabled": True},
        {"jobId": "c", "schedule": {"kind": "cron", "expr": "0 9 * * *"},
         "sessionTarget": "main", "payload": {"kind": "agentTurn"}, "enabled": True},
    ])
    ps = cp6.get_proactivity_score()
    _check(0.3 <= ps <= 0.9, "1g: mixed proactivity in [0.3,0.9]", f"got {ps:.3f}")

    # 1h: 无效数据容错
    print("\n  --- 1h: 无效数据容错 ---")
    cp7 = CronParser(jobs=[{}, {"not_a_job": True}, "string_item"])
    _check(cp7.get_job_count() == 2, "1h: filters non-dict", f"got {cp7.get_job_count()}")
    _check(cp7.get_proactivity_score() >= 0, "1h: no crash on bad data")


# =====================================================================
# TEST 2: CronParser 目录模式
# =====================================================================
def test_cron_dir_mode():
    print("\n" + "=" * 70)
    print("TEST 2: CronParser 目录模式")
    print("=" * 70)

    tmpdir = tempfile.mkdtemp(prefix="oc_cron_")
    try:
        cron_dir = os.path.join(tmpdir, "cron")
        os.makedirs(cron_dir)
        runs_dir = os.path.join(cron_dir, "runs")
        os.makedirs(runs_dir)

        # jobs.json
        jobs = [
            {"jobId": "d1", "name": "monitor",
             "schedule": {"kind": "every", "everyMs": 600000},
             "sessionTarget": "isolated",
             "payload": {"kind": "agentTurn", "text": "monitor"},
             "enabled": True},
            {"jobId": "d2", "name": "backup",
             "schedule": {"kind": "cron", "expr": "0 2 * * *"},
             "sessionTarget": "isolated",
             "payload": {"kind": "systemEvent", "text": "backup"},
             "enabled": True},
        ]
        with open(os.path.join(cron_dir, "jobs.json"), "w") as f:
            json.dump(jobs, f)

        # runs/d1.jsonl
        with open(os.path.join(runs_dir, "d1.jsonl"), "w") as f:
            for i in range(5):
                f.write(json.dumps({"ts": 1700000000 + i * 600, "status": "ok"}) + "\n")

        # 2a: 从目录加载
        print("\n  --- 2a: 目录加载 ---")
        cp = CronParser(cron_dir=cron_dir)
        _check(cp.has_cron(), "2a: has_cron from dir")
        _check(cp.get_job_count() == 2, "2a: 2 jobs loaded")
        _check(cp.get_total_runs() == 5, "2a: 5 run records", f"got {cp.get_total_runs()}")

        # 2b: 通过 load_from_dir 全流程
        print("\n  --- 2b: load_from_dir 集成 ---")
        # 构建标准 OpenClaw 目录
        with open(os.path.join(tmpdir, "SOUL.md"), "w") as f:
            f.write("# Soul\n自动化运维助手，擅长定时巡检。")
        sess_dir = os.path.join(tmpdir, "sessions")
        os.makedirs(sess_dir, exist_ok=True)
        with open(os.path.join(sess_dir, "s1.json"), "w") as f:
            json.dump({"session_id": "s1", "messages": [
                {"role": "user", "content": "帮我设置定时任务"},
                {"role": "assistant", "content": "已配置每10分钟巡检。"},
                {"role": "user", "content": "状态如何？"},
                {"role": "assistant", "content": "一切正常。"},
            ]}, f)

        data = load_from_dir(tmpdir)
        _check(data is not None, "2b: load_from_dir OK")
        if data:
            result = run_profile(data)
            _check(result is not None, "2b: run_profile with cron dir")
            if result:
                echo = result.get("echo", {})
                dims = echo.get("dimensions", {})
                i_raw = dims.get("I", dims.get("i", {})); i_val = i_raw["score"] if isinstance(i_raw, dict) else i_raw
                _check(i_val >= 0, "2b: ECHO I computed", f"I={i_val}")

        # 2c: .openclaw/cron/ 路径
        print("\n  --- 2c: .openclaw/cron/ 路径 ---")
        tmpdir2 = tempfile.mkdtemp(prefix="oc_dot_cron_")
        oc_dir = os.path.join(tmpdir2, ".openclaw")
        oc_cron = os.path.join(oc_dir, "cron")
        os.makedirs(oc_cron)
        with open(os.path.join(oc_cron, "jobs.json"), "w") as f:
            json.dump([{"jobId": "x1", "schedule": {"kind": "every", "everyMs": 60000},
                        "sessionTarget": "isolated", "payload": {"kind": "agentTurn"},
                        "enabled": True}], f)
        with open(os.path.join(oc_dir, "SOUL.md"), "w") as f:
            f.write("# Soul\n定时任务助手。")
        sd = os.path.join(oc_dir, "sessions")
        os.makedirs(sd)
        with open(os.path.join(sd, "c1.json"), "w") as f:
            json.dump({"session_id": "c1", "messages": [
                {"role": "user", "content": "检查"}, {"role": "assistant", "content": "OK"},
            ]}, f)

        data2 = load_from_dir(tmpdir2)
        _check(data2 is not None, "2c: load_from_dir(.openclaw/cron/)")
        if data2:
            result2 = run_profile(data2)
            _check(result2 is not None, "2c: run_profile .openclaw/cron/")
        shutil.rmtree(tmpdir2, ignore_errors=True)

    except Exception as e:
        _fail("Group 2", f"{type(e).__name__}: {e}")
        traceback.print_exc()
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


# =====================================================================
# TEST 3: FeatureExtractor cron 特征提取
# =====================================================================
def test_feature_extraction():
    print("\n" + "=" * 70)
    print("TEST 3: FeatureExtractor cron 特征")
    print("=" * 70)

    # 3a: 有 cron 数据的 bundle
    print("\n  --- 3a: 有 cron 的特征提取 ---")
    bundle_with_cron = {
        "soul_text": "自动化助手",
        "sessions": [{"session_id": "t1", "messages": [
            {"role": "user", "content": "你好"}, {"role": "assistant", "content": "你好！"}
        ]}],
        "cron_jobs": [
            {"jobId": "f1", "schedule": {"kind": "every", "everyMs": 300000},
             "sessionTarget": "isolated", "payload": {"kind": "agentTurn"}, "enabled": True},
            {"jobId": "f2", "schedule": {"kind": "every", "everyMs": 3600000},
             "sessionTarget": "main", "payload": {"kind": "agentTurn"}, "enabled": True},
        ],
    }
    parsed = DataParser.parse_bundle(bundle_with_cron)
    _check("cron" in parsed, "3a: parsed bundle has cron key")
    cron_obj = parsed.get("cron")
    _check(cron_obj is not None and hasattr(cron_obj, "has_cron"), "3a: cron is CronParser")
    if cron_obj:
        _check(cron_obj.get_job_count() == 2, "3a: CronParser.job_count=2")

    fe = FeatureExtractor(parsed)
    echo_f = fe.extract_echo_features()
    cps = echo_f.get("cron_proactivity_score", -999)
    _check(cps > 0, "3a: cron_proactivity_score > 0", f"got {cps:.3f}")
    _check(echo_f.get("cron_job_count", -1) == 2, "3a: cron_job_count=2")
    _check(echo_f.get("cron_enabled_count", -1) == 2, "3a: cron_enabled_count=2")
    _check(echo_f.get("cron_recurring_ratio", -1) == 1.0, "3a: cron_recurring_ratio=1.0")
    freq = echo_f.get("cron_frequency_score", -1)
    _check(freq > 0, "3a: cron_frequency_score > 0", f"got {freq:.3f}")

    # 3b: 无 cron 数据时降级
    print("\n  --- 3b: 无 cron 降级 ---")
    bundle_no_cron = {
        "soul_text": "普通助手",
        "sessions": [{"session_id": "t2", "messages": [
            {"role": "user", "content": "测试"}, {"role": "assistant", "content": "收到"}
        ]}],
    }
    parsed2 = DataParser.parse_bundle(bundle_no_cron)
    fe2 = FeatureExtractor(parsed2)
    echo_f2 = fe2.extract_echo_features()
    cps2 = echo_f2.get("cron_proactivity_score", -999)
    _check(cps2 == -1.0, "3b: no cron → proactivity=-1.0 (降级)", f"got {cps2}")


# =====================================================================
# TEST 4: ECHO I 维度 cron 信号集成
# =====================================================================
def test_echo_i_cron():
    print("\n" + "=" * 70)
    print("TEST 4: ECHO I 维度 cron 信号")
    print("=" * 70)

    # 4a: cron 对 I 维度的影响
    print("\n  --- 4a: cron 提升 I 维度 ---")
    base_bundle = {
        "soul_text": "你是一个主动的助手。",
        "sessions": [{"session_id": "i1", "messages": [
            {"role": "user", "content": "你好"}, {"role": "assistant", "content": "你好！有什么需要帮忙的？"},
            {"role": "user", "content": "天气"}, {"role": "assistant", "content": "今天晴朗。"},
        ]}],
    }
    # 无 cron 基线
    parsed_base = DataParser.parse_bundle(base_bundle)
    result_base = run_profile(base_bundle)
    I_base = result_base["echo"]["dimensions"]["I"]["score"]

    # 有密集 cron
    cron_bundle = dict(base_bundle)
    cron_bundle["cron_jobs"] = [
        {"jobId": "c1", "schedule": {"kind": "every", "everyMs": 300000},
         "sessionTarget": "isolated", "payload": {"kind": "agentTurn"}, "enabled": True},
        {"jobId": "c2", "schedule": {"kind": "every", "everyMs": 600000},
         "sessionTarget": "isolated", "payload": {"kind": "agentTurn"}, "enabled": True},
        {"jobId": "c3", "schedule": {"kind": "cron", "expr": "*/15 * * * *"},
         "sessionTarget": "isolated", "payload": {"kind": "agentTurn"}, "enabled": True},
    ]
    result_cron = run_profile(cron_bundle)
    I_cron = result_cron["echo"]["dimensions"]["I"]["score"]
    _check(I_cron > I_base, "4a: cron 提升 I", f"base={I_base:.3f} → cron={I_cron:.3f}")

    # 4b: 无 cron 时 I 维度仍能正常计算 (降级)
    print("\n  --- 4b: 无 cron 降级不影响 I ---")
    _check(0 <= I_base <= 1, "4b: I_base in [0,1]", f"got {I_base:.3f}")

    # 4c: Mock 场景差异化
    print("\n  --- 4c: Mock 场景 I 维度差异化 ---")
    all_scn = get_all_scenarios()
    i_values = {}
    for name, builder in all_scn.items():
        data = builder()
        result = run_profile(data)
        i_val = result["echo"]["dimensions"]["I"]["score"]
        i_values[name] = i_val
        print(f"      {name}: I = {i_val:.3f}")
    # 验证三个场景 I 维度均有效, 且都在合理范围
    for sn, iv in i_values.items():
        _check(0 <= iv <= 1, f"4c: {sn}.I in [0,1]", f"got {iv:.3f}")

    # 4d: cron 特征通过 FeatureExtractor 正确传递给 echo_classifier
    print("\n  --- 4d: cron 特征链路验证 ---")
    data_cf = all_scn["commander_codeforge"]()
    parsed_cf = DataParser.parse_bundle(data_cf)
    fe_cf = FeatureExtractor(parsed_cf)
    echo_f_cf = fe_cf.extract_echo_features()
    cps_cf = echo_f_cf.get("cron_proactivity_score", -999)
    _check(cps_cf > 0, "4d: CodeForge cron_proactivity > 0", f"got {cps_cf:.3f}")
    # 验证 compute_echo_profile 接收到特征后 I 维度计算包含 cron
    from echo_classifier import compute_echo_profile
    echo_with_cron = compute_echo_profile(echo_f_cf)
    I_with = echo_with_cron["dimensions"]["I"]["score"]
    # 去掉 cron 重算
    echo_f_cf_no_cron = dict(echo_f_cf)
    echo_f_cf_no_cron["cron_proactivity_score"] = -1.0
    echo_without_cron = compute_echo_profile(echo_f_cf_no_cron)
    I_without = echo_without_cron["dimensions"]["I"]["score"]
    _check(abs(I_with - I_without) > 0.001,
           "4d: cron 影响 I 计算", f"with={I_with:.4f} without={I_without:.4f}")


# =====================================================================
# TEST 5: parse_bundle cron 字段兼容
# =====================================================================
def test_parse_bundle_cron_compat():
    print("\n" + "=" * 70)
    print("TEST 5: parse_bundle cron 兼容性")
    print("=" * 70)

    # 5a: cron_jobs 字段
    print("\n  --- 5a: cron_jobs 字段 ---")
    b1 = {"soul_text": "test", "sessions": [],
           "cron_jobs": [{"jobId": "x", "schedule": {"kind": "every", "everyMs": 60000},
                          "sessionTarget": "main", "payload": {"kind": "agentTurn"}, "enabled": True}]}
    p1 = DataParser.parse_bundle(b1)
    _check(p1.get("cron") is not None, "5a: cron_jobs → cron key")
    _check(p1["cron"].get_job_count() == 1, "5a: job_count=1")

    # 5b: cron 字段 (别名)
    print("\n  --- 5b: cron 字段别名 ---")
    b2 = {"soul_text": "test", "sessions": [],
           "cron": [{"jobId": "y", "schedule": {"kind": "at", "atMs": 999},
                     "sessionTarget": "main", "payload": {"kind": "systemEvent"}, "enabled": True}]}
    p2 = DataParser.parse_bundle(b2)
    _check(p2.get("cron") is not None, "5b: cron alias → cron key")
    _check(p2["cron"].get_job_count() == 1, "5b: job_count=1")

    # 5c: 无 cron 字段
    print("\n  --- 5c: 无 cron 字段 ---")
    b3 = {"soul_text": "test", "sessions": []}
    p3 = DataParser.parse_bundle(b3)
    cron3 = p3.get("cron")
    _check(cron3 is not None, "5c: always has cron key")
    if cron3:
        _check(not cron3.has_cron(), "5c: empty CronParser")

    # 5d: cron 已经是 CronParser 实例
    print("\n  --- 5d: 传入 CronParser 实例 ---")
    existing_cp = CronParser(jobs=[{"jobId": "z", "schedule": {"kind": "every", "everyMs": 1000},
                                     "sessionTarget": "main", "payload": {"kind": "agentTurn"}, "enabled": True}])
    b4 = {"soul_text": "test", "sessions": [], "cron": existing_cp}
    p4 = DataParser.parse_bundle(b4)
    _check(p4["cron"] is existing_cp, "5d: CronParser pass-through")


# =====================================================================
# TEST 6: Mock 场景全流程 (含 cron)
# =====================================================================
def test_mock_full_v32():
    print("\n" + "=" * 70)
    print("TEST 6: Mock 场景全流程 v3.2")
    print("=" * 70)
    all_scn = get_all_scenarios()
    for name, builder in all_scn.items():
        print(f"\n  --- {name} ---")
        data = builder()
        # 验证 cron_jobs 存在
        cj = data.get("cron_jobs", [])
        _check(len(cj) > 0, f"{name}: has cron_jobs", f"count={len(cj)}")

        result = run_profile(data)
        _check(result is not None, f"{name}: run_profile OK")
        if result:
            for key in ("bond", "echo", "sync"):
                _check(key in result, f"{name}: has {key}")
            echo = result["echo"]
            _check("type_code" in echo, f"{name}: echo type_code")
            code = echo.get("type_code", "")
            _check(len(code) == 4 and code.isalpha(), f"{name}: echo code format", f"'{code}'")
            dims = echo.get("dimensions", {})
            for d in "ISTM":
                d_raw = dims.get(d, "MISSING")
                d_val = d_raw.get("score", d_raw) if isinstance(d_raw, dict) else d_raw
                _check(d in dims, f"{name}: echo dim {d}", f"val={d_val}")

    # 场景差异化验证
    print("\n  --- 差异化验证 ---")
    results = {}
    for name, builder in all_scn.items():
        results[name] = run_profile(builder())

    luna_I = results["companion_luna"]["echo"]["dimensions"]["I"]["score"]
    forge_I = results["commander_codeforge"]["echo"]["dimensions"]["I"]["score"]
    atlas_I = results["copilot_atlas"]["echo"]["dimensions"]["I"]["score"]
    print(f"      Luna.I={luna_I:.3f}  Forge.I={forge_I:.3f}  Atlas.I={atlas_I:.3f}")
    # 验证 cron 差异化: 三场景 I 维度不同 (cron 贡献了差异)
    _check(0 <= luna_I <= 1 and 0 <= forge_I <= 1 and 0 <= atlas_I <= 1,
           "差异化: 所有 I 在 [0,1]")
    # 至少两个场景 I 值不同 (cron 贡献了差异)
    unique_vals = len(set(round(v, 3) for v in [luna_I, forge_I, atlas_I]))
    _check(unique_vals >= 2, "差异化: I 值有分化", f"unique={unique_vals}")


# =====================================================================
# TEST 7: 边界情况
# =====================================================================
def test_edge_cases():
    print("\n" + "=" * 70)
    print("TEST 7: 边界情况")
    print("=" * 70)

    # 7a: 全部禁用的 cron
    print("\n  --- 7a: 全禁用 cron ---")
    cp_disabled = CronParser(jobs=[
        {"jobId": "d1", "schedule": {"kind": "every", "everyMs": 1000},
         "sessionTarget": "main", "payload": {"kind": "agentTurn"}, "enabled": False},
        {"jobId": "d2", "schedule": {"kind": "every", "everyMs": 2000},
         "sessionTarget": "main", "payload": {"kind": "agentTurn"}, "enabled": False},
    ])
    _check(cp_disabled.get_enabled_count() == 0, "7a: enabled=0")
    _check(cp_disabled.get_job_count() == 2, "7a: total=2")
    # proactivity 应该较低因为 frequency 基于 enabled 任务
    ps = cp_disabled.get_proactivity_score()
    _check(ps >= 0, "7a: proactivity >= 0", f"got {ps:.3f}")

    # 7b: 大量任务 (100个)
    print("\n  --- 7b: 大量任务 ---")
    many_jobs = [{"jobId": f"m{i}", "schedule": {"kind": "every", "everyMs": 60000 * (i + 1)},
                   "sessionTarget": "isolated", "payload": {"kind": "agentTurn"}, "enabled": True}
                  for i in range(100)]
    cp_many = CronParser(jobs=many_jobs)
    _check(cp_many.get_job_count() == 100, "7b: 100 jobs")
    ps_many = cp_many.get_proactivity_score()
    _check(0.0 <= ps_many <= 1.0, "7b: proactivity in [0,1]", f"got {ps_many:.3f}")

    # 7c: 缺少 schedule 字段
    print("\n  --- 7c: 缺少 schedule ---")
    cp_bad = CronParser(jobs=[{"jobId": "bad", "payload": {"kind": "agentTurn"}, "enabled": True}])
    _check(cp_bad.get_job_count() == 1, "7c: still counts")
    ps_bad = cp_bad.get_proactivity_score()
    _check(ps_bad >= 0, "7c: no crash", f"got {ps_bad:.3f}")

    # 7d: 不认识的 schedule.kind
    print("\n  --- 7d: 未知 schedule.kind ---")
    cp_unk = CronParser(jobs=[{"jobId": "unk", "schedule": {"kind": "unknown_kind"},
                                "sessionTarget": "main", "payload": {"kind": "agentTurn"}, "enabled": True}])
    _check(cp_unk.get_recurring_count() == 0, "7d: unknown kind→not recurring")

    # 7e: cron_dir 不存在
    print("\n  --- 7e: 不存在的 cron_dir ---")
    cp_nodir = CronParser(cron_dir="/tmp/nonexistent_cron_dir_xyz")
    _check(not cp_nodir.has_cron(), "7e: nonexistent dir→empty")

    # 7f: 空 jobs.json
    print("\n  --- 7f: 空 jobs.json ---")
    tmpdir = tempfile.mkdtemp(prefix="oc_empty_cron_")
    cron_dir = os.path.join(tmpdir, "cron")
    os.makedirs(cron_dir)
    with open(os.path.join(cron_dir, "jobs.json"), "w") as f:
        json.dump([], f)
    cp_empty = CronParser(cron_dir=cron_dir)
    _check(not cp_empty.has_cron(), "7f: empty jobs.json→no cron")
    shutil.rmtree(tmpdir, ignore_errors=True)


# =====================================================================
# Main
# =====================================================================
def main():
    print("=" * 70)
    print("OpenClaw SYNC Spectrum Profiler v3.2 — Cron 全链路 E2E Test")
    print("=" * 70)

    test_cron_parser_unit()
    test_cron_dir_mode()
    test_feature_extraction()
    test_echo_i_cron()
    test_parse_bundle_cron_compat()
    test_mock_full_v32()
    test_edge_cases()

    print("\n" + "=" * 70)
    print(f"DONE: {_PASS} passed, {_FAIL} failed")
    if _ERRORS:
        print("\nFailures:")
        for e in _ERRORS:
            print(f"  ✗ {e}")
    print("=" * 70)
    return 0 if _FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
