# SkillPilot 项目计划草案

## 一、项目名称

**SkillPilot：面向 Claude 扩展生态的智能推荐与自定义 Skill 构造 Agent**

也可以使用完整副标题：

**SkillPilot：一个不依赖成熟 Agent 框架的 Claude Skill / Plugin / MCP 搜索、评估与构造智能体**

---

## 二、项目定位

SkillPilot 是一个面向 Claude 扩展生态的轻量级智能体工具。它的核心目标是：根据用户的自然语言需求，自动判断用户更适合使用 Skill、Plugin、MCP，还是组合方案；随后在官方文档、GitHub 仓库、社区目录等来源中搜索相关扩展资源，并对候选资源进行功能匹配、可信度评估和安全风险分析。如果没有找到足够合适的现成资源，SkillPilot 可以在安全边界内帮助用户生成一个自定义 Skill 草案。

简单来说，SkillPilot 要解决的问题是：

> 用户知道自己想让 Claude 做什么，但不知道应该找 Skill、Plugin 还是 MCP，也不知道哪些资源可靠。如果没有现成资源，系统还能帮助用户构造一个可用的自定义 Skill。

---

## 三、项目背景与动机

随着大语言模型智能体生态的发展，模型能力的扩展已经不再只是依靠提示词，而是越来越多地依赖外部扩展机制。以 Claude / Claude Code 生态为例，用户可以通过 Skill 让 Claude 掌握某类任务流程，通过 MCP 连接外部工具和数据源，也可以通过 Plugin 打包和分发一整套 Claude Code 扩展能力。

但是，对于普通用户来说，这个生态存在几个实际问题。

第一，概念边界不清。很多用户并不清楚 Skill、Plugin 和 MCP 的区别。例如，若用户希望 Claude 按固定格式检查论文，这更适合 Skill；若用户希望 Claude 访问 GitHub Issue 或数据库，这更适合 MCP；若用户想安装一整套代码审查工作流，则可能需要 Plugin。

第二，资源分布分散。Claude Skills、Claude Code Plugins、MCP servers、GitHub 仓库、官方文档和第三方目录分布在不同位置。用户需要自己搜索、阅读 README、比较功能、判断维护状态和安装方式，成本较高。

第三，安全风险不透明。某些 Plugin 或 MCP server 可能涉及本地文件读写、shell 命令执行、hooks 自动触发、外部 API token、数据库连接等能力。用户如果只看功能描述，很难判断其真实权限风险。

第四，现成资源未必满足个性化需求。当用户需求较为具体时，可能找不到完全匹配的 Skill 或 Plugin。此时，如果只是返回“没有找到结果”，智能体的价值有限；更好的方式是分析需求缺口，并在允许范围内生成一个自定义 Skill 草案。

因此，SkillPilot 试图构建一个完整的“搜索—评估—推荐—构造”闭环：既能帮助用户寻找现成扩展，也能在找不到合适扩展时辅助用户自定义能力。

---

## 四、项目目标

本项目计划使用 Python 自行实现一个轻量级 Agent 框架，不使用 LangChain、CrewAI、AutoGPT 等成熟智能体开发框架。项目重点不在于调用某个现成 Agent 平台，而在于自行实现智能体的任务理解、工具调用、状态管理、候选评估、风险判断和决策流程。

SkillPilot 的具体目标包括：

1. **需求理解**
   解析用户自然语言需求，识别任务领域、所需能力、使用场景、是否需要外部工具、是否涉及文件读写或命令执行等信息。

2. **扩展类型判断**
   判断用户需求更适合 Skill、Plugin、MCP，还是混合方案。

3. **候选资源搜索**
   自动生成搜索计划，在官方文档、GitHub 仓库、社区资源目录等来源中检索候选扩展。

4. **候选信息抽取**
   从网页、README、SKILL.md、安装说明等内容中抽取结构化信息，包括功能描述、安装方式、依赖项、维护状态、权限风险等。

5. **功能匹配与排序**
   根据用户需求对候选资源进行匹配评分，判断其满足程度和缺失能力。

6. **可信度与风险评估**
   根据来源、维护情况、文档完整度、权限要求、脚本行为等因素评估候选资源的可信度和安全风险。

7. **推荐报告生成**
   输出推荐结果、推荐理由、风险提示、安装建议和替代方案。

8. **自定义 Skill 构造**
   当没有合适现成资源时，生成自定义 Skill 的文件结构、`SKILL.md`、资源模板、示例输入输出和使用说明。

9. **过程记录与可解释性**
   保存搜索路径、候选评分、决策理由和最终输出，方便复现和展示 Agent 的工作过程。

---

## 五、核心概念说明

SkillPilot 需要明确区分 Skill、Plugin 和 MCP 三类扩展形式。

### 1. Skill

Skill 主要解决的是：

> Claude 应该如何完成某类任务？

它更像是一份任务说明书或专家能力包，通常包含任务流程、输出模板、注意事项、示例、规则和必要的辅助脚本。Skill 适用于写作规范、论文审查、代码风格检查、数据分析流程、作业提示、实验报告格式检查等场景。

例如：

```text
用户需求：我想让 Claude 按照课程论文要求检查摘要、关键词、论证结构和引用格式。
推荐类型：Skill
原因：该任务主要是规范 Claude 的处理流程，不一定需要连接外部工具。
```

### 2. MCP

MCP 主要解决的是：

> Claude 需要连接什么外部工具或数据源？

它适合让 Claude 访问 GitHub、数据库、文件系统、搜索工具、网盘、浏览器、项目管理平台等外部系统。MCP 的能力更强，但也通常伴随更高的权限风险。

例如：

```text
用户需求：我想让 Claude 读取 GitHub Issue，并根据 Issue 修改代码。
推荐类型：MCP 或 Plugin + MCP
原因：该任务需要访问外部 GitHub 数据和本地代码仓库。
```

### 3. Plugin

Plugin 主要解决的是：

> 如何把一整套扩展能力打包、安装和分发？

一个 Plugin 可以包含多个 Skills、MCP servers、hooks、commands、subagents 等组件。它更像一个完整的 Claude Code 扩展包，适合复杂工作流。

例如：

```text
用户需求：我想安装一整套代码审查工作流，包括代码扫描、测试生成、PR 总结和安全检查。
推荐类型：Plugin
原因：该需求涉及多个子能力，适合打包为完整扩展方案。
```

---

## 六、系统总体架构

SkillPilot 采用“主 Agent + 多个 Skill 模块”的结构。

总体流程如下：

```text
用户自然语言需求
    ↓
RequirementParser：需求解析
    ↓
ExtensionTypeClassifier：判断 Skill / Plugin / MCP / 混合方案
    ↓
SourcePlanner：规划搜索来源
    ↓
SearchTools：网页搜索 / GitHub 搜索 / 本地缓存搜索
    ↓
PageReader / RepoReader：读取网页、README、SKILL.md
    ↓
CandidateExtractor：抽取候选资源信息
    ↓
CapabilityMatcher：功能匹配评分
    ↓
TrustEvaluator：可信度评估
    ↓
RiskAnalyzer：安全风险分析
    ↓
DecisionGate：推荐现有资源 or 构造自定义 Skill
    ↓
RecommendationWriter / SkillBuilder
    ↓
最终推荐报告或自定义 Skill 包
```

系统的关键特点是：

1. 不直接把搜索结果原样返回给用户；
2. 不把所有需求都归为“找插件”；
3. 会显式区分 Skill、Plugin 和 MCP；
4. 会对候选资源进行评分和风险分析；
5. 找不到合适资源时，可以进入自定义 Skill 构造流程。

---

## 七、Agent 主体设计

SkillPilot Agent 是整个系统的调度中心，负责维护状态、选择工具、记录中间结果并做出最终决策。

Agent 的基本循环可以设计为：

```text
Observe：接收用户需求和当前上下文
Plan：判断需要调用哪些模块
Act：调用搜索、读取、解析、评估等工具
Reflect：检查结果是否充分，是否需要补充搜索
Decide：判断推荐现成资源还是构造自定义 Skill
Report：输出最终推荐报告或 Skill 生成结果
```

主 Agent 状态可以设计为：

```python
agent_state = {
    "user_requirement": "",
    "parsed_requirement": {},
    "extension_type": "",
    "search_plan": [],
    "raw_sources": [],
    "candidates": [],
    "evaluated_candidates": [],
    "decision": "",
    "custom_skill_spec": {},
    "final_output": ""
}
```

---

## 八、核心模块设计

### 1. RequirementParser：需求解析模块

该模块负责把用户自然语言需求转化为结构化需求。

示例输入：

```text
我想让 Claude Code 帮我自动生成 Python 单元测试，运行测试，并根据失败结果提示修改方向。
```

示例输出：

```json
{
  "task_domain": "software_engineering",
  "desired_capabilities": [
    "generate_tests",
    "run_tests",
    "analyze_test_failures"
  ],
  "requires_codebase_access": true,
  "requires_command_execution": true,
  "requires_external_service": false,
  "risk_tolerance": "medium",
  "preferred_extension_type": "unknown"
}
```

这个模块可以由 LLM 辅助完成，但需要通过固定 JSON schema 限制输出格式，保证后续模块可以稳定读取。

---

### 2. ExtensionTypeClassifier：扩展类型判断模块

该模块判断用户需求更适合 Skill、Plugin、MCP 还是混合方案。

判断规则包括：

```text
如果需求主要是任务流程、写作规范、检查清单、格式要求 → Skill
如果需求需要访问外部工具、数据库、GitHub、网盘、浏览器 → MCP
如果需求是一整套 Claude Code 工作流，包含命令、hooks、MCP、多个技能 → Plugin
如果现有资源不足，但需求可以用说明、模板、脚本表达 → 自定义 Skill
```

输出示例：

```json
{
  "recommended_type": "skill",
  "confidence": 0.82,
  "reason": "用户需求主要是规范 Claude 如何完成一类任务，不需要连接外部系统。"
}
```

---

### 3. SourcePlanner：搜索源规划模块

该模块根据扩展类型生成搜索计划。

如果推荐类型是 Skill，则搜索来源包括：

```text
Claude Skills 文档
Anthropic Skills 示例仓库
GitHub 中包含 SKILL.md 的仓库
社区 Skill 目录
```

如果推荐类型是 MCP，则搜索来源包括：

```text
MCP 官方文档
MCP server 目录
GitHub 上相关 MCP server
目标服务的官方集成说明
```

如果推荐类型是 Plugin，则搜索来源包括：

```text
Claude Code Plugins 文档
Plugin marketplace 或目录
GitHub 上的 Claude Code plugin 仓库
相关 README 和安装说明
```

---

### 4. SearchTools：搜索模块

该模块负责执行搜索。MVP 阶段可以支持三种搜索方式：

```text
网页搜索
GitHub 搜索
本地缓存搜索
```

为了保证课堂演示稳定，可以提前缓存若干搜索结果和 README 文本。如果现场网络不稳定，Agent 仍然可以在缓存数据上完成推荐流程。

---

### 5. PageReader / RepoReader：页面和仓库读取模块

该模块负责读取候选资源页面，并提取关键信息。

对 Skill 类型资源，重点读取：

```text
SKILL.md
README.md
resources/
scripts/
examples/
```

对 MCP 类型资源，重点读取：

```text
server 功能
支持的数据源或工具
认证方式
API key 要求
读写权限
安装方式
运行命令
```

对 Plugin 类型资源，重点读取：

```text
包含哪些 skills
是否包含 MCP servers
是否包含 hooks
是否包含 slash commands
是否包含安装脚本
是否需要本地命令执行
```

---

### 6. CandidateExtractor：候选资源抽取模块

该模块将网页或 README 中的非结构化信息转化为统一格式。

候选对象可以设计为：

```python
@dataclass
class Candidate:
    name: str
    extension_type: str
    source_url: str
    description: str
    capabilities: list[str]
    installation: str | None
    dependencies: list[str]
    permissions: list[str]
    maintainer: str | None
    last_updated: str | None
    evidence: list[str]
```

示例输出：

```json
{
  "name": "code-review-skill",
  "extension_type": "skill",
  "description": "Help Claude perform structured code reviews",
  "capabilities": ["code_review", "security_check", "style_check"],
  "installation": "copy skill folder to .claude/skills/",
  "permissions": ["read_code"],
  "evidence": ["README describes structured code review workflow"]
}
```

---

### 7. CapabilityMatcher：功能匹配模块

该模块根据用户需求对候选资源进行评分。

建议评分维度如下：

```text
功能匹配度：40%
类型匹配度：15%
安装便利性：10%
文档完整度：10%
维护活跃度：10%
安全风险：15%
```

输出示例：

```json
{
  "candidate_name": "testing-skill",
  "match_score": 0.78,
  "matched_capabilities": [
    "generate_tests",
    "run_tests"
  ],
  "missing_capabilities": [
    "analyze_test_failures"
  ],
  "reason": "该资源支持测试生成和运行，但没有明确说明可以分析失败原因。"
}
```

---

### 8. TrustEvaluator：可信度评估模块

该模块评估候选资源是否可信。

可信度评估信号包括：

```text
是否来自官方或知名组织
是否有完整 README
是否有明确 license
是否近期维护
是否有 stars / forks / issue 活动
是否有清晰安装说明
是否存在可疑脚本
```

输出示例：

```json
{
  "trust_level": "medium",
  "positive_signals": [
    "README 完整",
    "安装说明清楚"
  ],
  "negative_signals": [
    "维护者非官方",
    "最近更新时间较早"
  ]
}
```

---

### 9. RiskAnalyzer：安全风险分析模块

该模块评估候选扩展的操作风险。

风险等级可以分为：

```text
low：纯说明型 Skill，不执行脚本，不连接外部系统
medium：读取本地文件、读取仓库、运行普通辅助脚本
high：写入文件、执行 shell 命令、自动 hooks、访问 token、操作数据库或远程服务
```

输出示例：

```json
{
  "risk_level": "high",
  "risk_reasons": [
    "包含自动执行 hook",
    "需要 shell command 权限",
    "可能修改本地代码仓库"
  ],
  "safe_usage_advice": [
    "建议先在测试仓库中运行",
    "不要直接在重要项目中启用自动执行",
    "安装前人工检查脚本内容"
  ]
}
```

---

### 10. DecisionGate：决策模块

DecisionGate 是 SkillPilot 的核心模块之一。它决定系统应该推荐已有资源，还是构造自定义 Skill。

建议规则如下：

```python
if best_candidate.score >= 0.75 and best_candidate.risk_level != "high":
    decision = "recommend_existing"
elif 0.45 <= best_candidate.score < 0.75:
    decision = "recommend_with_custom_extension"
else:
    decision = "build_custom_skill"
```

具体策略：

```text
高匹配、低风险 → 推荐已有资源
中等匹配 → 推荐已有资源，同时建议自定义补充 Skill
低匹配 → 构造自定义 Skill
高风险 → 不直接推荐安装，输出安全替代方案
```

这个模块体现了 Agent 的自主决策能力，而不是简单罗列搜索结果。

---

### 11. RecommendationWriter：推荐报告生成模块

该模块生成最终推荐报告。报告内容包括：

```text
用户需求理解
推荐扩展类型
搜索范围
候选资源列表
推荐排序
每个候选的功能匹配说明
可信度和风险分析
安装或使用建议
找不到合适结果时的替代方案
```

推荐报告示例结构：

```text
需求理解：
用户希望 Claude 支持 Python 单元测试生成、测试运行和失败分析。

扩展类型判断：
该需求适合 Plugin 或 Skill + 本地命令执行能力。

推荐结果：
1. Candidate A
   匹配度：0.82
   风险：medium
   推荐理由：支持测试生成和运行，但需要本地命令权限。

2. Candidate B
   匹配度：0.71
   风险：low
   推荐理由：适合作为测试生成 Skill，但不负责运行测试。

安全提示：
建议先在测试仓库中启用，不要直接用于重要项目。
```

---

### 12. SkillBuilder：自定义 Skill 构造模块

当没有合适资源时，SkillBuilder 自动生成一个自定义 Skill 草案。

SkillBuilder 的内部流程包括：

```text
SkillSpecGenerator：生成 Skill 需求规格
SkillStructurePlanner：规划文件结构
SkillMdWriter：生成 SKILL.md
ResourceGenerator：生成模板、规则、示例
ScriptGenerator：生成辅助脚本
SafetyReviewer：检查是否包含高风险行为
PackagingAdvisor：生成安装和测试说明
```

自定义 Skill 结构示例：

```text
homework-knowledge-hint/
├── SKILL.md
├── resources/
│   ├── hint_policy.md
│   ├── output_template.md
│   └── citation_rules.md
├── scripts/
│   └── split_questions.py
└── examples/
    ├── sample_assignment.md
    └── sample_output.md
```

`SKILL.md` 内容应包括：

```text
name
description
when_to_use
workflow
constraints
output_format
safety_policy
examples
```

SkillBuilder 不应该无条件生成高风险 Skill。如果用户需求涉及账号登录、数据库写入、批量删除文件、自动执行系统命令等风险操作，系统应拒绝直接构造，转而输出安全设计建议。

---

## 九、MVP 功能范围

为了保证项目可落地，MVP 版本聚焦于以下功能：

1. 用户输入自然语言需求；
2. 系统解析需求并生成结构化 JSON；
3. 判断需求适合 Skill、Plugin、MCP 或混合方案；
4. 搜索候选资源，或读取提前缓存的候选资源；
5. 读取候选资源的 README / SKILL.md / 文档页面；
6. 抽取候选资源的功能、安装方式和风险信息；
7. 对候选资源进行评分和排序；
8. 输出前 3 个推荐结果；
9. 当没有合适候选时，生成自定义 Skill 草案；
10. 保存决策轨迹和最终报告。

MVP 阶段不强制实现真实 Claude Code 插件安装，也不自动运行第三方脚本。系统重点是搜索、评估、推荐和构造，而不是替用户执行安装。

---

## 十、进阶功能

如果时间允许，可以加入以下功能：

1. GitHub API 搜索和仓库元数据读取；
2. 对 `SKILL.md` 的专门解析和质量评估；
3. 对脚本文件进行安全扫描；
4. 支持多轮对话式需求澄清；
5. 支持本地生成 `.claude/skills/` 目录；
6. 支持将自定义 Skill 打包为 zip；
7. 支持生成测试用例；
8. 支持用户偏好记忆，如“只推荐官方来源”“不推荐高风险 hooks”；
9. 支持对已有 Skill 进行改写和优化；
10. 支持构造 Plugin 草案，但不自动安装。

---

## 十一、演示设计

课堂汇报可以准备三个演示案例。

### 案例一：推荐 Skill

用户输入：

```text
我想让 Claude 帮我检查课程论文结构，重点检查摘要、关键词、论证逻辑和引用格式。
```

预期流程：

```text
需求解析 → 判断更适合 Skill → 搜索写作 / 文档审查相关资源 → 推荐候选 Skill → 给出风险较低的使用建议
```

预期输出：

```text
推荐类型：Skill
原因：该需求主要是任务流程和格式规范，不需要连接外部系统。
推荐结果：若干写作审查类 Skill 或自定义 Skill 建议。
```

---

### 案例二：推荐 MCP 或 Plugin

用户输入：

```text
我想让 Claude 读取 GitHub Issue，并根据 Issue 自动修改代码。
```

预期流程：

```text
需求解析 → 判断需要连接 GitHub 和本地代码仓库 → 推荐 MCP 或 Plugin → 分析权限风险
```

预期输出：

```text
推荐类型：MCP 或 Plugin + MCP
原因：该任务需要访问外部 GitHub 数据，并可能修改本地代码。
风险提示：需要 GitHub 权限、本地仓库访问权限，建议在测试仓库中运行。
```

---

### 案例三：未找到合适资源，构造自定义 Skill

用户输入：

```text
我想要一个 Skill，根据课程课件给书面作业题生成知识点提示，但不能直接给答案。
```

预期流程：

```text
需求解析 → 判断适合 Skill → 搜索现有资源 → 发现没有完全匹配候选 → 进入 SkillBuilder → 生成自定义 Skill 草案
```

预期输出：

```text
homework-knowledge-hint/
├── SKILL.md
├── resources/hint_policy.md
├── resources/output_template.md
├── resources/citation_rules.md
└── examples/sample_output.md
```

这个案例最能体现 SkillPilot 的核心价值：它不仅能推荐已有扩展，还能在没有合适工具时辅助构造新的 Skill。

---

## 十二、评价方式

项目可以从以下几个维度评价：

1. **类型判断准确性**
   对若干测试需求进行人工标注，检查系统是否正确判断 Skill、Plugin、MCP 或混合方案。

2. **检索相关性**
   检查推荐结果是否与用户需求相关。

3. **候选抽取质量**
   检查系统能否从 README、SKILL.md 或文档页面中正确抽取功能、安装方式和风险信息。

4. **推荐解释质量**
   检查系统是否给出清晰推荐理由，而不是只罗列链接。

5. **风险识别能力**
   检查系统是否能识别 hooks、shell 命令、文件写入、API token、数据库访问等风险因素。

6. **自定义 Skill 质量**
   检查生成的 `SKILL.md` 是否结构完整，description 是否准确，workflow 是否可执行，约束边界是否清楚。

7. **系统闭环完整性**
   检查系统是否实现从需求输入、检索、评估、决策到推荐或构造的完整流程。

---

## 十三、技术路线

项目主体使用 Python 实现。

建议技术栈：

```text
Python
requests / httpx：网页请求
BeautifulSoup：网页解析
GitHub API：仓库搜索和元数据读取
dataclasses / pydantic：结构化数据
json：缓存和状态保存
LLM API：需求解析、候选摘要、Skill 生成
规则系统：类型判断、风险评分、决策阈值
argparse / typer：命令行交互
Markdown 文件生成：输出推荐报告和 Skill 草案
```

项目明确不使用成熟 Agent 框架。Agent 的工具注册、状态管理、模块调度、决策阈值和输出生成均由项目自行实现。

---

## 十四、项目目录结构

```text
SkillPilot/
├── main.py
├── agent/
│   ├── skillpilot_agent.py
│   ├── state.py
│   ├── planner.py
│   └── decision_gate.py
├── skills/
│   ├── requirement_parser.py
│   ├── extension_type_classifier.py
│   ├── source_planner.py
│   ├── web_search.py
│   ├── github_search.py
│   ├── repo_reader.py
│   ├── candidate_extractor.py
│   ├── capability_matcher.py
│   ├── trust_evaluator.py
│   ├── risk_analyzer.py
│   ├── recommendation_writer.py
│   └── skill_builder.py
├── builders/
│   ├── skill_spec_generator.py
│   ├── skill_md_writer.py
│   ├── resource_generator.py
│   └── safety_reviewer.py
├── data/
│   ├── source_cache.json
│   ├── candidate_cache.json
│   └── user_preferences.json
├── examples/
│   ├── example_requirements.json
│   └── demo_outputs/
├── generated_skills/
│   └── homework-knowledge-hint/
├── outputs/
│   ├── recommendation_report.md
│   └── decision_trace.json
├── README.md
└── requirements.txt
```

---

## 十五、命令行交互示例

### 1. 推荐模式

```bash
python main.py recommend "我想让 Claude 自动生成 Python 单元测试并分析失败原因"
```

预期输出：

```text
需求理解：
- 任务领域：代码测试
- 所需能力：测试生成、测试运行、失败分析
- 推荐扩展类型：Plugin 或 Skill + 本地命令执行能力

推荐结果：
1. Candidate A
   匹配度：0.82
   风险：medium
   推荐理由：支持测试生成和运行，但需要本地命令权限。

2. Candidate B
   匹配度：0.71
   风险：low
   推荐理由：适合作为测试生成 Skill，但不负责运行测试。

安全提示：
建议先在测试仓库中启用，不要直接用于重要项目。
```

### 2. 自定义 Skill 构造模式

```bash
python main.py build-skill "帮我构造一个根据课程课件给作业题提示知识点但不直接给答案的 Skill"
```

预期输出：

```text
未找到完全匹配的现成资源，开始构造自定义 Skill。

已生成：
generated_skills/homework-knowledge-hint/
├── SKILL.md
├── resources/hint_policy.md
├── resources/output_template.md
├── resources/citation_rules.md
└── examples/sample_output.md
```

---

## 十六、预期成果

最终项目成果包括：

1. Python 源代码；
2. README 使用说明；
3. 示例输入需求；
4. 推荐报告样例；
5. 自定义 Skill 生成样例；
6. 决策轨迹 JSON；
7. 课堂汇报 PPT；
8. 书面报告 PDF；
9. 如有可能，提供 GitHub 仓库链接。

---

## 十七、项目创新点

第一，SkillPilot 是一个“面向智能体扩展生态的智能体”。它不是解决普通文本问答，而是帮助用户选择、评估和构造其他智能体扩展能力。

第二，系统不仅搜索资源，还会理解需求、判断扩展类型、抽取候选信息、评估功能匹配度、分析安全风险并生成推荐报告，形成完整 Agent 工作流。

第三，系统明确区分 Skill、Plugin 和 MCP，能够根据用户需求选择不同路径，避免简单地把所有问题都归为“找插件”。

第四，系统加入安全意识，不仅考虑工具是否有用，也考虑来源可信度、权限要求、hooks、MCP server、shell 命令和文件读写等风险。

第五，系统支持 Search-or-Build 机制。当现有资源不足时，SkillPilot 可以构造自定义 Skill，从“寻找能力”升级为“生成能力”。

---

## 十八、风险与限制

第一，网页信息可能变化。解决方案是使用缓存机制，并为课堂演示准备固定样例。

第二，第三方资源安全性难以完全自动判断。解决方案是只做风险提示，不自动安装或运行不可信代码。

第三，LLM 生成的 Skill 可能存在描述过宽、触发条件不清或工作流不完整的问题。解决方案是加入 SafetyReviewer，对 description、workflow、权限边界和输出格式进行检查。

第四，真实 Claude 扩展生态可能持续变化。解决方案是将项目重点放在通用的搜索、评估和构造机制，而不是依赖某个固定市场页面。

第五，MVP 阶段不承诺自动安装 Claude 插件或 MCP server。系统优先输出推荐报告和自定义 Skill 草案，以保证安全性和可控性。

---

## 十九、总结

SkillPilot 是一个面向 Claude 扩展生态的轻量级智能体。它能够根据用户自然语言需求，判断用户更适合使用 Skill、Plugin、MCP 还是混合方案，并自动检索相关资源，评估候选资源的功能匹配度、可信度和安全风险。当没有合适现成资源时，SkillPilot 可以在安全边界内生成自定义 Skill 草案。

相比普通搜索工具，SkillPilot 的价值在于它不仅回答“有哪些工具”，还回答“我应该用哪种扩展形式”“哪个候选更适合我”“安装前有什么风险”“没有合适工具时能否构造一个”。因此，该项目具有明确的问题边界、完整的系统结构、较强的实用性和较好的课堂展示价值。
