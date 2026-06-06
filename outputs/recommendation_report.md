# SkillPilot 推荐报告

## 用户需求理解

将多张图片拼成有艺术感的组图

## 扩展类型判断

需求主要是规范 Claude 如何完成任务，适合先以 Skill 表达。

## 搜索计划

- 目标类型：skill
- 需求领域：image_composition
- 需求能力：image_collage_creation、multi_image_layout、artistic_image_composition、image_processing
- 搜索源：
  - anthropic_skills_repo：Anthropic Skills Repository (official_github_marketplace_repo, official)
    - 入口：https://api.github.com/repos/anthropics/skills/contents/skills
    - 读取方式：github_marketplace_manifest_reader；搜索方式：marketplace_json_searcher
  - anthropic_agent_skills_docs：Anthropic Agent Skills Docs (official_docs, official)
    - 入口：https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview.md
    - 读取方式：docs_markdown_reader；搜索方式：docs_keyword_searcher
  - anthropic_skills_cookbook：Anthropic Skills Cookbook (official_example_repo, official)
    - 入口：https://api.github.com/repos/anthropics/anthropic-cookbook/contents/skills
    - 读取方式：github_repo_tree_reader；搜索方式：github_contents_searcher
  - skillsmp_directory：SkillsMP Skills Marketplace (community_skill_directory_api, community)
    - 入口：https://skillsmp.com/api/v1/skills/search
    - 读取方式：skillsmp_api_reader；搜索方式：skillsmp_api_searcher
1. [source] image collage creation multi image layout artistic image composition Claude Skill SKILL.md Anthropic Skills Repository ".claude-plugin" marketplace.json（目的：Search inside the curated source `anthropic_skills_repo`.，源：anthropic_skills_repo）
2. [source] image collage creation multi image layout artistic image composition Claude Skill SKILL.md Anthropic Agent Skills Docs official docs 将多张图片拼成有艺术感的组图（目的：Search inside the curated source `anthropic_agent_skills_docs`.，源：anthropic_agent_skills_docs）
3. [source] image collage creation multi image layout artistic image composition Claude Skill SKILL.md Anthropic Skills Cookbook examples README 将多张图片拼成有艺术感的组图（目的：Search inside the curated source `anthropic_skills_cookbook`.，源：anthropic_skills_cookbook）
4. [source] image collage creation multi image layout artistic image composition 将多张图片拼成有艺术感的组图（目的：Search inside the curated source `skillsmp_directory`.，源：skillsmp_directory）

## 搜索结果

暂无搜索结果。

## 页面与仓库读取

暂无页面或仓库读取结果。

## 失败处理

本次搜索和读取阶段未记录失败项。

## 候选资源与评分

暂无足够匹配的候选资源。

## 决策结果

- 决策：build_custom_skill
- 原因：用户显式请求构造 Skill，直接进入 SkillBuilder Agent。

## 使用建议与安全替代

未找到足够证据支撑现成推荐时，应明确说明搜索不足，并优先生成可控的自定义 Skill 草案。

## SkillBuilder 构造过程

- 生成目录：`/home/achewwa/Projects/SkillPilot/generated_skills/xiaohongshu-collage-composer`
- 生成文件：
  - `/home/achewwa/Projects/SkillPilot/generated_skills/xiaohongshu-collage-composer/SKILL.md`
  - `/home/achewwa/Projects/SkillPilot/generated_skills/xiaohongshu-collage-composer/resources/layout_presets.json`
  - `/home/achewwa/Projects/SkillPilot/generated_skills/xiaohongshu-collage-composer/resources/decorations/papers`
  - `/home/achewwa/Projects/SkillPilot/generated_skills/xiaohongshu-collage-composer/resources/decorations/tapes`
  - `/home/achewwa/Projects/SkillPilot/generated_skills/xiaohongshu-collage-composer/resources/decorations/elements`
  - `/home/achewwa/Projects/SkillPilot/generated_skills/xiaohongshu-collage-composer/resources/style_guide.md`
  - `/home/achewwa/Projects/SkillPilot/generated_skills/xiaohongshu-collage-composer/examples/example_7_photos.md`
  - `/home/achewwa/Projects/SkillPilot/generated_skills/xiaohongshu-collage-composer/examples/example_minimal_5.md`
  - `/home/achewwa/Projects/SkillPilot/generated_skills/xiaohongshu-collage-composer/examples/example_error_too_few.md`
  - `/home/achewwa/Projects/SkillPilot/generated_skills/xiaohongshu-collage-composer/README.md`
  - `/home/achewwa/Projects/SkillPilot/generated_skills/xiaohongshu-collage-composer/scripts/README.md`
- 规格摘要：将 5-9 张用户照片合成为 3:4 竖向、拼贴混搭风格的小红书组图成品 PNG。自动决定错落叠放、旋转、内置纸质/手绘装饰素材，并基于输入图片自动提取主色生成统一艺术调性。不添加任何文字。
- 安全审查：medium
  - 规格要求生成辅助脚本，必须在人工审查后才可启用。
- 安全替代方案：
  - 保持 Skill 为说明、模板和检查清单，不自动连接外部系统。
  - 需要外部工具时，只给出人工配置建议。
- Builder 状态：complete
- Builder 反思：达到最大澄清轮数，使用已收集信息保守生成 Skill。
- Skill 名称：Xiaohongshu Collage Composer
- Skill slug：xiaohongshu-collage-composer
- 澄清问答：
  - 第 1 轮：第 1 轮已收集字段：q1_use_scenario、q2_artistic_style、q3_output_format。
    - 问：这个图片组图工具主要用在什么场景？
      - 选项：q1_opt_social. 社交媒体分享；q1_opt_album. 个人相册纪念；q1_opt_design. 专业设计素材
      - 答：1
    - 问："艺术感"具体倾向哪种风格？
      - 选项：q2_opt_minimal. 极简留白风；q2_opt_collage. 拼贴混搭风；q2_opt_filmic. 胶片复古风
      - 答：2
    - 问：希望 Skill 最终交付什么形式的产物？
      - 选项：q3_opt_image. 直接生成成品图片；q3_opt_plan. 输出排版方案与参数；q3_opt_template. 生成可编辑模板
      - 答：1
  - 第 2 轮：第 2 轮已收集字段：q2_1_input_scale、q2_2_platform_size、q2_3_collage_control。
    - 问：用户单次会提供多少张图片，Skill 需要支持的输入规模是怎样的？
      - 选项：q2_1_opt_small. 少量精选（2-4 张）；q2_1_opt_medium. 中等数量（5-9 张）；q2_1_opt_flexible. 灵活可变（2-20 张以上）
      - 答：2
    - 问：成品图片需要适配哪些社交平台的尺寸规格？
      - 选项：q2_2_opt_xiaohongshu. 小红书优先（3:4 竖图）；q2_2_opt_instagram. Instagram 优先（1:1 方图或九宫格）；q2_2_opt_multi. 多平台一次性导出
      - 答：1
    - 问：拼贴混搭的艺术细节（旋转、叠放、装饰元素）希望由 Skill 自动决定还是用户可控？
      - 选项：q2_3_opt_auto. 全自动一键出图；q2_3_opt_preset. 提供风格预设可选；q2_3_opt_param. 开放参数精细调整
      - 答：1
  - 第 3 轮：第 3 轮已收集字段：q3_1_decoration_source、q3_2_color_strategy、q3_3_text_caption。
    - 问：拼贴风格中的装饰元素（手绘涂鸦、纸质纹理、贴纸等）应该如何获取？
      - 选项：q3_1_opt_bundled. 内置素材包随 Skill 分发；q3_1_opt_procedural. 程序化生成装饰；q3_1_opt_hybrid. 内置基础素材 + 程序化点缀
      - 答：1
    - 问：3:4 竖向拼贴组图的整体配色应如何确定，以保证"艺术感"统一？
      - 选项：q3_2_opt_extract. 从输入图片自动提取主色；q3_2_opt_preset_palette. 使用内置艺术色板；q3_2_opt_mono_paper. 统一米白/牛皮纸底色
      - 答：1
    - 问：组图中是否需要 Skill 自动添加文字（标题、日期、手写体短句等）？
      - 选项：q3_3_opt_none. 不加任何文字；q3_3_opt_auto_caption. 自动添加点缀文字；q3_3_opt_user_text. 用户传入文字内容
      - 答：1

## 安全提示

SkillPilot 不会自动安装、运行或授权第三方扩展。涉及命令执行、写入、token、数据库或远程写操作的候选，必须先人工审查。
