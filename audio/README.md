# 课程音频

当前使用本地 Qwen3-TTS 1.7B CustomVoice（MLX 4-bit）。正常美式语速，按角色分配声音，并逐句设置语气和停顿。

| 课程与内容 | 文件 | 时长 |
| --- | --- | --- |
| 第一课：课文、注释、词汇与常用表达扩展 | [001-1-lesson.wav](001-1-lesson.wav) | 2 分 17 秒 |
| 第一课：练习 | [001-2-practice.wav](001-2-practice.wav) | 1 分 51 秒 |
| 第一课：语法 | [001-3-gramar.wav](001-3-gramar.wav) | 2 分 46 秒 |
| 第二课：图片练习、词汇、书面练习 | [002-1-lesson.wav](002-1-lesson.wav) | 2 分 34 秒 |
| 第二课：练习册 | [002-2-practice.wav](002-2-practice.wav) | 1 分 44 秒 |
| 第二课：语法 | [002-3-gramar.wav](002-3-gramar.wav) | 约 3 分 4 秒 |

`gramar` 沿用原文件名。角色标签和 Question / Answer / Statement 标签不朗读。练习包含完整答案；题目与答案之间留有停顿。

## 词汇与页面顺序

**每课词汇并入 lesson 文件，严格遵循 HTML 的 section 顺序，不单独生成词汇音频。** 第一课是课文与注释之后读词汇；第二课是图片练习 → 词汇 → 书面抄写。

按词汇表顺序读单词／短语，再给一个现代日常美式场景的例句，例如 “Can I borrow your pen?”、“I left my watch at home.”、“Where did you park your car?”。第一课 11 个词条，第二课 10 个词条；不读音标、词性或中文。

保留课本原词。针对用法差异补充语境说明与常用表达：handbag 仍在使用，美式也常说 purse；Pardon? 礼貌但可能显得正式，日常可用 “Sorry, I didn't catch that.”；Thanks 是 thank you 的常见简短形式。这些是词汇 section 的扩展，不改写练习的标准答案，也不把原词一概说成过时。

## 第二课练习依据

第二课按每个 section 的指令组织录音：

- 图片题：物品提示 → 停顿 → 完整问句。问句本身是造句题的答案，不凭图片推断所有权。
- 情景题：情景 → 停顿 → 适用表达。
- 排序题：原词序提示 → 停顿 → 完整问句。
- 问答题：物品提示 → 问句 → “Yes, it is.”。
- 抄写题：按顺序读完整句子。

已核对原书图片、练习册答案及语法 PDF，覆盖 56 个原始条目（含示例）。详细来源见 [第二课内容依据](scripts/002/README.md)。词汇例句为补充学习材料。

## 目录与生成

```text
audio/
├── NNN-1-lesson.wav        课文／图片练习，含词汇
├── NNN-2-practice.wav      练习册
├── NNN-3-gramar.wav        语法
├── scripts/001/            第一课角色表、三个脚本
├── scripts/002/            第二课角色表、三个脚本及来源说明
├── scripts/examples/       多人对话示例脚本
├── examples/               多人对话样音
└── work/                   逐句缓存、生成记录与检查报告（不上传）
```

在项目根目录运行，例如生成第二课 lesson：

```sh
HF_HUB_OFFLINE=1 /Users/admin/.local/share/nce1-qwen3-tts/bin/python \
  skills/nce1-lesson-audio/scripts/render_qwen3_audio.py \
  --script audio/scripts/002/lesson.json \
  --model "$HOME/.cache/nce1-models/Qwen3-TTS-12Hz-1.7B-CustomVoice-4bit" \
  --output audio/002-1-lesson.wav
```

练习和语法分别用 `practice.json`、`grammar.json`，输出对应文件名。角色表通过 `roles_file` 引用。词汇段落在 `lesson.json` 中标记为 `section: "vocabulary"`，修正片段保留选定的随机种子和生成参数。程序将中间文件放到 `audio/work/<输出文件名（无扩展名）>/`，可用 `--work-dir` 修改。

## 多人角色与校验

第一课保持 Ryan 男声／旁白和 Serena 女声。第二课图片题按图中提问者使用 Ryan、Aiden、Serena、Vivian，其他练习的角色分配见课程 `roles.json`。每个角色保持固定声音，名字不作为朗读标签。

[四人对话示例](examples/four-roles.wav)约 23 秒，对应[脚本](scripts/examples/four-roles.json)：Tom/Ryan、Jack/Aiden、Sue/Serena、Anna/Vivian。Ryan/Aiden 是英语预设，其他声音的口音和自然度需结合试听判断。

音频已检查完整性，并用本地语音识别辅助核对台词。识别差异需结合后续分段检查和修正记录查看，ASR 不代表听感评价。正式 WAV、角色表和脚本随 Git 提交，逐句缓存与本地校验报告不上传。旧 Kokoro 成品、历史试听和对应程序已清理。模型和 Python 环境位于用户目录，生成无需 API key，不使用 ffmpeg。

## 扩展声音表：5 男 + 4 女

现在可按角色选择全部 9 个预设，模板见 [roles-template.json](../skills/nce1-lesson-audio/assets/roles-template.json)。

- 男声：Ryan、Aiden、Uncle_Fu、Dylan、Eric。
- 女声：Serena、Vivian、Ono_Anna、Sohee。

[九种声音对比](examples/nine-voices.wav)使用相同的问句和回答；播放顺序、时间位置见 [声音索引](examples/voices.md)。新声音的英文口音和听感需要试听判断，优先保证清楚自然。后续人物多的课文会按人物建立固定分配，并可用角色指令补充老师、学生、店员等说话风格；风格变化不等于新的独立音色。
