# SkillPilot Project Info

本文件用于跨窗口同步 SkillPilot 的当前项目状态、实现逻辑、运行方式和后续开发注意事项。

## 项目定位

SkillPilot 是一个用 Python 手动搭建的轻量级 LLM 智能体项目，面向 Claude 扩展生态中的 Skill、Claude Code Plugin、MCP Server 和混合方案选择问题。

给定用户自然语言需求后，系统会完成需求理解、扩展类型判断、固定来源检索、内容读取、候选资源评分、安全风险判断、推荐报告输出，以及必要时的自定义 Skill 草案生成。

项目用于《大语言模型与信息决策》课程展示。核心原则是自行实现 agent 工作流和 skill 调度，不依赖 LangChain、CrewAI、AutoGPT 等成熟智能体框架。

## 当前实现原则

- Python 是主实现语言。
- CLI 是主要交互界面。
- 核心结构是 `pipeline-agent-skill`。
- LLM 负责语义理解、结构化判断、候选原文评分、决策解释和 Skill 内容生成。
- 确定性逻辑负责 URL 解析、配置读取、文件写入、枚举校验、读取上限、评分聚合和高风险 guardrail。
- 不自动安装第三方 Plugin、MCP Server、脚本或仓库代码。
- 不自动执行候选资源中的 shell 命令。
- 不在项目中保存 API key、token 或 endpoint。
- 不为任何特例添加专门兜底选项；兜底逻辑应保持通用、可解释、可测试。

## 当前代码结构

```text
SkillPilot/
  main.py
  pyproject.toml
  README.md
  project_info.md
  data/
    candidate_cache.json
    demo_cases.json
  docs/
    pipeline_agent_skill_mapping.md
    stage_2_3_source_access.json
  skillpilot/
    agent.py
    cli.py
    config.py
    llm.py
    models.py
    pipeline.py
    safety.py
    scoring.py
    utils.py
    agents/
      core.py
      requirement.py
      discovery.py
      evaluation.py
      decision.py
      builder.py
      report.py
    skills/
      core.py
      requirement.py
      classification.py
      planning.py
      cache.py
      evaluation.py
      decision.py
      report.py
      discovery/
        source_catalog.py
        source_access_guide.py
        search_tools.py
        readers.py
      builder/
        question_planner.py
        skill_spec_generator.py
        safety_reviewer.py
        packaging_advisor.py
        skill_builder.py
        skill_md_writer.py
        skill_structure_planner.py
        resource_generator.py
  tests/
```

`skillpilot/agents/` 只放 Agent 编排逻辑。  
`skillpilot/skills/` 放可被 Agent 调用的能力模块。  
项目代码入口集中在 `skillpilot/agents/`、`skillpilot/skills/`、`skillpilot/pipeline.py` 和 `skillpilot/cli.py`。

## Pipeline

主入口是 `skillpilot.pipeline.SkillPilotPipeline`。

当前 pipeline 顺序：

1. 创建 `PipelineContext`。
2. `RequirementAnalysisAgent` 解析需求、判断扩展类型、规划搜索。
3. `SourceDiscoveryAgent` 执行 source-aware 搜索并读取页面或仓库内容。
4. `CandidateEvaluationAgent` 评分候选资源；在离线或全部跳过搜索时可读取本地缓存。
5. `DecisionAgent` 根据候选分数和风险等级做最终决策。
6. 当决策需要构造 Skill 时，`SkillBuilderAgent` 生成自定义 Skill 草案。
7. `ReportAgent` 写出 Markdown 推荐报告。
8. `RecommendationWriter` 写出 JSON 决策轨迹。

`PipelineContext` 保存整次运行的共享状态，包括需求、分类、搜索计划、搜索结果、读取内容、候选评分、决策、Skill 草案、报告路径、trace 路径和 agent/skill trace events。

## Agents

### RequirementAnalysisAgent

文件：`skillpilot/agents/requirement.py`

调用的 skills：

- `RequirementParser`
- `ExtensionTypeClassifier`
- `SourcePlanner`

职责：

- 将自然语言需求转换成 `ParsedRequirement`。
- 判断目标扩展类型：`skill`、`mcp`、`plugin`、`mixed` 或 `unknown`。
- 根据扩展类型和需求能力生成 `SearchPlan`。

### SourceDiscoveryAgent

文件：`skillpilot/agents/discovery.py`

调用的 skills：

- `SearchExecutor`
- `SourceSearchAgent`
- `SourceSearchTool`
- `ContentReader`
- `PageReader`
- `RepoReader`

职责：

- 按 `SearchPlan` 执行固定来源搜索。
- 将查询按 `source_id` 分组，并发调度 source-level search agent。
- 保留搜索成功、失败、无结果、跳过等状态。
- 读取成功搜索结果中的页面或 GitHub 仓库内容。
- 保留读取状态、错误信息、元数据和截断后的正文。

### CandidateEvaluationAgent

文件：`skillpilot/agents/evaluation.py`

调用的 skills：

- `CandidateEvaluator`
- `LocalCandidateCache`

职责：

- 让 LLM 直接阅读 `RetrievedContent.content`。
- 生成候选名称、类型、描述、能力、安装线索、依赖、权限、维护信息和证据。
- 输出能力分、文档分、安全分、风险等级、风险原因和评分理由。
- 使用评分权重聚合最终分数。
- 在网络搜索关闭或全部跳过时使用本地候选缓存。

### DecisionAgent

文件：`skillpilot/agents/decision.py`

调用的 skill：

- `DecisionGate`

职责：

- 当没有足够候选或分数过低时，进入自定义 Skill 草案流程。
- 当候选高风险时，不直接推荐安装，转向更安全的自定义 Skill 或人工审查建议。
- 当候选分数较高且风险可接受时，推荐现有资源。
- 当候选中等相关时，推荐参考现有资源并补充自定义 Skill。
- 可以调用 LLM 生成更清晰的中文决策原因，但不允许 LLM 改变确定性 decision type。

### SkillBuilderAgent

文件：`skillpilot/agents/builder.py`

调用的 skills：

- `DetailOptionGenerator`
- `QuestionPlanner`
- `SkillSpecGenerator`
- `SafetyReviewer`
- `PackagingAdvisor`
- `SkillBuilder`
- `SkillMdWriter`
- `SkillStructurePlanner`
- `ResourceGenerator`

职责：

- 根据需求和决策进入 Skill 构造流程。
- 最多进行配置指定轮数的澄清问答。
- 每个澄清问题提供三个可选细节选项，同时保留自由文本回答。
- 生成 `SkillSpec`，包括名称、slug、描述、触发条件、工作流、约束、输出格式、资源文件和示例文件。
- 做 Skill 安全审查。
- 生成 `SKILL.md`、`resources/`、`examples/`、`README.md` 等文件。
- 高风险请求会写出 `SAFE_DESIGN.md`，而不是生成完整可用 Skill。

### ReportAgent

文件：`skillpilot/agents/report.py`

调用的 skill：

- `RecommendationWriter`

职责：

- 写出 `outputs/recommendation_report.md`。
- 写出 `outputs/decision_trace.json`。
- 记录 report 和 trace 写入事件。

## Skills

核心 skill 文件：

- `skillpilot/skills/requirement.py`：需求解析。
- `skillpilot/skills/classification.py`：扩展类型判断。
- `skillpilot/skills/planning.py`：搜索源和查询规划。
- `skillpilot/skills/cache.py`：本地候选缓存读取。
- `skillpilot/skills/evaluation.py`：候选理解、评分和风险解释。
- `skillpilot/skills/decision.py`：决策 gate 和决策原因。
- `skillpilot/skills/report.py`：报告和 trace 写入。

Discovery skills：

- `skillpilot/skills/discovery/source_catalog.py`
- `skillpilot/skills/discovery/source_access_guide.py`
- `skillpilot/skills/discovery/search_tools.py`
- `skillpilot/skills/discovery/readers.py`

Builder skills：

- `skillpilot/skills/builder/question_planner.py`
- `skillpilot/skills/builder/skill_spec_generator.py`
- `skillpilot/skills/builder/safety_reviewer.py`
- `skillpilot/skills/builder/resource_generator.py`
- `skillpilot/skills/builder/skill_builder.py`
- `skillpilot/skills/builder/skill_md_writer.py`
- `skillpilot/skills/builder/skill_structure_planner.py`
- `skillpilot/skills/builder/packaging_advisor.py`

## 数据模型

主要 Pydantic 模型在 `skillpilot/models.py`：

- `ParsedRequirement`
- `TypeClassification`
- `SearchSource`
- `SearchQuery`
- `SearchResult`
- `RetrievedContent`
- `SearchPlan`
- `Candidate`
- `CandidateEvaluation`
- `Decision`
- `AgentSkillTraceEvent`
- `BuilderSession`
- `BuilderTurn`
- `ClarificationQuestion`
- `ClarificationOption`
- `SkillSpec`
- `SkillResourceSpec`
- `SafetyReviewResult`
- `SkillDraftResult`
- `AgentRunResult`

这些模型同时服务于 pipeline 内部状态、报告输出、JSON trace 和测试断言。

## 搜索源

固定源目录在 `skillpilot/skills/discovery/source_catalog.py`。

当前覆盖：

- Skill 来源：
  - `anthropic_skills_repo`
  - `anthropic_agent_skills_docs`
  - `anthropic_skills_cookbook`
  - `skillsmp_directory`
- MCP 来源：
  - `official_mcp_registry`
  - `glama_mcp`
  - `smithery_mcp`
- Plugin 来源：
  - `anthropic_official_plugin_marketplace`
  - `anthropic_community_plugin_marketplace`
  - `anthropic_demo_plugin_marketplace`
  - `ccplugins_awesome_marketplace`

`SourcePlanner` 只基于这些固定 source 生成 source-aware 查询。搜索结果和读取内容都会保留 `source_id`，便于 trace 和报告解释。

Source-specific 网页/API 搜索由 `docs/stage_2_3_source_access.json` 指导。JSON 中每个 `source_id` 对应一个结构化条目，包含 `searcher_type`、`reader_type`、`entrypoint`、`content_format`、`query_parameters`、`result_mapping`、`detail_reading`、`risk_notes` 和 `failure_handling`。运行时 `SourceAccessGuideLoader` 根据查询的 `source_id` 取出对应条目，`SourceSearchTool` 再按 `searcher_type` 分发到可复用搜索器：

- `skillsmp_api_searcher`
- `marketplace_json_searcher`
- `docs_keyword_searcher`
- `github_contents_searcher`
- `mcp_registry_api_searcher`
- `glama_api_searcher`
- `smithery_api_searcher`

这样新增或调整搜索源时，优先更新 JSON 中的 source metadata 和网页/API 访问指导；Python 中只保留少量通用搜索器和 dispatcher。

## 评分与决策

评分权重在 `skillpilot/scoring.py`：

- capability match：45%
- type match：15%
- documentation quality：20%
- safety risk：20%

其中 capability、documentation、safety 主要来自 LLM 结构化评分；type match 是确定性比较。最终候选按 `match_score` 降序排列。

风险策略在 `skillpilot/safety.py`。涉及命令执行、写文件、删除、hook、token、API key、数据库、远程写操作等能力时，会提高风险等级并降低 safety score。

## LLM 配置

默认 provider：`claude_cli`。

适配层文件：`skillpilot/llm.py`。

`ClaudeCliLLM` 通过 stdin 向本地 `claude -p` 发送 prompt，并默认关闭工具和会话持久化。项目复用本机 Claude CLI 配置，不保存密钥。当前默认显式传入模型 `claude-sonnet-4-6`。

可选 provider：

- `claude_cli`：实际运行使用。
- `static_json`：离线测试或 smoke run 使用，返回固定 JSON。

常用环境变量：

```bash
SKILLPILOT_LLM_PROVIDER=claude_cli
SKILLPILOT_CLAUDE_COMMAND=claude
SKILLPILOT_CLAUDE_MODEL=claude-sonnet-4-6
SKILLPILOT_CLAUDE_MAX_BUDGET_USD=0.05
SKILLPILOT_CLAUDE_DISABLE_TOOLS=1
SKILLPILOT_CLAUDE_NO_SESSION=1
SKILLPILOT_ENABLE_LLM_EVALUATION=1
```

## 搜索与 Builder 配置

搜索配置在 `skillpilot/config.py`：

```bash
SKILLPILOT_ENABLE_NETWORK_SEARCH=1
SKILLPILOT_SEARCH_TIMEOUT_SECONDS=8
SKILLPILOT_SEARCH_MAX_RESULTS=5
SKILLPILOT_SEARCH_USER_AGENT=SkillPilot/0.1
SKILLPILOT_HTTP_PROXY=http://172.22.0.1:7890
SKILLPILOT_HTTPS_PROXY=http://172.22.0.1:7890
GITHUB_TOKEN=<optional>
GH_TOKEN=<optional>
```

GitHub token 优先读取 `GITHUB_TOKEN` 或 `GH_TOKEN`。如果二者都没有设置，配置层会尝试调用本机 `gh auth token` 复用 GitHub CLI 登录态；token 只在运行时传给 GitHub API，不写入报告或 trace。

Builder 配置：

```bash
SKILLPILOT_BUILDER_INTERACTIVE=1
SKILLPILOT_BUILDER_MAX_ROUNDS=3
SKILLPILOT_OUTPUTS_DIR=outputs
SKILLPILOT_GENERATED_SKILLS_DIR=generated_skills
```

## CLI

入口：

```bash
python main.py
```

命令：

```bash
python main.py recommend "<需求>"
python main.py build-skill "<需求>"
python main.py demo --case skill
python main.py demo --case mcp
python main.py demo --case build
```

交互模式指令：

```text
/build <需求>
/demo skill|mcp|build
/help
/exit
```

## 输出

默认输出路径：

```text
outputs/recommendation_report.md
outputs/decision_trace.json
generated_skills/<skill-slug>/
```

报告包含需求理解、扩展类型、搜索计划、搜索结果、读取结果、失败处理、候选评分、最终决策、SkillBuilder 构造过程和安全提示。

在交互式 CLI 中，如果决策需要进入 `SkillBuilderAgent`，pipeline 会先写出一版 interim `recommendation_report.md`，CLI 会打印决策阶段摘要，然后再进入 Builder 澄清问答。Builder 完成后，报告会被最终结果覆盖更新。

Trace 保存完整结构化 `AgentRunResult`，包括 `trace_events`。每个 trace event 记录：

- agent
- skill
- status
- summary
- metadata

## 测试状态

当前测试命令：

```bash
conda run -n skill_pilot python -m pytest
```

当前结果：

```text
41 passed
```

测试覆盖重点：

- CLI smoke 行为
- 搜索规划和 source catalog
- source-specific search executor
- 页面和 GitHub 仓库读取
- 候选评估和决策 gate
- LLM 驱动的分类、查询规划、决策解释和安全审查
- SkillBuilder 问答、动态 Skill 输出和高风险阻断
- pipeline trace events

## 当前开发状态

当前工作分支：

```text
refactor/physical-agent-skill-layout
```

当前实现已经采用 `agents/` 和 `skills/` 物理结构。`generated_skills/xiaohongshu-collage-composer/` 是未跟踪生成目录，除非明确需要，不应纳入本轮项目结构修改。

## 后续建议

1. 为课堂展示准备 2 到 3 个稳定 demo：
   - Skill 推荐
   - MCP 推荐或自定义构造
   - 直接构造 Skill
2. 记录成功运行的终端输出、报告和 trace，避免课堂现场依赖不稳定网络。
3. 根据 demo 结果微调 LLM prompt，使报告中的候选证据和风险说明更清晰。
4. 为 `SourceSearchTool` 增加更多固定 source 的真实 API reader/searcher。
5. 为高风险 Skill 构造路径增加更多安全审查测试。
6. 准备课程 PPT 和最终中文报告。

## 重要文件

- `README.md`：面向用户和展示的项目说明。
- `project_info.md`：当前项目同步记忆。
- `docs/pipeline_agent_skill_mapping.md`：当前 pipeline-agent-skill 路径映射。
- `docs/stage_2_3_source_access.json`：source-specific 网页/API 搜索和读取的结构化运行指南。
- `data/demo_cases.json`：demo 输入。
- `data/candidate_cache.json`：离线候选缓存。
