---
name: nce1-lesson-html
description: "在 nce1 项目中根据本地教材扫描页与语法 PDF，快速制作新概念英语第一册第 45–144 课的 HTML 学习页。文字优先，保留课文、词汇、练习、答案及后续补图位置；偶数课仅在容易时裁图。适用于批量生成课文网页、继续下一课、给已生成课文补图。"
---

# NCE1 文字优先课文页

在已有 `html/assets/lesson.css`、`lesson.js`、`img/`、`pdf/` 的 nce1 仓库中工作。默认仓库是 `/Users/hiscat/IdeaProjects/nce1`，用户提供其他路径时使用该路径。此 skill 制作第一册网页，不套用第三册逐句 IPA 分析格式。

## 本项目的默认规则

- 只制作用户指定的课号范围。若只是要求建立模板/验证样例，不自动扩展为 100 课。
- **奇数课先不裁图、不调用生图服务**。完整保留英文、中文译文、说话人、课前问题、生词、注释、练习及答案。
- **偶数课可快速裁取原书配图**：每课配图操作默认预算 2 分钟；需要复杂定位、反复修图或等待时立即保留 text，标记 pending 后继续。此预算仅针对配图，不削减正文与题目核对。
- “不截图”指不制作正文插图；为读清扫描 PDF 而临时渲染页面不受此限制。
- 无图时仍保留全部数字、物品名称、动作、数量、方位、否定与对比信息。若题目依赖图片，转成等价文字提示后保留作答框，不能直接丢题，也不要用完整答案替代待答提示。
- 区分 `scene`（对话情节）、`item`（物品/数量/方位）、`action`（动作/能力练习）。插图描述应来自文字语义，不凭旧图猜情节。
- 将未来生图的人物设定放在每课 `characters` 中，场景引用角色 ID。同一课重复人物保持脸型、发型和服装一致，不要求跨课相同。不回改此前已完成的彩色课文。
- 保留原始扫描页。未来只在完成替换、确认无引用后清理被替代的裁图，不删除 `img/` 中的教材源图。

## 生成流程

1. 检查 Git 状态、相邻课及共享资产。保留用户的未提交内容。读取 [数据格式](references/content-format.md)。把本 skill 目录记为 `SKILL_DIR`，用绝对路径调用脚本。
2. 用库存脚本一次查出本批扫描文件、练习答案候选及准确 PDF 页码：

   ```sh
   python3 "$SKILL_DIR/scripts/source_inventory.py" --repo /path/to/nce1 --from 47 --to 60
   ```

   库存脚本需要 `pypdf`，渲染脚本仅用 Python 标准库。库存不是转录结果；**不能把空壳或标题清单算作完成课文**。
3. 看教材两页和练习页，完整转录到 `lessons/lesson-NNN.json`。先记每组题数和示例数，再填具体内容。阅读题/教材无答案的题标注 `suggested`；习题册答案读对应 `img/key-*.jpg`。不要凭记忆拼教材。
4. 根据 PDF 书签页码渲染本课语法练习，检查跨页续题。语法答案位于 Answer Key 部分，需实际定位并核对，不能从练习页码推算。示例 45 课练习 PDF 141–143 页、答案 477–478 页；46 课练习 144–145 页、答案 478–479 页。PDF 页码与书上印刷页码不同。

   ```sh
   mkdir -p tmp/lesson-html
   pdftoppm -f 141 -l 143 -scale-to 1800 -png 'pdf/新概念英语语法练习1_按课程索引.pdf' tmp/lesson-html/grammar
   ```

5. 奇数课为连续对话分组设置稳定的 `scene-01` 等图片 slot；偶数课保留每项文字提示，并可做一次快速裁图。**先读取原图像素尺寸**，工具预览可能缩小，坐标要换算到原图。图片描述、原图路径、尺寸、裁图坐标与 pending 原因记录在同一份 JSON，不维护另一份会漂移的图片清单。
6. 核对课文/练习/语法三部分、词汇、示例、所有小题及答案来源，最后设置 `status: verified`。可参考仓库中已验证的 `lessons/lesson-045.json`（奇数课）和 `lesson-046.json`（偶数课），复制结构而不是复制内容。
7. 渲染本批，再更新首页和课间导航：

   ```sh
   python3 "$SKILL_DIR/scripts/render_lessons.py" --repo /path/to/nce1 --from 47 --to 60
   python3 "$SKILL_DIR/scripts/sync_navigation.py" --repo /path/to/nce1 --from 47 --to 60
   python3 "$SKILL_DIR/scripts/render_lessons.py" --repo /path/to/nce1 --from 47 --to 60 --check
   ```

   渲染器只覆盖带本模板标记的页面，遇到旧式手写页面停止，避免覆盖既有成果。修改 JSON 后重渲染，不直接改生成 HTML。导航脚本只调整本批及边界课的相关按钮，并根据实际 HTML 文件刷新首页。
8. 检查 HTML 标题、三部分、可答题总数、示例只读、source links、图片完整性和前后页。浏览器可用时检查桌面/手机布局，填写一题验证进度，Submit 验证答案报告及复制降级；不能把静态校验说成浏览器验证。每批做适量代表性验证，避免每课重复昂贵的截图流程。
9. 报告实际完成范围、pending 图片数、跳过原因和验证结果。Git 提交/推送遵循当前会话授权，不把调用本 skill 本身当作推送授权。

## 后续补图

图片和文案的唯一数据源是 `lessons/lesson-NNN.json`。筛选 `images.*.status == "pending"` 得到待补图；使用 `description`、对应 block 的原文及引用的 `characters` 制作图片。文本优先模式无需 API key。

将图片放入 `html/assets/lesson-NNN/`，在该 slot 设置 `status: ready`、`src`（相对 html/）、`width`、`height`，保留原来的 `kind`、描述和文字关联，然后重新渲染该课。页面自动把图放到对应原文旁边。批量补图不改题目 ID、不删文字、不重新编排练习。

新题型需要更复杂的表格等展示时，先在 JSON 完整保留信息；有必要再扩展 renderer 的 block 类型，不能只用当前类型能力裁减题目。
