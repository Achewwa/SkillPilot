# SkillPilot 推荐报告

## 用户需求理解

阅读pdf的插件

## 扩展类型判断

用户明确提到插件，优先规划 Claude Code Plugin 方向，同时保留后续安全评估。

## 搜索计划

- 目标类型：plugin
- 搜索源：web_search, github_repository_search
1. [github] PDF reading document parsing Claude Code plugin GitHub（目的：Find Claude Code plugin repositories.）
2. [web] PDF reading document parsing "Claude Code plugin"（目的：Find plugin documentation or examples.）
3. [github] PDF reading document parsing "claude-code" plugin（目的：Find repositories using Claude Code plugin naming.）
4. [web] 阅读pdf的插件 Claude Code plugin（目的：Search the original requirement against plugin terms.）

## 搜索结果

1. [github/no_results] PDF reading document parsing Claude Code plugin GitHub
   - 查询：PDF reading document parsing Claude Code plugin GitHub
   - 说明：GitHub search returned no repositories.
2. [web/no_results] PDF reading document parsing "Claude Code plugin"
   - 查询：PDF reading document parsing "Claude Code plugin"
   - 说明：Web search returned no visible results.
3. [github/no_results] PDF reading document parsing "claude-code" plugin
   - 查询：PDF reading document parsing "claude-code" plugin
   - 说明：GitHub search returned no repositories.
4. [web/success] ZSHYC/pdf-master: 全能型 PDF 处理 Claude Code 插件 - GitHub
   - URL：https://github.com/ZSHYC/pdf-master
   - 查询：阅读pdf的插件 Claude Code plugin
   - 说明：PDF -Master 🚀 全能型 PDF 处理 Claude Code 插件 一个插件，覆盖所有 PDF 场景 — 解析、编辑、转换、AI 增强、OCR、安全 🌐 官网 • 功能特性 • 快速开始 • 使用指南 • AI 配置 • 开发
5. [web/success] PDF-Master - 全能型 PDF 处理 Claude Code 插件
   - URL：https://zshyc.github.io/pdf-master/
   - 查询：阅读pdf的插件 Claude Code plugin
   - 说明：全能型 PDF 处理 Claude Code 插件 一个插件，覆盖所有 PDF 场景 解析 · 编辑 · 转换 · AI 增强 · OCR · 安全
6. [web/success] 一行命令，让你的 Code Agent 会读PDF - 知乎
   - URL：https://zhuanlan.zhihu.com/p/2022009123592480470
   - 查询：阅读pdf的插件 Claude Code plugin
   - 说明：Claude Code、Cursor、Kimi Code、Codex、Cline——现在大家写代码越来越依赖 Code Agent。但大模型有一个短板： 读不了 PDF 。你丢给它一个 PDF 文件路径，它只会告诉你&#34;这是个二进制文件，我读不了&#34;。论…

## 候选资源与评分

暂无足够匹配的候选资源。

## 决策结果

- 决策：build_custom_skill
- 原因：没有足够匹配的候选资源，进入自定义 Skill 草案流程。

## 安全提示

本报告由占位骨架生成，不会自动安装、运行或授权第三方扩展。后续实现应继续保留人工确认和风险提示。
