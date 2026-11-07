---
name: nce1-lesson-audio
description: Generate natural American English audio for New Concept English Book 1 lessons with local speech models, separate lesson, practice, and grammar WAV files, role based dialogue, completed answers, and grammar prompts followed by answers.
---

# NCE1 lesson audio

Generate three WAV files per lesson in the project's `audio/` directory. The learner approved Qwen3-TTS over Kokoro; use **Qwen3-TTS CustomVoice 1.7B, MLX 4-bit**, with a fixed cast per lesson. The accepted first-lesson voices are **Ryan** for male dialogue and narration and **Serena** for female dialogue. For multiple characters, assign distinct presets using the role table below. No new sample approval is needed for this accepted setup.

## Content and delivery

Read `html/lesson-NNN.html` before preparing a new lesson. Use linked scans and the grammar PDF if necessary, and check workbook answers against available answer keys. Preserve exercise order and every item. Reuse existing corrected scripts when regenerating an unchanged lesson.

- Lesson: introduce the situation and reading question, perform the dialogue with distinct voices, then give the reading answer. Include vocabulary or pronunciation notes when relevant to the source.
- Practice: complete all answers before generating speech. Use an example name for personal responses and explain it when necessary.
- Grammar: speak the actual prompt, pause, then give the answer. For transformations, read the statement followed by its question form.
- Never speak role prefixes (`Sue:`, `John:`, `You:`, `A:`, `B:`), repeated `Question:`, `Answer:`, or `Statement:` labels, HTML markup, blanks, or Chinese translations. Keep names inside actual sentences, such as “My name is John.”
- Use normal conversational American English and restrained expression. Yes/no questions and “Pardon?” often rise; neutral wh-questions and completed answers usually fall. Pass directions through `instructions`, not spoken `text`. Instructions guide delivery but do not guarantee pitch contours.

Serena is a Chinese female preset capable of English synthesis. The learner liked the sample; do not describe her as a verified native American voice.

## Files and scripts

Keep `audio/` tidy:

```text
audio/
  NNN-1-lesson.wav
  NNN-2-practice.wav
  NNN-3-gramar.wav
  README.md
  scripts/NNN/{roles,lesson,practice,grammar}.json
  scripts/examples/            Current reusable multi-role example
  examples/                    Current multi-role demonstration audio
  work/NNN-1-lesson/            segments/ and manifest.json (likewise other files)
  work/NNN-checks/              Content checks and repair reports
```

Keep the user's `gramar` spelling. Do not delete unrelated audio. Put demonstrations under `examples/` and intermediate files under `work/`, not at the audio root. Old Kokoro files, past voice comparisons, and the obsolete online renderer have been removed at the user's request. Keep model weights and environments outside the project.

## Multiple characters

Use a lesson-wide `roles.json` shared by its three scripts. Each role ID maps to a preset `speaker`, a description, and optional delivery `instructions`. A segment uses `role` to identify the character, never putting the role label in spoken text. The same character must retain its preset across scenes and sections. Roles are semantic identities, not genders; do not collapse all male or female characters into one voice.

For example, `roles.json`:

```json
{
  "tom": {"speaker": "Ryan", "description": "Tom, male"},
  "jack": {"speaker": "Aiden", "description": "Jack, male"},
  "sue": {"speaker": "Serena", "description": "Sue, female"},
  "anna": {"speaker": "Vivian", "description": "Anna, female"}
}
```

And a section script:

```json
{
  "seed": 42,
  "roles_file": "roles.json",
  "segments": [{
    "role": "anna",
    "text": "Pardon?",
    "instructions": "Speak in conversational American English at a normal pace. Politely ask for repetition with a gentle questioning rise.",
    "pause_after": 0.45
  }]
}
```

`roles_file` is relative to the script. An inline `roles` object is also supported, but not together with `roles_file`. Role instructions are prepended to sentence instructions. The helper rejects undefined roles and conflicting speaker overrides. Existing direct `speaker` segments remain supported. Per-segment `generation_seed` and `generation_temperature` preserve repairs. Only `text` is spoken.

Available presets in the installed model:

| Presets | Voice group | Original language |
| --- | --- | --- |
| Ryan, Aiden | Male | English |
| Serena, Vivian | Female | Chinese |
| Uncle_Fu, Dylan, Eric | Male | Chinese |
| Ono_Anna | Female | Japanese |
| Sohee | Female | Korean |

Start with Ryan/Aiden and Serena/Vivian for two male and two female characters. Additional presets can be tested when a lesson needs more distinct voices. Non-English presets can synthesize English, but do not assume their accent is native American. Instructions can adjust delivery; they do not create unlimited distinct voice identities. Do not add characters absent from the lesson. A narrator may share a preset when clearly separated from dialogue.

The current four-character example is `audio/scripts/examples/four-roles.json`, rendered to `audio/examples/four-roles.wav`. Its roles are Tom/Ryan, Jack/Aiden, Sue/Serena, Anna/Vivian. Additional voices have not yet received learner listening approval; report that distinction without making approval a prerequisite to requested generation.

## Generate with Qwen3-TTS

The local environment is `/Users/admin/.local/share/nce1-qwen3-tts`, using Python 3.11, `mlx-audio==0.6.4`, and `soundfile`. The model directory is `~/.cache/nce1-models/Qwen3-TTS-12Hz-1.7B-CustomVoice-4bit`.

From the repository root:

```sh
HF_HUB_OFFLINE=1 /Users/admin/.local/share/nce1-qwen3-tts/bin/python \
  skills/nce1-lesson-audio/scripts/render_qwen3_audio.py \
  --script audio/scripts/001/lesson.json \
  --model "$HOME/.cache/nce1-models/Qwen3-TTS-12Hz-1.7B-CustomVoice-4bit" \
  --output audio/001-1-lesson.wav
```

Repeat with `practice.json` → `001-2-practice.wav` and `grammar.json` → `001-3-gramar.wav`. Intermediate segments and `manifest.json` go to `<output parent>/work/<output stem>/`; `--work-dir` overrides this location. Existing first-lesson scripts contain the completed answers and repaired generation parameters.

For a fresh setup, create a separate Python 3.11 environment and install `mlx-audio==0.6.4` plus `soundfile`. Download `mlx-community/Qwen3-TTS-12Hz-1.7B-CustomVoice-4bit`, including `speech_tokenizer/` (approximately 2.3 GB total). ModelScope hosts this repository and worked when HF mirror large-file downloads stalled. Verify sizes and SHA256 against repository metadata, then load the local directory. No API key, ffmpeg, macOS say, or pitch shifting is needed.

## Validation

Check WAV decoding, sample rate, duration, and nonempty finite audio. Review unusually long short sentences, especially outputs at the generation token limit. Regenerate suspicious segments and preserve their selected seed/temperature in the source JSON.

Use speech recognition for content checks when available. Repetitive exercises can cause whole-file recognition omissions: check affected segments separately before deciding speech is missing. Record initial findings, repairs, and final checks under `work/NNN-checks/`. Do not claim subjective listening or accent validation from file headers or ASR. Report the three final links and durations.
