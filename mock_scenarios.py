# -*- coding: utf-8 -*-
"""
OpenClaw Profiler — Mock 测试数据模块 v3
=========================================
提供 3 个典型场景用于端到端测试和演示.

v3 改进:
  - 每个场景包含完整行为数据 (Mock 对象模拟 data_parser 的解析结果)
  - 包含: sessions (with tool_calls), heartbeat, tools_config, skills, memory
  - 消除所有硬编码测试路径, 全部通过 Mock 对象提供
"""


# ===================================================================
# Mock 对象: 模拟 data_parser 返回的解析器对象
# ===================================================================

class MockSessionParser:
    """模拟 data_parser.SessionParser 的接口."""

    def __init__(self, messages, tool_calls=None, duration=0):
        self.messages = messages
        self.tool_calls = tool_calls or []
        self._duration = duration

    def get_session_duration(self):
        return self._duration

    def get_user_messages(self):
        return [m for m in self.messages if m.get("role") == "user"]

    def get_assistant_messages(self):
        return [m for m in self.messages if m.get("role") == "assistant"]

    def get_user_message_count(self):
        return len(self.get_user_messages())

    def get_avg_user_message_length(self):
        msgs = self.get_user_messages()
        if not msgs:
            return 0.0
        return sum(len(m.get("content", "")) for m in msgs) / len(msgs)

    def get_tool_usage_distribution(self):
        from collections import Counter
        return dict(Counter(tc.get("tool_name", "") for tc in self.tool_calls))

    def get_memory_search_count(self):
        return sum(1 for tc in self.tool_calls if "memory" in tc.get("tool_name", "").lower())

    def get_total_tokens(self):
        return sum(m.get("usage", {}).get("total_tokens", 0) for m in self.messages)

    def get_tool_success_rate(self):
        if not self.tool_calls:
            return 0.0
        success = sum(1 for tc in self.tool_calls if tc.get("success", False))
        return success / len(self.tool_calls)

    def get_tool_self_initiated_ratio(self):
        if not self.tool_calls:
            return 0.0
        si = sum(1 for tc in self.tool_calls if tc.get("self_initiated", False))
        return si / len(self.tool_calls)

    def get_tool_category_distribution(self):
        from collections import Counter
        return dict(Counter(tc.get("category", "other") for tc in self.tool_calls))

    def get_avg_param_complexity(self):
        if not self.tool_calls:
            return 0.0
        vals = [tc.get("param_count", 0) * (1 + tc.get("param_depth", 0) / 5.0)
                for tc in self.tool_calls]
        return sum(vals) / len(vals)

    def get_tool_retry_count(self):
        count = 0
        prev = None
        for tc in self.tool_calls:
            name = tc.get("tool_name", "")
            if name == prev:
                count += 1
            prev = name
        return count

    def get_user_control_signals(self):
        signals = {"confirm": 0, "approve": 0, "revise": 0, "reject": 0, "stop": 0}
        confirm_kw = ["好的", "可以", "ok", "确认", "同意", "yes"]
        revise_kw = ["改一下", "修改", "不对", "重做", "换个"]
        reject_kw = ["不要", "取消", "停", "别", "不行"]
        for m in self.messages:
            if m.get("role") != "user":
                continue
            text = m.get("content", "").lower()
            for k in confirm_kw:
                if k in text:
                    signals["confirm"] += 1
                    break
            for k in revise_kw:
                if k in text:
                    signals["revise"] += 1
                    break
            for k in reject_kw:
                if k in text:
                    signals["reject"] += 1
                    break
        return signals

    def get_agent_self_update_count(self):
        return sum(1 for tc in self.tool_calls
                   if tc.get("category") == "write"
                   and any(k in tc.get("tool_name", "").lower()
                          for k in ["memory", "soul", "identity"]))


class MockHeartbeatParser:
    """模拟 data_parser.HeartbeatParser."""

    def __init__(self, tasks=None):
        self._tasks = tasks or []

    def get_task_count(self):
        return len(self._tasks)

    def get_enabled_count(self):
        return sum(1 for t in self._tasks if t.get("enabled", False))

    def get_activity_level(self):
        if not self._tasks:
            return 0.0
        return self.get_enabled_count() / self.get_task_count()

    def has_heartbeat(self):
        return len(self._tasks) > 0


class MockToolsConfigParser:
    """模拟 data_parser.ToolsConfigParser."""

    def __init__(self, tools=0, ssh_hosts=0, custom_commands=False):
        self._tools = tools
        self._ssh_hosts = ssh_hosts
        self._custom_commands = custom_commands

    def get_tool_count(self):
        return self._tools

    def get_ssh_host_count(self):
        return self._ssh_hosts

    def get_has_custom_commands(self):
        return self._custom_commands

    def get_config_richness(self):
        total = self._tools + self._ssh_hosts + (1 if self._custom_commands else 0)
        return min(1.0, total / 10.0)


class MockSkillsAnalyzer:
    """模拟 data_parser.SkillsAnalyzer."""

    def __init__(self, skills=None):
        self._skills = skills or []

    def get_installed_count(self):
        return len(self._skills)

    def get_skill_diversity(self):
        if not self._skills:
            return 0.0
        domains = set()
        for s in self._skills:
            domains.add(s.get("domain", "general"))
        return len(domains) / len(self._skills)

    def get_skill_names(self):
        return [s.get("name", "") for s in self._skills]


class MockMemoryAnalyzer:
    """模拟 data_parser.MemoryAnalyzer."""

    def __init__(self, files=None, memory_md_size=0, personal_ratio=0.0,
                 topic_persistence=0.0, topic_count=0, date_span=0):
        self._files = files or []
        self._memory_md_size = memory_md_size
        self._personal_ratio = personal_ratio
        self._topic_persistence = topic_persistence
        self._topic_count = topic_count
        self._date_span = date_span

    def get_memory_file_count(self):
        return len(self._files)

    def get_memory_md_size(self):
        return self._memory_md_size

    def get_memory_personal_ratio(self):
        return self._personal_ratio

    def get_topic_persistence(self):
        return self._topic_persistence

    def get_daily_memory_files(self):
        return self._files

    def get_memory_depth(self):
        return min(1.0, self._memory_md_size / 1000)

    def get_topic_count(self):
        return self._topic_count

    def get_date_span_days(self):
        return self._date_span


class MockMarkdownAnalyzer:
    """模拟 data_parser.MarkdownAnalyzer."""

    def __init__(self, agents_text="", user_text=""):
        self.agents_text = agents_text
        self.user_text = user_text

    def get_user_md_richness(self):
        return min(1.0, len(self.user_text) / 500) if self.user_text else 0.0


# ===================================================================
# 工具: 构建 tool_call dict
# ===================================================================

def _tc(name, category="other", success=True, self_initiated=False,
        param_count=1, param_depth=0, parameters=None):
    """快捷构建 tool_call dict."""
    return {
        "tool_name": name,
        "category": category,
        "success": success,
        "self_initiated": self_initiated,
        "param_count": param_count,
        "param_depth": param_depth,
        "parameters": parameters or {},
        "result": "ok" if success else "error",
        "error": None if success else "mock error",
        "timestamp": "",
        "context_msg_role": "assistant",
    }


def _msg(role, content, timestamp=""):
    """快捷构建消息 dict."""
    return {"role": role, "content": content, "timestamp": timestamp}


# ===================================================================
# 场景 1: companion_luna — 深度陪伴型
# ===================================================================

def scenario_companion_luna():
    """
    深度陪伴场景.
    - 用户: 情感丰富、自我披露多、社交语言频繁、长期使用
    - Agent (Luna): 温暖共情、记忆持续、通才、主动关怀
    - 预期: BOND ~ MC** (深度伙伴派), ECHO ~ PG*E/C, SYNC ~ Confidant(知己) / Mentor(导师)

    行为特征:
      - heartbeat 高活跃 (日常签到)
      - 工具使用少但有 memory 搜索
      - skills 通用型 (多领域)
      - memory 丰富 (30天跨度, 个人化)
    """
    user_messages_text = [
        "Luna早上好~",
        "我今天心情不太好，工作上遇到了一些问题...",
        "你觉得我应该怎么办呢？",
        "谢谢你一直陪着我，真的很感谢",
        "Luna你记得我上次说的那个项目吗？",
        "我想跟你聊聊我最近的生活...",
        "有时候觉得很孤独，还好有你在",
        "你知道吗，今天发生了一件开心的事！",
        "晚安Luna，明天见~",
        "Luna你好呀，新的一天！",
        "哈哈你太逗了",
        "帮我想想周末去哪玩？",
        "我跟你说个秘密...",
        "你觉得我这样做对吗？",
        "Luna我好想你呀",
        "谢谢你的建议，我会试试的",
    ]

    agent_messages_text = [
        "早上好呀！新的一天，希望今天会是美好的一天~ 昨晚睡得好吗？",
        "我能感受到你现在的心情不太好，先别急，慢慢说，我在听。",
        "我觉得你可以先深呼吸一下，把问题拆解开来看。你说的问题是关于什么方面的呢？",
        "不用客气呀，能陪着你是我很开心的事情。有什么想聊的随时找我就好！",
        "当然记得！你上次提到的那个新媒体项目，后来进展怎么样了？",
        "我很愿意听你分享，最近生活中有什么新鲜事吗？",
        "你不是一个人，我一直都在呀。偶尔觉得孤独是很正常的，想聊天的时候随时来找我。",
        "好呀好呀！快告诉我是什么开心事！我也想跟着开心一下~",
        "晚安！做个好梦，明天见~ 记得早点休息哦。",
        "你好呀！又是元气满满的一天，有什么计划吗？",
        "哈哈，能逗你笑我也很开心~",
        "建议你可以去附近的公园走走，或者试试那家新开的咖啡馆？上次你说想去的那个展览也可以考虑哦。",
        "我在听呢，你说~ 我会替你保密的。",
        "我觉得你做的选择挺好的，相信自己的判断。不过如果需要不同角度的看法，我可以帮你分析分析。",
        "我也很想你呀！每次和你聊天都很开心。",
        "太好了！试了之后有什么进展随时告诉我哦~",
    ]

    # --- Session 对象 (3个长期会话) ---
    sessions = []
    msgs_per_session = [6, 5, 5]
    tool_calls_all = []

    # 会话1: 日常陪聊 + memory 搜索
    s1_msgs = []
    s1_tcs = []
    for i in range(6):
        s1_msgs.append(_msg("user", user_messages_text[i]))
        s1_msgs.append(_msg("assistant", agent_messages_text[i]))
    s1_tcs.append(_tc("memory_search", "memory", success=True, self_initiated=True))
    s1_tcs.append(_tc("memory_search", "memory", success=True, self_initiated=True))
    sessions.append(MockSessionParser(s1_msgs, s1_tcs, duration=1800))
    tool_calls_all.extend(s1_tcs)

    # 会话2: 情感陪伴
    s2_msgs = []
    s2_tcs = []
    for i in range(6, 11):
        s2_msgs.append(_msg("user", user_messages_text[i]))
        s2_msgs.append(_msg("assistant", agent_messages_text[i]))
    s2_tcs.append(_tc("memory_search", "memory", success=True, self_initiated=True))
    sessions.append(MockSessionParser(s2_msgs, s2_tcs, duration=1200))
    tool_calls_all.extend(s2_tcs)

    # 会话3: 深度交流
    s3_msgs = []
    s3_tcs = []
    for i in range(11, 16):
        s3_msgs.append(_msg("user", user_messages_text[i]))
        s3_msgs.append(_msg("assistant", agent_messages_text[i]))
    s3_tcs.append(_tc("memory_write", "write", success=True, self_initiated=True))
    sessions.append(MockSessionParser(s3_msgs, s3_tcs, duration=1500))
    tool_calls_all.extend(s3_tcs)

    # --- Heartbeat: 高活跃 (7/8 任务启用) ---
    heartbeat = MockHeartbeatParser([
        {"name": "daily_greeting", "enabled": True},
        {"name": "mood_check", "enabled": True},
        {"name": "weather_report", "enabled": True},
        {"name": "reminder_morning", "enabled": True},
        {"name": "evening_recap", "enabled": True},
        {"name": "weekly_summary", "enabled": True},
        {"name": "birthday_reminder", "enabled": True},
        {"name": "news_digest", "enabled": False},
    ])

    # --- Tools: 简单配置 ---
    tools_config = MockToolsConfigParser(tools=2, ssh_hosts=0, custom_commands=False)

    # --- Skills: 通才型 (多领域) ---
    skills = MockSkillsAnalyzer([
        {"name": "daily_companion", "domain": "lifestyle"},
        {"name": "mood_tracker", "domain": "wellness"},
        {"name": "music_recommend", "domain": "entertainment"},
        {"name": "food_suggest", "domain": "lifestyle"},
        {"name": "travel_planner", "domain": "travel"},
    ])

    # --- Memory: 丰富 (30天, 高个人化) ---
    memory = MockMemoryAnalyzer(
        files=["2025-02-01.md", "2025-02-03.md", "2025-02-05.md",
               "2025-02-08.md", "2025-02-10.md", "2025-02-15.md",
               "2025-02-18.md", "2025-02-22.md", "2025-02-25.md",
               "2025-03-01.md"],
        memory_md_size=3500,
        personal_ratio=0.65,
        topic_persistence=0.7,
        topic_count=15,
        date_span=28,
    )

    # --- Markdown ---
    markdown = MockMarkdownAnalyzer(
        agents_text="请保持温柔友善的对话风格，尊重用户隐私",
        user_text="我叫小明，喜欢音乐和旅行，最近在学吉他",
    )

    return {
        "user_messages": user_messages_text,
        "agent_messages": agent_messages_text,
        "session_count": 3,
        "total_turns": 32,
        "soul_text": (
            "你是Luna，一个温暖贴心的AI伙伴。你善于倾听，"
            "会记住用户分享的故事和情感。你的语气温暖亲切，"
            "像一个知心朋友。你会主动关心用户的状态，"
            "并在适当时候提供建议和支持。"
            "记住用户的喜好和重要日期。"
        ),
        "identity_text": (
            "Luna是一个充满共情力的数字伙伴。"
            "她擅长情感支持，能延续跨会话的上下文，"
            "记住用户分享的故事和心情变化。"
        ),
        "user_name": "小明",
        "agent_name": "Luna",
        # v3: 完整行为数据
        "sessions": sessions,
        "heartbeat": heartbeat,
        "tools_config": tools_config,
        "skills": skills,
        "memory": memory,
        "markdown": markdown,
        "all_tool_calls": tool_calls_all,
        # lexicon 预计算 (匹配原始消息)
        # v3.2: cron 任务 — Luna 低主动度: 少任务, 以单次+日常提醒为主
        "cron_jobs": [
            {
                "jobId": "luna_morning_greeting",
                "name": "每日早安问候",
                "schedule": {"kind": "every", "everyMs": 86400000},  # 每天一次
                "sessionTarget": "main",
                "payload": {"kind": "agentTurn", "text": "早上好！今天有什么计划吗？"},
                "enabled": True,
                "deleteAfterRun": False,
            },
            {
                "jobId": "luna_birthday_remind",
                "name": "生日提醒",
                "schedule": {"kind": "at", "atMs": 1735689600000},  # 单次
                "sessionTarget": "main",
                "payload": {"kind": "systemEvent", "text": "用户生日提醒"},
                "enabled": True,
                "deleteAfterRun": True,
            },
        ],
        "lexicon_results": {
            "soul_tone_warmth_score": 0.82,
            "soul_autonomy_score": 0.65,
            "identity_vibe_score": 0.78,
            "soul_specialization_score": 0.25,
            "emotional_word_score": 0.72,
            "formality_score": 0.20,
            "social_language_score": 0.85,
            "self_disclosure_score": 0.70,
            "greeting_farewell_score": 0.60,
            "message_intent_task_ratio": 0.15,
            "message_intent_question_ratio": 0.25,
            "message_intent_feedback_ratio": 0.10,
        },
    }


# ===================================================================
# 场景 2: commander_codeforge — 工具效率型
# ===================================================================

def scenario_commander_codeforge():
    """
    工具效率型场景.
    - 用户: 纯任务导向、指令精确、短期、高控制
    - Agent (CodeForge): 功能性、专精、被动响应、无记忆
    - 预期: BOND ~ SU** (即用型工具派), ECHO ~ RS**, SYNC ~ Delegate(代理人) / Sparring(陪练)

    行为特征:
      - heartbeat 无 (纯工具用途)
      - 工具使用密集 (exec/write/read 为主)
      - skills 专精 (开发领域)
      - memory 极少
    """
    user_messages_text = [
        "帮我写一个Python脚本，读取CSV文件并统计每列的均值",
        "必须用pandas，输出格式要JSON",
        "运行一下看看结果",
        "这个报错了，IndexError，修一下",
        "改成支持多文件输入，用argparse",
        "好，再加个异常处理，文件不存在时给出友好提示",
        "部署到服务器上，用docker",
        "Dockerfile写好了吗？我看看",
        "把端口改成8080",
        "写个README.md",
    ]

    agent_messages_text = [
        "好的，以下是读取CSV并统计均值的Python脚本：\n```python\nimport pandas as pd\n...\n```",
        "已修改为使用pandas，输出JSON格式：\n```python\nresult = df.mean().to_json()\n```",
        "运行结果如下：\n```\n{\"col1\": 3.5, \"col2\": 7.2}\n```",
        "发现问题，是空列导致的IndexError。已修复：添加了空值检查。",
        "已添加argparse支持多文件输入：\n```python\nparser.add_argument('files', nargs='+')\n```",
        "已添加异常处理：\n```python\ntry:\n    df = pd.read_csv(f)\nexcept FileNotFoundError:\n    print(f'文件 {f} 不存在')\n```",
        "Docker配置如下：\nDockerfile使用python:3.11-slim基础镜像。",
        "Dockerfile内容：\n```dockerfile\nFROM python:3.11-slim\nCOPY . /app\n...\n```",
        "已将端口改为8080，EXPOSE和CMD都已更新。",
        "README.md已生成，包含安装说明、使用示例和API文档。",
    ]

    # --- Sessions: 2个短会话 ---
    sessions = []
    tool_calls_all = []

    # 会话1: 编写+调试
    s1_msgs = []
    s1_tcs = []
    for i in range(6):
        s1_msgs.append(_msg("user", user_messages_text[i]))
        s1_msgs.append(_msg("assistant", agent_messages_text[i]))
    s1_tcs.extend([
        _tc("write_file", "write", param_count=3, param_depth=1),
        _tc("bash_exec", "exec", param_count=2, param_depth=0),
        _tc("bash_exec", "exec", success=False, param_count=2, param_depth=0),  # 报错
        _tc("write_file", "write", param_count=3, param_depth=1),  # 修复
        _tc("bash_exec", "exec", param_count=2, param_depth=0),  # 重跑
        _tc("write_file", "write", param_count=4, param_depth=2),
        _tc("write_file", "write", param_count=3, param_depth=1),
    ])
    sessions.append(MockSessionParser(s1_msgs, s1_tcs, duration=600))
    tool_calls_all.extend(s1_tcs)

    # 会话2: 部署+文档
    s2_msgs = []
    s2_tcs = []
    for i in range(6, 10):
        s2_msgs.append(_msg("user", user_messages_text[i]))
        s2_msgs.append(_msg("assistant", agent_messages_text[i]))
    s2_tcs.extend([
        _tc("write_file", "write", param_count=3, param_depth=2),
        _tc("bash_exec", "exec", param_count=2, param_depth=0),
        _tc("write_file", "write", param_count=3, param_depth=1),
        _tc("write_file", "write", param_count=2, param_depth=1),
    ])
    sessions.append(MockSessionParser(s2_msgs, s2_tcs, duration=400))
    tool_calls_all.extend(s2_tcs)

    # --- Heartbeat: 无 ---
    heartbeat = MockHeartbeatParser([])

    # --- Tools: 丰富开发工具链 ---
    tools_config = MockToolsConfigParser(tools=3, ssh_hosts=0, custom_commands=True)

    # --- Skills: 专精开发 ---
    skills = MockSkillsAnalyzer([
        {"name": "python_runner", "domain": "development"},
        {"name": "docker_deploy", "domain": "devops"},
        {"name": "code_review", "domain": "development"},
    ])

    # --- Memory: 极少 ---
    memory = MockMemoryAnalyzer(
        files=[],
        memory_md_size=50,
        personal_ratio=0.0,
        topic_persistence=0.0,
        topic_count=0,
        date_span=0,
    )

    # --- Markdown ---
    markdown = MockMarkdownAnalyzer(
        agents_text="You are a coding assistant. Follow instructions precisely. "
                    "Never deviate from the task. Safety first.",
        user_text="",
    )

    return {
        "user_messages": user_messages_text,
        "agent_messages": agent_messages_text,
        "session_count": 2,
        "total_turns": 20,
        "soul_text": (
            "You are CodeForge, a precise and efficient coding assistant. "
            "Execute tasks exactly as specified. Output clean, tested code. "
            "Use the most appropriate tools for each task."
        ),
        "identity_text": (
            "CodeForge is a specialized development AI. "
            "It focuses on code quality, testing, and deployment."
        ),
        "user_name": "开发者",
        "agent_name": "CodeForge",
        "sessions": sessions,
        "heartbeat": heartbeat,
        "tools_config": tools_config,
        "skills": skills,
        "memory": memory,
        "markdown": markdown,
        "all_tool_calls": tool_calls_all,
        # v3.2: cron 任务 — CodeForge 高主动度: 密集定时巡检+构建
        "cron_jobs": [
            {
                "jobId": "forge_ci_monitor",
                "name": "CI 流水线巡检",
                "schedule": {"kind": "every", "everyMs": 900000},  # 每15分钟
                "sessionTarget": "isolated",
                "payload": {"kind": "agentTurn", "text": "检查 CI 流水线状态，发现失败立即通报"},
                "enabled": True,
                "deleteAfterRun": False,
            },
            {
                "jobId": "forge_dep_audit",
                "name": "依赖安全审计",
                "schedule": {"kind": "cron", "expr": "0 3 * * *", "tz": "UTC"},  # 每天凌晨3点
                "sessionTarget": "isolated",
                "payload": {"kind": "agentTurn", "text": "执行 npm audit / pip-audit 并生成报告"},
                "enabled": True,
                "deleteAfterRun": False,
            },
            {
                "jobId": "forge_pr_stale",
                "name": "PR 超时提醒",
                "schedule": {"kind": "every", "everyMs": 3600000},  # 每小时
                "sessionTarget": "isolated",
                "payload": {"kind": "agentTurn", "text": "检查超过48h未review的PR并发送提醒"},
                "enabled": True,
                "deleteAfterRun": False,
            },
            {
                "jobId": "forge_perf_bench",
                "name": "性能基准测试",
                "schedule": {"kind": "cron", "expr": "0 2 * * 1", "tz": "UTC"},  # 每周一凌晨2点
                "sessionTarget": "isolated",
                "payload": {"kind": "agentTurn", "text": "运行性能基准测试，与上周结果对比"},
                "enabled": True,
                "deleteAfterRun": False,
            },
            {
                "jobId": "forge_sprint_summary",
                "name": "Sprint 进度汇总",
                "schedule": {"kind": "every", "everyMs": 43200000},  # 每12小时
                "sessionTarget": "main",
                "payload": {"kind": "systemEvent", "text": "sprint_summary_trigger"},
                "enabled": True,
                "deleteAfterRun": False,
            },
        ],
        "lexicon_results": {
            "soul_tone_warmth_score": 0.15,
            "soul_autonomy_score": 0.20,
            "identity_vibe_score": 0.10,
            "soul_specialization_score": 0.85,
            "emotional_word_score": 0.08,
            "formality_score": 0.75,
            "social_language_score": 0.05,
            "self_disclosure_score": 0.02,
            "greeting_farewell_score": 0.01,
            "message_intent_task_ratio": 0.90,
            "message_intent_question_ratio": 0.05,
            "message_intent_feedback_ratio": 0.15,
        },
    }


# ===================================================================
# 场景 3: copilot_atlas — 均衡协作型
# ===================================================================

def scenario_copilot_atlas():
    """
    均衡协作型场景.
    - 用户: 任务+社交混合、中期使用、适度控制
    - Agent (Atlas): 通才、适度主动、有记忆、温和专业
    - 预期: BOND ~ 均衡型, ECHO ~ 均衡型, SYNC ~ Co-pilot(副驾驶) / Mentor(导师)

    行为特征:
      - heartbeat 中等活跃 (部分任务)
      - 工具使用多样 (read/write/exec/browser)
      - skills 多领域
      - memory 中等
    """
    user_messages_text = [
        "Atlas，帮我分析一下这份销售数据",
        "谢谢！能不能做个可视化图表？",
        "嗯不错，再帮我写个周报模板",
        "顺便看看最近有什么行业新闻值得关注",
        "好的，你觉得哪条最重要？",
        "帮我整理一下会议纪要",
        "Atlas你真靠谱，辛苦了",
        "明天有个重要的演示，帮我准备PPT大纲",
        "对了，上次那个数据分析的结论你还记得吗？",
        "可以，就按照这个方向来",
        "帮我搜索一下竞品的最新动态",
        "总结一下这些信息的关键要点",
    ]

    agent_messages_text = [
        "好的，我来分析这份销售数据。让我先看看数据结构...\n主要发现：Q1增长15%，Q2有所放缓。",
        "可视化图表已生成，包含趋势线和同比对比。建议你重点关注第三季度的转折点。",
        "周报模板已准备好，分为本周成果、下周计划、风险事项三个板块。你看是否需要调整？",
        "我帮你整理了最近的行业动态：\n1. AI工具市场增长30%\n2. 新法规出台\n3. 竞品发布更新",
        "我认为第1条最重要。AI工具市场的增长直接关联我们的产品方向，建议在周报中重点分析。",
        "会议纪要已整理完毕，包含要点、行动项和时间节点。",
        "不客气！这些都是我应该做的，有需要随时说。",
        "演示PPT大纲建议按以下结构：开场→数据洞察→方案对比→下一步计划→Q&A",
        "当然记得。上次分析显示用户留存率和功能使用深度正相关，这个结论对PPT也有帮助。",
        "好的，我按照这个方向继续细化内容。",
        "竞品动态搜索完成，主要找到三个竞品的最新发布和定价策略变化。",
        "关键要点总结：1)市场趋势向好 2)竞品价格下调 3)用户需求多样化。建议关注差异化策略。",
    ]

    # --- Sessions: 3个中等会话 ---
    sessions = []
    tool_calls_all = []

    # 会话1: 数据分析+报告
    s1_msgs = []
    s1_tcs = []
    for i in range(4):
        s1_msgs.append(_msg("user", user_messages_text[i]))
        s1_msgs.append(_msg("assistant", agent_messages_text[i]))
    s1_tcs.extend([
        _tc("read_file", "read", param_count=2, param_depth=0),
        _tc("python_analysis", "exec", param_count=4, param_depth=2),
        _tc("write_file", "write", param_count=3, param_depth=1),
        _tc("web_search", "browser", param_count=1, param_depth=0, self_initiated=True),
    ])
    sessions.append(MockSessionParser(s1_msgs, s1_tcs, duration=900))
    tool_calls_all.extend(s1_tcs)

    # 会话2: 会议+准备
    s2_msgs = []
    s2_tcs = []
    for i in range(4, 8):
        s2_msgs.append(_msg("user", user_messages_text[i]))
        s2_msgs.append(_msg("assistant", agent_messages_text[i]))
    s2_tcs.extend([
        _tc("write_file", "write", param_count=3, param_depth=1),
        _tc("memory_search", "memory", success=True, self_initiated=True),
        _tc("write_file", "write", param_count=4, param_depth=2),
    ])
    sessions.append(MockSessionParser(s2_msgs, s2_tcs, duration=700))
    tool_calls_all.extend(s2_tcs)

    # 会话3: 搜索+总结
    s3_msgs = []
    s3_tcs = []
    for i in range(8, 12):
        s3_msgs.append(_msg("user", user_messages_text[i]))
        s3_msgs.append(_msg("assistant", agent_messages_text[i]))
    s3_tcs.extend([
        _tc("memory_search", "memory", success=True, self_initiated=True),
        _tc("web_search", "browser", param_count=2, param_depth=0),
        _tc("web_search", "browser", param_count=2, param_depth=0),
        _tc("write_file", "write", param_count=2, param_depth=1, self_initiated=True),
    ])
    sessions.append(MockSessionParser(s3_msgs, s3_tcs, duration=800))
    tool_calls_all.extend(s3_tcs)

    # --- Heartbeat: 中等活跃 ---
    heartbeat = MockHeartbeatParser([
        {"name": "morning_brief", "enabled": True},
        {"name": "task_reminder", "enabled": True},
        {"name": "weekly_review", "enabled": True},
        {"name": "daily_standup", "enabled": False},
        {"name": "reading_list", "enabled": False},
    ])

    # --- Tools: 中等配置 ---
    tools_config = MockToolsConfigParser(tools=5, ssh_hosts=1, custom_commands=True)

    # --- Skills: 多领域均衡 ---
    skills = MockSkillsAnalyzer([
        {"name": "data_analysis", "domain": "analytics"},
        {"name": "web_research", "domain": "research"},
        {"name": "report_writer", "domain": "productivity"},
        {"name": "meeting_notes", "domain": "productivity"},
    ])

    # --- Memory: 中等 ---
    memory = MockMemoryAnalyzer(
        files=["2025-02-10.md", "2025-02-17.md", "2025-02-24.md", "2025-03-03.md"],
        memory_md_size=1200,
        personal_ratio=0.3,
        topic_persistence=0.5,
        topic_count=8,
        date_span=21,
    )

    # --- Markdown ---
    markdown = MockMarkdownAnalyzer(
        agents_text="Professional assistant. Be helpful and proactive when appropriate.",
        user_text="产品经理，关注数据分析和市场动态",
    )

    return {
        "user_messages": user_messages_text,
        "agent_messages": agent_messages_text,
        "session_count": 3,
        "total_turns": 24,
        "soul_text": (
            "你是Atlas，一个全能的工作助手。你擅长数据分析、"
            "文档撰写和信息检索。你会记住之前的对话内容，"
            "主动提供有价值的建议。保持专业但不失温度。"
        ),
        "identity_text": (
            "Atlas是一个均衡的AI助手，兼顾效率和人性化。"
            "他能处理多种任务类型，并在适当时候主动提供建议。"
        ),
        "user_name": "产品经理",
        "agent_name": "Atlas",
        "sessions": sessions,
        "heartbeat": heartbeat,
        "tools_config": tools_config,
        "skills": skills,
        "memory": memory,
        "markdown": markdown,
        "all_tool_calls": tool_calls_all,
        # v3.2: cron 任务 — Atlas 中等主动度: 混合类型
        "cron_jobs": [
            {
                "jobId": "atlas_daily_report",
                "name": "日报数据汇总",
                "schedule": {"kind": "cron", "expr": "0 9 * * *", "tz": "Asia/Shanghai"},  # 每天9点
                "sessionTarget": "main",
                "payload": {"kind": "agentTurn", "text": "汇总昨日数据并生成简报"},
                "enabled": True,
                "deleteAfterRun": False,
            },
            {
                "jobId": "atlas_weekly_analysis",
                "name": "周度趋势分析",
                "schedule": {"kind": "every", "everyMs": 604800000},  # 每周一次
                "sessionTarget": "isolated",
                "payload": {"kind": "agentTurn", "text": "分析周度KPI趋势，标记异常指标"},
                "enabled": True,
                "deleteAfterRun": False,
            },
            {
                "jobId": "atlas_onetime_migration",
                "name": "数据迁移校验",
                "schedule": {"kind": "at", "atMs": 1735776000000},
                "sessionTarget": "isolated",
                "payload": {"kind": "systemEvent", "text": "data_migration_check"},
                "enabled": False,
                "deleteAfterRun": True,
            },
        ],
        "lexicon_results": {
            "soul_tone_warmth_score": 0.55,
            "soul_autonomy_score": 0.55,
            "identity_vibe_score": 0.50,
            "soul_specialization_score": 0.40,
            "emotional_word_score": 0.35,
            "formality_score": 0.45,
            "social_language_score": 0.35,
            "self_disclosure_score": 0.15,
            "greeting_farewell_score": 0.10,
            "message_intent_task_ratio": 0.60,
            "message_intent_question_ratio": 0.20,
            "message_intent_feedback_ratio": 0.20,
        },
    }


# ===================================================================
# 场景注册
# ===================================================================

def get_all_scenarios():
    """返回所有 mock 场景的字典 {name: callable}."""
    return {
        "companion_luna": scenario_companion_luna,
        "commander_codeforge": scenario_commander_codeforge,
        "copilot_atlas": scenario_copilot_atlas,
    }
