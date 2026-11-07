# 第一课音频

当前正式版本使用本地 Qwen3-TTS 1.7B CustomVoice（MLX 4-bit），Ryan 男声／旁白和 Serena 女声。正常语速，按句子设置语气并保留问答停顿。

| 内容 | 文件 | 时长 |
| --- | --- | --- |
| 课文 | [001-1-lesson.wav](001-1-lesson.wav) | 44 秒 |
| 练习 | [001-2-practice.wav](001-2-practice.wav) | 1 分 51 秒 |
| 语法 | [001-3-gramar.wav](001-3-gramar.wav) | 2 分 46 秒 |

`gramar` 沿用原文件名。角色标签和 Question / Answer / Statement 标签不参与朗读；练习包含完整答案，语法按题目、停顿、答案的顺序播放。

## 目录

```text
audio/
├── 001-1-lesson.wav         正式课文
├── 001-2-practice.wav       正式练习
├── 001-3-gramar.wav         正式语法
├── scripts/001/            当前角色表与三个生成脚本（JSON）
├── scripts/examples/       四人对话示例脚本
├── examples/               当前四人对话示例音频
└── work/                   逐句音频、生成记录、内容检查报告
```

`work/001-checks/` 中的整段识别报告记录了初次检查结果，其中的识别差异要结合 `group-check.json` 和 `final-repairs-check.json` 查看。语音识别核对台词，不代表听感评价。当前第一课成品和生成中间文件保留；旧 Kokoro 成品、历史试听及其脚本已清理。

## 重新生成

在项目根目录运行，`section` 设为 `lesson`、`practice` 或 `grammar`，`filename` 设为上表对应的正式文件名。例如生成课文：

```sh
HF_HUB_OFFLINE=1 /Users/admin/.local/share/nce1-qwen3-tts/bin/python \
  skills/nce1-lesson-audio/scripts/render_qwen3_audio.py \
  --script audio/scripts/001/lesson.json \
  --model "$HOME/.cache/nce1-models/Qwen3-TTS-12Hz-1.7B-CustomVoice-4bit" \
  --output audio/001-1-lesson.wav
```

练习使用 `audio/scripts/001/practice.json`，语法使用 `audio/scripts/001/grammar.json`。程序默认将逐句音频及生成记录写入 `audio/work/<音频文件名（不含扩展名）>/`，也可通过 `--work-dir` 指定位置。脚本保留了修正片段的随机种子和生成参数。

模型缓存在用户目录，Python 环境也独立存放，不混入音频目录。生成不需要 API key，不使用 ffmpeg。

## 多人角色

每课用 `scripts/课号/roles.json` 统一管理角色，课文、练习和语法都通过 `roles_file` 引用。台词用 `role` 指定说话人；角色名称不会被念出来。同一个人物在各部分保持相同声音。当前第一课已迁移到角色表，原有声音、台词、修正参数和成品音频保持一致。

[四人对话示例](examples/four-roles.wav)约 23 秒，对应[示例脚本](scripts/examples/four-roles.json)：

| 人物 | 声音 | 性别 |
| --- | --- | --- |
| Tom | Ryan | 男 |
| Jack | Aiden | 男 |
| Sue | Serena | 女 |
| Anna | Vivian | 女 |

模型另有 Uncle_Fu、Dylan、Eric 男声和 Ono_Anna、Sohee 女声，可按后续课文人物试用。Ryan/Aiden 是英语预设；其他声音原始语言不同，英语口音和听感要通过样音判断。第一课已认可 Ryan/Serena，新增声音尚待实际试听评价。

正式 WAV、当前四人示例、角色表和生成脚本随 Git 提交；`work/` 中可重新生成的逐句缓存及本地校验报告忽略，不上传。
