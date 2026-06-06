# SkillPilot 推荐报告

## 用户需求理解

维护github仓库的能力

## 扩展类型判断

LLM 类型判断：该需求的核心是通过 GitHub API 与外部平台进行持续交互，涉及 issue 追踪、PR 管理、分支操作等均属于外部服务调用而非本地代码工作流。MCP Server 专为将外部服务能力暴露给 Claude 而设计，GitHub 官方也提供了成熟的 MCP 实现。虽然 requires_codebase_access 和 requires_command_execution 为 true，但这里的代码访问主要指通过 API 读写仓库内容，而非本地 IDE 环境中的代码编辑；命令执行需求也更多体现在 GitHub API 调用语义上。Claude Code Plugin 更适合本地开发环境中的代码生成/修改工作流，不匹配本需求以 GitHub 平台为中心的外部服务依赖特征。

## 搜索计划

- 目标类型：mcp
- 需求领域：github_repository_management
- 需求能力：github_repo_maintenance、github_issue_tracking、github_pull_request_management、github_branch_management、code_review、github_api_access
- 搜索源：
  - official_mcp_registry：Official MCP Registry (official_registry_api, official)
    - 入口：https://registry.modelcontextprotocol.io/v0.1/servers
    - 读取方式：generic_mcp_registry_reader；搜索方式：mcp_registry_api_searcher
  - glama_mcp：Glama MCP Registry (community_registry_api, community)
    - 入口：https://glama.ai/api/mcp/v1/servers
    - 读取方式：glama_api_reader；搜索方式：glama_api_searcher
  - smithery_mcp：Smithery MCP Registry (commercial_hosted_registry_api, commercial)
    - 入口：https://api.smithery.ai/servers
    - 读取方式：smithery_api_reader；搜索方式：smithery_api_searcher
1. [source] github repository management MCP server（目的：Find official or canonical GitHub MCP server entries covering repo maintenance, issue tracking, and PR management，源：official_mcp_registry）
2. [source] github pull request code review branch MCP（目的：Locate MCP servers specifically exposing GitHub PR lifecycle, code review, and branch operations via GitHub API，源：official_mcp_registry）
3. [source] github MCP server repository issue pull request branch management Claude（目的：Retrieve enriched quality signals, license info, and tool attributes for GitHub MCP candidates from community registry，源：glama_mcp）
4. [source] github-mcp-server code review API access Claude skill（目的：Cross-check community adoption and attribute completeness for github-mcp-server type packages，源：glama_mcp）
5. [source] github repository MCP hosted remote API server verified（目的：Identify hosted and verified GitHub MCP deployments suitable for medium-risk external service integration without local setup，源：smithery_mcp）

## 搜索结果

1. [source/official_mcp_registry/no_results] github repository management MCP server
   - 查询：github repository management MCP server
   - 说明：Registry API contained no matching entries.
2. [github/official_mcp_registry/success] ai.aliengiraffe/spotdb
   - URL：https://github.com/aliengiraffe/spotdb
   - 查询：github pull request code review branch MCP
   - 说明：Ephemeral data sandbox for AI workflows with guardrails and security
3. [github/glama_mcp/success] ssh-mcp
   - URL：https://github.com/SC-ML-cmd/ssh-mcp
   - 查询：github MCP server repository issue pull request branch management Claude
   - 说明：Enables SSH interactive session management through MCP, supporting commands, menus, and session lifecycle operations.
4. [github/glama_mcp/success] rustfs-mcp
   - URL：https://github.com/stackblaze/rustfs-mcp
   - 查询：github MCP server repository issue pull request branch management Claude
   - 说明：A per-add-on RustFS (S3) object-storage admin MCP for the kubero chat, enabling management of S3-compatible buckets and objects through natural language.
5. [github/glama_mcp/success] SIN-Code-Frontend-Design-Skill
   - URL：https://github.com/OpenSIN-Code/SIN-Code-Frontend-Design-Skill
   - 查询：github-mcp-server code review API access Claude skill
   - 说明：Provides 8 MCP tools for frontend design: load design system, generate components, scaffold pages, review consistency, extract tokens, check WCAG 2.2 AA, test responsiveness, and export to Figma.
6. [github/glama_mcp/success] Kairos
   - URL：https://github.com/gerchowl/kairos
   - 查询：github-mcp-server code review API access Claude skill
   - 说明：when2meet-style scheduling polls — self-hostable, reverse-proxy-auth friendly, agent-first API (OpenAPI + llms.txt + MCP).
7. [source/smithery_mcp/success] Gmail
   - URL：https://smithery.ai/servers/gmail
   - 查询：github repository MCP hosted remote API server verified
   - 说明：Manage Gmail end-to-end: send, draft, reply, forward, and bulk-modify or delete messages and threads. Organize your inbox with labels, archiving, and trashing, and retrieve messages, attachments, and profile details on demand. Access and search contacts to autofill recipients and keep people data in sync.
8. [source/smithery_mcp/success] Exa Search
   - URL：https://exa.ai
   - 查询：github repository MCP hosted remote API server verified
   - 说明：Fast, intelligent web search and web crawling. Get fresh information about libraries, APIs, and SDKs.
9. [source/smithery_mcp/success] Mesh MCP
   - URL：https://me.sh
   - 查询：github repository MCP hosted remote API server verified
   - 说明：Access your network seamlessly with a simple and efficient server. Leverage a variety of tools to enhance your applications and workflows. Start integrating with your existing systems effortlessly.
10. [github/smithery_mcp/success] Context7
   - URL：https://github.com/upstash/context7#readme
   - 查询：github repository MCP hosted remote API server verified
   - 说明：Fetch up-to-date, version-specific documentation and code examples directly into your prompts. Enhance your coding experience by eliminating outdated information and hallucinated APIs. Simply add `use context7` to your questions for accurate and relevant answers.
11. [source/smithery_mcp/success] Jina AI
   - URL：https://jina.ai
   - 查询：github repository MCP hosted remote API server verified
   - 说明：AI-powered search and retrieval platform. Search the web, read page content, extract structured data, and ground AI responses.

## 页面与仓库读取

1. [source/skipped] github repository management MCP server
   - 说明：Only successful search results with URLs are read.
2. [github/success] aliengiraffe/spotdb
   - URL：https://github.com/aliengiraffe/spotdb
   - 说明：Give your agents a secure, containerized SQL sandbox with MCP or API access enabled with DuckDB. No infra required, quick spin-up cycle. Push any CSV — query, analyze, and move on.
3. [github/success] SC-ML-cmd/ssh-mcp
   - URL：https://github.com/SC-ML-cmd/ssh-mcp
   - 说明：ssh-mcp 支持连接远程节点，支持维持会话
4. [github/success] stackblaze/rustfs-mcp
   - URL：https://github.com/stackblaze/rustfs-mcp
   - 说明：Per-add-on RustFS (S3) object-storage admin MCP for the kubero chat
5. [github/success] OpenSIN-Code/SIN-Code-Frontend-Design-Skill
   - URL：https://github.com/OpenSIN-Code/SIN-Code-Frontend-Design-Skill
   - 说明：OpenSIN-Code Skill: SOTA frontend design system + philosophy (Anthropic-compatible) with v0-pool integration, MCP tools, WCAG a11y checks
6. [github/success] gerchowl/kairos
   - URL：https://github.com/gerchowl/kairos
   - 说明：when2meet-style scheduling polls — self-hostable, reverse-proxy-auth friendly, agent-first API (OpenAPI + llms.txt + MCP)
7. [source/success] Gmail - MCP | Smithery
   - URL：https://smithery.ai/servers/gmail
   - 说明：Manage Gmail end-to-end: send, draft, reply, forward, and bulk-modify or delete messages and threads. Organize your inbox with labels, archiving, and trashing, and retrieve messages, attachments, and profile details on demand. Access and search contacts to autofill recipients and keep people data in sync.
8. [source/success] Exa | Web Search API, AI Search Engine, & Website Crawler
   - URL：https://exa.ai
   - 说明：Real-time AI search engine with a powerful web search API, web crawling API, SERP API, and deep research tools. Search and extract structured content from websites and live data.
9. [source/success] Mesh - Be more thoughtful with the people in your network.
   - URL：https://me.sh
   - 说明：Mesh is a beautiful rolodex and CRM for iPhone, Mac, Windows, and web, built automatically to help you manage your personal and professional relationships.
10. [github/success] upstash/context7
   - URL：https://github.com/upstash/context7
   - 说明：Context7 Platform -- Up-to-date code documentation for LLMs and AI code editors
11. [source/success] Jina AI - Your Search Foundation, Supercharged.
   - URL：https://jina.ai
   - 说明：Best-in-class embeddings, rerankers, web reader, deepsearch, small language models. Search AI for multilingual and multimodal data.

## 失败处理

- 搜索未完成：[source/official_mcp_registry/no_results] 查询 `github repository management MCP server`；原因：Registry API contained no matching entries.
- 读取未完成：[source/official_mcp_registry/skipped] `github repository management MCP server`；原因：Only successful search results with URLs are read.

## 候选资源与评分

1. Context7 MCP (@upstash/context7-mcp)
   - 类型：mcp
   - 描述：Context7 是一个文档检索平台，通过 MCP 服务或 CLI 工具为 LLM 提供最新的第三方库文档和代码示例，帮助 AI 编码助手避免使用过时 API 或幻觉接口。
   - 总分：0.52
   - 分项：能力 0.04，类型 1.0，文档 0.92，安全 0.82
   - 匹配能力：无
   - 缺失能力：github_repo_maintenance、github_issue_tracking、github_pull_request_management、github_branch_management、code_review、github_api_access
   - 风险等级：low
   - 说明：LLM 结构化评分：依据原文 README，Context7 是一个文档检索 MCP 工具，其核心功能为 resolve-library-id 和 query-docs，专注于为 LLM 注入最新的第三方库文档（如 Next.js、Supabase、MongoDB 等）。与用户需求'维护 GitHub 仓库'（涵盖仓库维护、Issue 追踪、PR 管理、分支管理、代码审查、GitHub API 访问）完全不匹配。原文中无任何 GitHub 操作能力的证据，6 项目标能力全部缺失，capability_score 极低（0.04，非零仅因理论上可查询 GitHub 相关库文档）。文档质量高（0.92），有完整安装指南、多语言文档、API 参考及故障排查文档。安全评分良好（0.82），MIT 许可、56k+ Stars、活跃维护，轻微扣分来自社区内容质量免责声明。综合判断：此候选与 GitHub 仓库管理需求严重不符，不应作为满足该需求的候选推荐。
   - 来源：https://github.com/upstash/context7
   - 安装线索：npx ctx7 setup（自动模式）或手动配置 MCP 客户端指向 https://mcp.context7.com/mcp，可通过 CONTEXT7_API_KEY 头部传递 API Key
   - 风险原因：
     - 工具功能与需求完全不匹配，集成后无法实现任何 GitHub 仓库管理目标
     - README 免责声明指出社区贡献的库文档质量无法完全保证，存在内容准确性风险（与本需求无关但需知晓）
2. stackblaze/rustfs-mcp
   - 类型：mcp
   - 描述：Per-add-on RustFS (S3) object-storage admin MCP for the kubero chat
   - 总分：0.48
   - 分项：能力 0.0，类型 1.0，文档 0.65，安全 1.0
   - 匹配能力：无
   - 缺失能力：code_review、github_api_access、github_branch_management、github_issue_tracking、github_pull_request_management、github_repo_maintenance
   - 风险等级：low
   - 说明：LLM 评分未完成，使用本地兜底规则。
   - 来源：https://github.com/stackblaze/rustfs-mcp
   - 风险原因：
     - 未发现明显的高危权限或敏感依赖。
   - 证据：
     - stackblaze/rustfs-mcp
     - Description: Per-add-on RustFS (S3) object-storage admin MCP for the kubero chat
     - Last updated: 2026-06-05T15:34:03Z
3. aliengiraffe/spotdb
   - 类型：mcp
   - 描述：一个基于 DuckDB 的轻量级临时数据沙箱，支持 MCP 与 REST API 接入，面向 AI 工作流的数据查询与分析场景，与 GitHub 仓库管理完全无关。
   - 总分：0.42
   - 分项：能力 0.02，类型 1.0，文档 0.55，安全 0.75
   - 匹配能力：无
   - 缺失能力：github_repo_maintenance、github_issue_tracking、github_pull_request_management、github_branch_management、code_review、github_api_access
   - 风险等级：low
   - 说明：LLM 结构化评分：本候选与需求「维护 GitHub 仓库的能力」不存在任何功能交集。原文证据表明 SpotDB 是一个 DuckDB 驱动的 SQL 数据沙箱，核心能力为 CSV 数据上传、SQL 查询与 MCP 数据访问，与 GitHub API 操作、Issue/PR 管理、分支管理及代码审查均无关联。6 项目标能力全部缺失，capability_score 评定为 0.02（非零仅因其实现了 MCP 协议这一通用接口标准，但协议本身不等于 GitHub 能力）。该候选系误命中，建议排除。
   - 来源：https://github.com/aliengiraffe/spotdb
   - 安装线索：brew tap aliengiraffe/spaceship && brew install spotdb；MCP 接入：claude mcp add spotdb -s user -- npx -y mcp-remote http://localhost:8081/stream
   - 风险原因：
     - 该工具本身安全设计合理（MIT 许可、数据隔离、守卫机制），但与需求完全不匹配，引入此工具无法满足 GitHub 管理需求，存在选型错误的风险。

## 决策结果

- 决策：recommend_with_custom_extension
- 原因：LLM 决策解释：三个候选资源（Context7 MCP、rustfs-mcp、spotdb）的匹配分数均低于 0.55（分别为 0.52、0.48、0.42），且没有任何一个候选项命中所需能力，六项核心能力（github_repo_maintenance、github_issue_tracking、github_pull_request_management、github_branch_management、code_review、github_api_access）在所有候选中均完全缺失。现有资源与 GitHub 仓库管理需求存在根本性的功能错位，直接采用任何候选项均无法实现目标。建议以现有候选资源作为参考背景，另行构建自定义 Skill 以完整覆盖上述缺失的 GitHub 操作能力。

## 使用建议与安全替代

建议把现有候选作为参考资料，同时使用生成的自定义 Skill 补齐缺失能力。

## 安全提示

SkillPilot 不会自动安装、运行或授权第三方扩展。涉及命令执行、写入、token、数据库或远程写操作的候选，必须先人工审查。
