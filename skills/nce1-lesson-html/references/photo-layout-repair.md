# 照片排版修复

先完整记录用户指定范围的照片分组，再修改 canonical JSON。`reports/photo-layout-audit/` 是第48–144课实例：原始坐标OCR、逐课目视发现、修复映射分别保存；OCR不是已校对正文。

- `recognize_lesson_photos.swift` 使用本地 Apple Vision 输出文字与坐标。先处理旋转，再按版面分栏、编号和图文位置人工核对，不能全页按纵坐标串行拼接。
- `photo-frame-regions.json` 保存照片坐标系、旋转和分格框。`prepare_photo_panels.py` 根据完整边框轮廓做透视矫正；斜边包围盒可能包含邻格，不能以最靠近四角的墨点推断边框。自动定位失败时填写显式四边形，并检查每幅裁图。
- `repair-map.json` 保存核对后的逐图原文/台词、原编号、组别和表格。比较句应保留成对/三联关系，词表、时间表要恢复列关系。原来正确的彩图可逐格拆分；彩图本身错误时必须重做。
- `colorize_photo_panels.py` 使用已安装的本地 FLUX.2 Klein 模型，一课共享图集以减少加载开销，再拆成候选图。原始照片线稿约束人物、动作、物品数量；颜色后处理可以统一重复人物。图集仅是生成中间产物，每格独立入页。
- `refine_photo_colors.py` 的局部填色需目视复核，不能自动批准。`color-reviews.json` 把批准绑定到最终图集哈希；图集变化后必须重新检查。
- `repair_photo_layout.py --lessons ...` 应用指定映射并校验独立 Practice/Grammar 没有变化。它不是通用识别器；不要在未知源图上套用该批固定映射。基线提交保证重跑可复现；执行前检查是否有用户后续修改，不能覆盖后续变更。
- `table` block 使用 `caption`、`headers`、`rows`，每行列数必须一致。原编号用 `source_label`，关联组用 `source_group`；`cue_heading` 保存共同提示。`source_status` 向学习者说明真实源照片裁切限制。

发布前逐格检查顺序、裁边、人物与提示含义，校验 JSON/HTML、所有本地图片，并抽查桌面与手机布局。浏览器检查图片时先触发 lazy-load 或 `decode()`，不能将尚未加载判为缺图。

正文或提示变化时记录音频待同步项。只拆图/分段不表示音频需要重合成，也不能仅凭旧音频文件存在就宣称新正文已有同步录音。音频更新是另一个明确执行并验证的步骤。
