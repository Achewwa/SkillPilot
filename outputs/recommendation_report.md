# SkillPilot 推荐报告

## 用户需求理解

自动管理github

## 扩展类型判断

需求涉及外部服务或仓库访问，MCP 更适合作为工具连接层。

## 搜索计划

- 目标类型：mcp
- 搜索源：web_search, github_repository_search
1. [github] GitHub issue reader codebase access MCP server GitHub（目的：Find MCP server repositories.）
2. [web] GitHub issue reader codebase access "Model Context Protocol" server（目的：Find MCP documentation and directories.）
3. [github] GitHub issue reader codebase access "mcp server"（目的：Find repositories using common MCP wording.）
4. [web] 自动管理github Claude MCP server（目的：Search the original requirement against MCP terms.）

## 搜索结果

1. [github/skipped] GitHub issue reader codebase access MCP server GitHub
   - 查询：GitHub issue reader codebase access MCP server GitHub
   - 说明：Network search is disabled. Set SKILLPILOT_ENABLE_NETWORK_SEARCH=1 to execute this query.
2. [web/skipped] GitHub issue reader codebase access "Model Context Protocol" server
   - 查询：GitHub issue reader codebase access "Model Context Protocol" server
   - 说明：Network search is disabled. Set SKILLPILOT_ENABLE_NETWORK_SEARCH=1 to execute this query.
3. [github/skipped] GitHub issue reader codebase access "mcp server"
   - 查询：GitHub issue reader codebase access "mcp server"
   - 说明：Network search is disabled. Set SKILLPILOT_ENABLE_NETWORK_SEARCH=1 to execute this query.
4. [web/skipped] 自动管理github Claude MCP server
   - 查询：自动管理github Claude MCP server
   - 说明：Network search is disabled. Set SKILLPILOT_ENABLE_NETWORK_SEARCH=1 to execute this query.

## 候选资源与评分

1. github-issue-workflow-mcp
   - 类型：mcp
   - 匹配度：0.95
   - 风险等级：high
   - 说明：占位评分：基于能力关键词重合、扩展类型一致性和权限风险生成。
   - 来源：cache://mcp/github-issues
2. paper-review-skill-template
   - 类型：skill
   - 匹配度：0.0
   - 风险等级：low
   - 说明：占位评分：基于能力关键词重合、扩展类型一致性和权限风险生成。
   - 来源：cache://skills/paper-review
3. python-test-helper-skill
   - 类型：skill
   - 匹配度：0.0
   - 风险等级：low
   - 说明：占位评分：基于能力关键词重合、扩展类型一致性和权限风险生成。
   - 来源：cache://skills/python-tests

## 决策结果

- 决策：recommend_with_custom_extension
- 原因：候选资源有一定相关性，但仍建议用自定义 Skill 补齐缺口。

## 安全提示

本报告由占位骨架生成，不会自动安装、运行或授权第三方扩展。后续实现应继续保留人工确认和风险提示。
