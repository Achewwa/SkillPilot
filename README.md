# SkillPilot

SkillPilot 是一个面向 Claude 扩展生态的轻量级 Python 智能体项目。它的目标是根据用户的自然语言需求，判断用户更适合使用 Claude Skill、Claude Code Plugin、MCP Server，还是组合方案；随后检索或读取候选资源，对功能匹配度、可信度和安全风险进行评估，并输出推荐报告。如果没有合适的现成资源，系统可以辅助生成一个自定义 Skill 草案。

本项目用于《大语言模型与信息决策》课程项目。实现方向是使用 Python 自行构建智能体工作流，而不是依赖 LangChain、CrewAI、AutoGPT 等成熟智能体框架。

## 项目动机

Claude 的扩展生态中包含 Skill、Plugin、MCP 等多种能力扩展形式。普通用户经常面临几个问题：

- 不清楚 Skill、Plugin、MCP 分别适合什么场景。
- 不知道应该从官方文档、GitHub、社区目录还是其他来源查找资源。
- 难以判断第三方资源是否维护良好、是否可信。
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
- 根据功能匹配、可信度和安全风险对候选资源排序。
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
  -> CandidateExtractor：候选信息抽取
  -> CapabilityMatcher：能力匹配评分
  -> TrustEvaluator：可信度评估
  -> RiskAnalyzer：安全风险分析
  -> DecisionGate：推荐或构造决策
  -> RecommendationWriter / SkillBuilder：输出报告或 Skill 草案
```

MVP 不会自动安装第三方 Plugin 或 MCP Server，也不会自动运行第三方脚本。系统只提供分析、推荐、风险提示和安全范围内的 Skill 草案生成。

## 计划中的命令行形式

```bash
python main.py recommend "我想让 Claude 自动生成 Python 单元测试并分析失败原因"
python main.py build-skill "帮我构造一个根据课程课件给作业题提示知识点但不直接给答案的 Skill"
python main.py demo --case skill
python main.py demo --case mcp
python main.py demo --case build
```

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
- 可信度与安全风险分析
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
- 创建 `projects_info.md` 作为跨窗口同步的项目记忆文件。

具体进度请查看 `projects_info.md`。

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

## 参考文件

- `课程项目.pdf`：课程项目要求。
- `project_draft.md`：原始项目计划草案，仅作为参考，后续可以根据实际实现删改。
- `projects_info.md`：项目进度与同步信息。
