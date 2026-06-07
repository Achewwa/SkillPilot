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

## 安装与环境

```bash
cd SkillPilot
conda create -n skill_pilot python=3.11
conda activate skill_pilot
pip install -e .
```

# 环境变量配置

```bash
export SKILLPILOT_CLAUDE_MODEL=your_claude_model
export GITHUB_TOKEN=your_github_token
```

Claude Code 其他配置直接从本地 claude-cli 读取;

如果没有显式设置 `GITHUB_TOKEN` 或 `GH_TOKEN`，SkillPilot 会尝试读取本机 GitHub CLI 登录态：

```bash
gh auth token
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

启动本地 Web UI：

```bash
python main.py web --host 127.0.0.1 --port 8000
```

## 输出文件

默认输出：

```text
outputs/recommendation_report.md
outputs/decision_trace.json

# ---若进入构造skill阶段---
generated_skills/<skill-slug>/SKILL.md
generated_skills/<skill-slug>/resources/
generated_skills/<skill-slug>/examples/
```