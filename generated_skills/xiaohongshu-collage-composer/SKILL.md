# Xiaohongshu Collage Composer

## Description

将 5-9 张用户照片合成为 3:4 竖向、拼贴混搭风格的小红书组图成品 PNG。自动决定错落叠放、旋转、内置纸质/手绘装饰素材，并基于输入图片自动提取主色生成统一艺术调性。不添加任何文字。

## When To Use

- The user request is related to image_composition.
- The user asks for a repeatable workflow rather than a one-off answer.
- The task benefits from clear constraints, examples, or output templates.

## Workflow

1. 步骤 1 输入校验：确认用户提供 5-9 张本地图片路径（支持 JPG/PNG）。少于 5 张或多于 9 张时，提示用户调整数量并说明 Skill 的设计范围；非本地路径或无法读取时直接报错退出。
2. 步骤 2 读取与归一：使用 Pillow 打开所有图片，按 EXIF 方向纠正，统一缩放至最长边不超过 1200px 以控制内存与速度。
3. 步骤 3 主色提取：对所有输入图片做小尺寸缩略并合并像素，使用 KMeans（k=5）聚类提取主色板，挑选 1 个偏暖中性色作为画布底色、1 个作为装饰强调色、并生成 2-3 个胶带色（饱和度降低、明度统一），保证整体调性一致。
4. 步骤 4 布局生成：根据图片数量从 resources/layout_presets.json 中选择对应 3:4 画布的拼贴模板（5/6/7/8/9 张各一套），模板定义每张图的中心点、相对尺寸、基础旋转范围和层叠顺序；每张图在模板范围内随机微调位置（±20px）与旋转（±8°）以呈现自然错落感。
5. 步骤 5 装饰渲染：在 resources/decorations/ 中按需选取纸纹底图作为画布背景层（叠加步骤 3 的底色），从胶带 PNG 中为每张图片随机选择 1-2 段贴在边角，从手绘元素中随机添加 2-4 个点缀，所有装饰使用步骤 3 的色板做色相微调以融入主色。
6. 步骤 6 合成与输出：在 1242×1656 画布上按层叠顺序合成：背景纸纹 → 装饰底层（色块/手绘）→ 图片（带轻微白边与阴影）→ 胶带与上层手绘。保存为 PNG 到用户指定路径或默认 ./output/collage_<timestamp>.png，并向用户报告输出路径、所用布局编号与提取色板。
7. 步骤 7 异常处理：scripts 调用失败、依赖缺失（Pillow/numpy/scikit-learn）、内存不足、素材缺失等情况下，给出明确错误信息与修复建议，不静默回退。

## Constraints

- 仅处理用户本地路径下的图片文件，不下载远程 URL、不访问网络。
- 输入数量严格限定 5-9 张；越界时不静默裁剪或补全，直接提示用户调整。
- 输出固定为 3:4 竖向 PNG，分辨率基准 1242×1656；不输出 1:1、9:16 或其他比例。
- 不向组图中添加任何文字、日期、标题或字体渲染；如用户要求加文字，应明确告知本 Skill 不支持并建议在其他工具中后期添加。
- 装饰素材仅使用 resources/decorations/ 内置文件，不调用在线素材库、不生成 AI 图像。
- 保留输入图片原始内容，不做美颜、换脸、风格迁移等会改变图像语义的处理；仅允许轻微缩放、旋转、白边、阴影和整体亮度/饱和度的统一微调（≤10%）。
- 不读取或修改输入图片所在目录之外的任何文件；输出目录在调用时显式指定，默认 ./output/。
- 不保留或上传用户图片到任何外部位置；处理过程仅在本地内存与指定输出路径完成。
- 随机化使用可重置种子（可通过参数 seed 传入），保证同输入可复现结果。

## Output Format

向用户返回一段简洁的结构化文本，包含：① 输出文件绝对路径；② 使用的布局预设编号（如 layout_7_a）；③ 从输入图片提取的主色板（HEX 列表）；④ 随机种子；⑤ 如有警告（例如某张图过窄被裁剪）逐条列出。不返回 base64 图片数据，不返回完整 JSON 元数据，除非用户显式要求。

## Resources

- `resources/layout_presets.json`: 为 5/6/7/8/9 张输入分别预定义 3:4 画布上的拼贴布局模板（中心点、相对尺寸、旋转范围、层叠顺序）。
- `resources/decorations/papers/`: 内置牛皮纸、米白纸、轻噪点纸纹背景素材，作为画布底层。
- `resources/decorations/tapes/`: 胶带 PNG 素材，用于贴在照片边角，呈现拼贴感。
- `resources/decorations/elements/`: 手绘点缀元素 PNG，用于装饰拼贴空白处。
- `resources/style_guide.md`: 向 Claude 说明拼贴混搭风的视觉准则与素材使用策略。

## Examples

- `examples/example_7_photos.md`: 展示 7 张旅行照片输入下的完整调用流程与输出结果说明。
- `examples/example_minimal_5.md`: 展示最少 5 张输入下的简单调用示例。
- `examples/example_error_too_few.md`: 展示输入少于 5 张时 Skill 的拒绝与提示行为。
