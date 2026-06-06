# SkillPilot

SkillPilot 是一个用 Python 自行搭建的轻量级智能体项目，用于帮助用户在 Claude 扩展生态中完成需求分析、资源发现、候选评估、风险判断、推荐输出，以及必要时的自定义 Skill 草案生成。

项目的核心设计是 `pipeline-agent-skill`：`SkillPilotPipeline` 负责编排整体流程；不同 Agent 承担需求分析、资源发现、候选评估、决策、Skill 构造和报告输出等角色；每个 Agent 调用对应的 Skill 模块与 LLM、网络资源、本地文件和报告系统交互。

本项目用于《大语言模型与信息决策》课程项目。实现原则是用 Python 手动搭建智能体工作流，不依赖 LangChain、CrewAI、AutoGPT 等成熟智能体框架。

## 能做什么

SkillPilot 接收一段自然语言需求，例如：

```text
我想让 Claude 帮我阅读 PDF 并总结重点
帮我构造一个根据课程课件给作业题提示知识点但不直接给答案的 Skill
我需要连接 GitHub issue 并读取仓库上下文
```

系统会完成以下工作：

- 将用户需求解析成结构化任务信息。
- 判断需求更适合 Claude Skill、Claude Code Plugin、MCP Server、混合方案或未知类型。
- 基于扩展类型选择固定的高优先级信息源。
- 执行 source-aware 查询，并保留搜索状态、失败原因和 source id。
- 读取页面或 GitHub 仓库内容，抽取 README、`SKILL.md`、配置文件和元数据。
- 让 LLM 直接阅读候选原文，输出候选字段、能力匹配、文档证据、安全风险和评分。
- 用确定性 guardrail 做最终推荐、补充构造或自定义 Skill 决策。
- 输出中文推荐报告和 JSON 决策轨迹。
- 在需要时生成一个 Claude Skill 草案目录。

## 当前架构

```text
用户需求
  -> SkillPilotPipeline
     -> RequirementAnalysisAgent
        -> RequirementParser
        -> ExtensionTypeClassifier
        -> SourcePlanner
     -> SourceDiscoveryAgent
        -> SearchExecutor / SourceSearchAgent
        -> ContentReader / PageReader / RepoReader
     -> CandidateEvaluationAgent
        -> CandidateEvaluator
        -> LocalCandidateCache
     -> DecisionAgent
        -> DecisionGate
     -> SkillBuilderAgent
        -> QuestionPlanner
        -> SkillSpecGenerator
        -> SafetyReviewer
        -> SkillBuilder
     -> ReportAgent
        -> RecommendationWriter
```

主要目录：

```text
skillpilot/
  agents/                 # Agent 编排层
  skills/                 # 可被 Agent 调用的能力模块
    builder/              # Skill 构造相关能力
    discovery/            # 搜索源、搜索执行和内容读取
  models.py               # Pydantic 数据模型
  pipeline.py             # 主流程编排
  config.py               # 环境变量配置
  llm.py                  # LLM 适配层
  safety.py               # 风险策略
  scoring.py              # 评分权重
  utils.py                # 通用工具
  web.py                  # 本地 Web UI 服务与 JSON API
  web_assets/             # Web UI 静态页面、样式和交互脚本
```

## Agent 与 Skill

`RequirementAnalysisAgent` 负责理解需求、判断扩展类型并规划搜索源。它调用 `RequirementParser`、`ExtensionTypeClassifier` 和 `SourcePlanner`。

`SourceDiscoveryAgent` 负责资源发现和内容读取。它调用 `SearchExecutor`、`SourceSearchAgent`、`ContentReader`、`PageReader` 和 `RepoReader`。

资源发现使用 `docs/stage_2_3_source_access.json` 作为网页/API 搜索指导。每个 `source_id` 都有一个 JSON 条目，声明入口 URL、搜索器类型、内容格式、查询参数、结果字段映射、详情读取策略、风险提示和失败处理方式。运行时 `SourceAccessGuideLoader` 会按 `SearchQuery.source_id` 读取对应条目，`SourceSearchTool` 再按 `searcher_type` 分发到 marketplace JSON、registry API、docs keyword 或 GitHub contents 等通用搜索器。

`CandidateEvaluationAgent` 负责候选理解和评分。它调用 `CandidateEvaluator`，在离线或搜索全部跳过时可使用 `LocalCandidateCache`。

`DecisionAgent` 负责最终决策。它调用 `DecisionGate`，根据匹配分、风险等级和候选可用性选择推荐现有资源、推荐现有资源并补充自定义 Skill，或直接构造自定义 Skill。

`SkillBuilderAgent` 负责构造 Skill 草案。它会生成澄清问题、处理三选项和自由文本回答、生成 Skill 规格、做安全审查，并写入 `SKILL.md`、`resources/`、`examples/` 等文件。

`ReportAgent` 负责写出推荐报告和决策轨迹。

## LLM 与确定性逻辑

SkillPilot 使用 LLM 处理语义判断和结构化理解，包括：

- 需求解析
- 扩展类型判断
- source-aware 查询规划
- 候选原文理解与评分
- 决策原因润色
- Skill 规格和资源内容生成
- Skill 构造安全审查

以下逻辑保持确定性：

- URL 解析和 GitHub 仓库路径解析
- 文件写入
- 配置读取
- 枚举校验
- 搜索和读取上限
- 评分聚合公式
- 高风险 guardrail
- 第三方扩展不自动安装、不自动运行

## 安全原则

SkillPilot 不会自动安装、运行或授权第三方 Plugin、MCP Server、脚本或仓库代码。

以下行为会被重点标记为高风险：

- 执行 shell 命令
- 写入、覆盖或批量删除文件
- 自动 hook 或后台执行
- 读取、收集或传输 API key、token、账号凭据
- 操作数据库
- 连接远程服务并执行写操作
- 生成或分发未经审查的脚本

高风险候选不会被鼓励直接安装。系统会给出风险原因、安全替代方案，或转入更小权限的自定义 Skill 草案流程。

## 安装与环境

在 WSL 中进入项目：

```bash
conda activate skill_pilot
cd /home/achewwa/Projects/SkillPilot
```

运行测试：

```bash
conda run -n skill_pilot python -m pytest
```

也可以直接使用当前环境运行：

```bash
python -m pytest
```

## 命令行使用

进入交互式会话：

```bash
python main.py
```

推荐现有扩展或方案：

```bash
python main.py recommend "我想让 Claude 自动生成 Python 单元测试并分析失败原因"
```

直接构造自定义 Skill 草案：

```bash
python main.py build-skill "帮我构造一个根据课程课件给作业题提示知识点但不直接给答案的 Skill"
```

运行演示案例：

```bash
python main.py demo --case skill
python main.py demo --case mcp
python main.py demo --case build
```

启动本地 Web UI：

```bash
python main.py web
```

默认地址是 `http://127.0.0.1:8000`。Web UI 复用 `SkillPilotAgent` 和现有 pipeline，提供比 CLI 更方便的本地交互界面。

交互式会话支持：

```text
/build <需求>      直接进入 Skill 构造流程
/demo skill|mcp|build
/help
/exit
```

当推荐流程决定进入自定义 Skill 构造时，CLI 会先打印决策阶段摘要，包括 decision type、原因、候选数量、最佳候选和读取成功数，并预先写出 `outputs/recommendation_report.md`。随后才进入 Builder 澄清问答；Builder 结束后报告会被更新为包含 Skill 草案信息的最终版本。

## 输出文件

默认输出：

```text
outputs/recommendation_report.md
outputs/decision_trace.json
generated_skills/<skill-slug>/SKILL.md
generated_skills/<skill-slug>/resources/
generated_skills/<skill-slug>/examples/
```

`recommendation_report.md` 包含：

- 用户需求理解
- 扩展类型判断
- 搜索计划和搜索源
- 搜索结果
- 页面与仓库读取结果
- 失败处理
- 候选资源与评分
- 决策结果
- SkillBuilder 构造过程
- 安全提示

`decision_trace.json` 保存完整结构化轨迹，包括需求、分类、搜索计划、搜索结果、读取内容、候选评分、最终决策、Skill 草案信息和 agent/skill trace events。

## Web UI

启动本地 Web UI：

```bash
python main.py web --host 127.0.0.1 --port 8000
```

默认地址是 `http://127.0.0.1:8000`。Web UI 运行时遵循当前环境变量配置，例如 `SKILLPILOT_LLM_PROVIDER`、`SKILLPILOT_ENABLE_NETWORK_SEARCH` 和输出目录配置。

## 配置

默认 LLM provider 是 WSL 本地 `claude` CLI，复用本机 Claude Code 配置，不在项目中保存 API key 或 endpoint。
项目默认显式使用 `claude-sonnet-4-6`，避免跟随 Claude CLI 的本地默认模型变化。

常用 LLM 配置：

```bash
export SKILLPILOT_LLM_PROVIDER=claude_cli
export SKILLPILOT_CLAUDE_COMMAND=claude
export SKILLPILOT_CLAUDE_MODEL=claude-sonnet-4-6
export SKILLPILOT_CLAUDE_MAX_BUDGET_USD=0.05
export SKILLPILOT_ENABLE_LLM_EVALUATION=1
```

离线测试可使用静态 JSON provider：

```bash
export SKILLPILOT_LLM_PROVIDER=static_json
```

搜索配置：

```bash
export SKILLPILOT_ENABLE_NETWORK_SEARCH=1
export SKILLPILOT_SEARCH_TIMEOUT_SECONDS=8
export SKILLPILOT_SEARCH_MAX_RESULTS=5
export SKILLPILOT_HTTP_PROXY=http://172.22.0.1:7890
export GITHUB_TOKEN=<optional-token>
```

如果没有显式设置 `GITHUB_TOKEN` 或 `GH_TOKEN`，SkillPilot 会尝试读取本机 GitHub CLI 登录态：

```bash
gh auth token
```

该 token 只在运行时传给 GitHub API，不会写入项目文件、报告或 trace。

Builder 配置：

```bash
export SKILLPILOT_BUILDER_INTERACTIVE=1
export SKILLPILOT_BUILDER_MAX_ROUNDS=3
export SKILLPILOT_OUTPUTS_DIR=outputs
export SKILLPILOT_GENERATED_SKILLS_DIR=generated_skills
```

## 当前测试状态

当前测试命令：

```bash
conda run -n skill_pilot python -m pytest
```

当前测试结果：

```text
41 passed
```

## 参考文件

- `project_info.md`：项目同步信息、结构说明和后续开发注意事项。
- `docs/pipeline_agent_skill_mapping.md`：pipeline、agent、skill 与当前代码路径的映射。
- `docs/stage_2_3_source_access.json`：source-specific 网页/API 搜索与读取的结构化运行指南。
- `data/demo_cases.json`：演示用需求样例。
- `data/candidate_cache.json`：离线或跳过搜索时使用的本地候选缓存。
