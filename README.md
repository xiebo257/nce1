# nce1

nce1 lesson, practice, grammar

1. [x] upload all lesson, practice images
2. [ ] make all lesson HTML
3. [ ] make all lesson audio including practice, grammar
4. [ ] make all lesson image color painted
5. [ ] try to make video

第 45–144 课使用 [nce1-lesson-html skill](skills/nce1-lesson-html/SKILL.md)
制作文字优先的学习页。已验证样例：[第 45 课](html/lesson-045.html)、
[第 46 课](html/lesson-046.html)。

在 Codex 中使用：

```text
用 $nce1-lesson-html 生成第 47–60 课。奇数课先保留文字，偶数课能快速裁图就裁，慢则跳过，保留完整文字。
```

课文内容、答案与待补图位置保存在 `lessons/lesson-NNN.json`。核对内容后，
用模板生成 HTML；脚本不负责 OCR 或自动转录教材：

```sh
python3 skills/nce1-lesson-html/scripts/render_lessons.py --from 45 --to 46
python3 skills/nce1-lesson-html/scripts/sync_navigation.py --from 45 --to 46
python3 skills/nce1-lesson-html/scripts/render_lessons.py --from 45 --to 46 --check
```

本机已将该 skill 链接到 `~/.codex/skills/nce1-lesson-html`。在其他机器上，
把仓库的 `skills/nce1-lesson-html` 目录复制或链接到自己的 Codex skills 目录即可。
