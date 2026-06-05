# SkillPilot

SkillPilot 是一个面向 Claude 扩展生态的轻量级 Python 智能体项目。它的目标是根据用户的自然语言需求，判断用户更适合使用 Claude Skill、Claude Code Plugin、MCP Server，还是组合方案；随后从固定数据源中检索或读取候选资源，对功能匹配度、文档证据和安全风险进行评估，并输出推荐报告。如果没有合适的现成资源，系统可以辅助生成一个自定义 Skill 草案。

本项目用于《大语言模型与信息决策》课程项目。实现方向是使用 Python 自行构建智能体工作流，而不是依赖 LangChain、CrewAI、AutoGPT 等成熟智能体框架。

## 项目动机

Claude 的扩展生态中包含 Skill、Plugin、MCP 等多种能力扩展形式。普通用户经常面临几个问题：

- 不清楚 Skill、Plugin、MCP 分别适合什么场景。
- 不知道应该从官方文档、GitHub、社区目录还是其他来源查找资源。
- 难以判断候选资源的文档证据是否足以支撑推荐。
- 难以识别插件、MCP 或脚本可能带来的文件读写、命令执行、token 暴露、数据库访问等安全风险。
- 当没有现成资源完全符合需求时，不知道如何构造一个可用的自定义 Skill。

SkillPilot 试图把这些步骤整合成一个完整闭环：需求理解、类型判断、候选检索、信息抽取、评分评估、风险分析、推荐输出，以及必要时的自定义 Skill 构造。

## 核心目标

SkillPilot 的首版目标包括：

- 将用户自然语言需求解析为结构化任务信息。
- 判断需求适合 Skill、Plugin、MCP 或混合方案。
- 基于扩展类型规划搜索源。
- 从缓存、文档、GitHub 仓库或社区资源中读取候选资源。
- 抽取候选资源的功能、安装方式、依赖、维护状态、权限和风险信息。
- 根据功能匹配、文档证据和安全风险对候选资源排序。
- 输出中文推荐报告，说明推荐理由、缺失能力、风险提示和使用建议。
- 当现有候选不合适时，生成自定义 Skill 草案。
- 保存决策轨迹，便于复现和课堂展示。

## MVP 范围

首版将实现为命令行工具，不做图形界面。MVP 重点是稳定、可解释、可展示的智能体流程，而不是大规模实时搜索。

```text
用户需求
  -> RequirementParser：需求解析
  -> ExtensionTypeClassifier：扩展类型判断
  -> SourcePlanner：搜索源规划
  -> SearchTools / 本地缓存：候选检索
  -> PageReader / RepoReader：页面或仓库读取
  -> LLM Evaluator：直接阅读候选原文并输出候选信息、能力、文档和安全评分
  -> DecisionGate：推荐或构造决策
  -> RecommendationWriter / SkillBuilder：输出报告或 Skill 草案
```

MVP 不会自动安装第三方 Plugin 或 MCP Server，也不会自动运行第三方脚本。系统只提供分析、推荐、风险提示和安全范围内的 Skill 草案生成。

## 计划中的命令行形式

```bash
python main.py
python main.py recommend "我想让 Claude 自动生成 Python 单元测试并分析失败原因"
python main.py build-skill "帮我构造一个根据课程课件给作业题提示知识点但不直接给答案的 Skill"
python main.py demo --case skill
python main.py demo --case mcp
python main.py demo --case build
```

直接运行 `python main.py` 会进入交互式会话。会话中直接输入自然语言需求即可，系统会自动尝试推荐已有扩展；如果判断没有合适候选，会进入自定义 Skill 草案流程。也可以使用 `/build <需求>` 直接生成 Skill 草案，使用 `/demo skill|mcp|build` 运行演示案例，使用 `/exit` 退出。

## 预期输出

```text
outputs/recommendation_report.md
outputs/decision_trace.json
generated_skills/<skill-name>/SKILL.md
generated_skills/<skill-name>/resources/
generated_skills/<skill-name>/examples/
```

推荐报告应包含：

- 用户需求理解
- 推荐扩展类型
- 搜索范围
- 候选资源列表
- 候选排序与评分
- 功能匹配说明
- 缺失能力说明
- 文档证据与安全风险分析
- 使用建议或替代方案

## 安全原则

SkillPilot 不应无条件推荐或生成高风险能力。以下行为需要被标记为高风险：

- 自动执行 shell 命令
- 写入或批量删除文件
- 自动 hooks
- 访问 API token 或账号凭据
- 操作数据库
- 连接远程服务并执行写操作

对于高风险候选，系统应给出风险提示和安全替代方案，而不是鼓励用户直接安装或运行。

## 当前状态

当前仓库处于项目初始阶段。已经完成：

- 阅读课程项目要求 PDF。
- 阅读并整理原始项目草案。
- 创建 conda 环境 `skill_pilot`。
- 安装初始 Python 依赖。
- 验证 WSL 中的 Claude Code 可以正常调用。
- 创建项目介绍 README。
- 创建 `project_info.md` 作为跨窗口同步的项目记忆文件。
- 搭建可运行 Python 项目骨架，包括 CLI、核心模型、占位 agent 流程、本地 demo 缓存、报告输出和自定义 Skill 草案生成。
- 添加基座 LLM 配置层，默认复用 WSL 本地 `claude` CLI 的现有配置。

具体进度请查看 `project_info.md`。

## 环境使用

在 WSL 中进入项目：

```bash
conda activate skill_pilot
cd /home/achewwa/Projects/SkillPilot
```

验证 Claude Code：

```bash
claude -p --tools '' --no-session-persistence --max-budget-usd 0.05 'Please only output OK'
```

预期输出：

```text
OK
```

## LLM 配置

项目代码中的基座 LLM 默认通过 WSL 本地 `claude` CLI 调用，复用当前机器上已有的 Claude Code 配置，不在项目内保存 API key 或 endpoint。

可选环境变量：

```bash
export SKILLPILOT_LLM_PROVIDER=claude_cli
export SKILLPILOT_CLAUDE_COMMAND=claude
export SKILLPILOT_ENABLE_LLM_EVALUATION=1
```

## 网络搜索配置

网络搜索默认开启。需要离线测试或课堂演示固定输出时，可以显式关闭：

```bash
export SKILLPILOT_ENABLE_NETWORK_SEARCH=0
```

如果 WSL 需要通过宿主机代理访问外网，可以设置：

```bash
export SKILLPILOT_HTTP_PROXY=http://172.22.0.1:7890
export SKILLPILOT_SEARCH_TIMEOUT_SECONDS=8
export SKILLPILOT_SEARCH_MAX_RESULTS=3
```

## 参考文件

- `info.pdf`：课程项目要求。
- `project_draft.md`：原始项目计划草案，仅作为参考，后续可以根据实际实现删改。
- `project_info.md`：项目进度与同步信息。
