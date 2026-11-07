---
name: nce1-lesson-audio
description: Generate natural American English audio for New Concept English Book 1 lessons with local speech models, lesson audio with vocabulary in HTML section order, separate practice and grammar WAV files, role based dialogue, completed answers, and grammar prompts followed by answers.
---

# NCE1 lesson audio

Generate lesson, practice, and grammar WAV files when those sections exist in the project's `audio/` directory. Include every lesson's vocabulary inside its lesson audio at the position of the vocabulary section in the source HTML; do not create a separate vocabulary audio file. Do not fabricate missing sections merely to fill filenames. The learner approved Qwen3-TTS over Kokoro; use **Qwen3-TTS CustomVoice 1.7B, MLX 4-bit**, with a fixed cast per lesson. The accepted first-lesson voices are **Ryan** for male dialogue and narration and **Serena** for female dialogue. For multiple characters, assign distinct presets using the role table below. No new sample approval is needed for this accepted setup.

## Content and delivery

Read `html/lesson-NNN.html` before preparing a new lesson. Use linked scans and the grammar PDF if necessary, and check workbook answers against available answer keys. Preserve exercise order and every item. Reuse existing corrected scripts when regenerating an unchanged lesson.

- Lesson: introduce the situation and reading question, perform the dialogue with distinct voices, then give the reading answer. Include vocabulary or pronunciation notes when relevant to the source.
- Vocabulary: include the lesson's New words and expressions list within `NNN-1-lesson.wav`. Follow the HTML order of blocks as well as the source order of words. For lesson 001, dialogue and notes precede vocabulary; for lesson 002, picture prompts precede vocabulary, followed by the written exercise. Never append vocabulary blindly if later lesson sections follow it. Read each word or phrase, pause, then a short natural example sentence and a repeat pause. Examples are supplemental; record that in script notes. Use American pronunciation even if the page prints British IPA. Do not read IPA, part-of-speech labels, or Chinese translations unless requested. Include expressions such as “thank you”; do not silently omit function words.
- Practice: complete all answers before generating speech. Use an example name for personal responses and explain it when necessary.
- Grammar: speak the actual prompt, pause, then give the answer. For transformations, read the statement followed by its question form.
- Never speak role prefixes (`Sue:`, `John:`, `You:`, `A:`, `B:`), repeated `Question:`, `Answer:`, or `Statement:` labels, HTML markup, blanks, or Chinese translations. Keep names inside actual sentences, such as “My name is John.”
- Use normal conversational American English and restrained expression. Yes/no questions and “Pardon?” often rise; neutral wh-questions and completed answers usually fall. Pass directions through `instructions`, not spoken `text`. Instructions guide delivery but do not guarantee pitch contours.

## Contemporary vocabulary examples and alternatives

Keep the book's target vocabulary and original exercise answers. Vocabulary example sentences should use contemporary everyday American situations: borrowing a pen, checking whether a seat is free, finding a phone or keys, parking a car, getting dressed, or inviting a friend over. Prefer short idiomatic sentences and normal contractions. Do not default every entry to “This is my …” merely because that grammar is easy. Keep examples understandable for the lesson's level.

For a term that is formal, regionally different, dated in a particular sense, or less common in current casual speech, add a brief usage explanation and a useful modern alternative immediately after that vocabulary item. Mark supplemental examples with `supplemental: true`; do not replace the printed word silently or change source exercise answers. Distinguish register and region from obsolescence, and do not invent usage claims. Modern alternatives are for learning, not claims that every original word is old-fashioned.

Examples relevant to lesson 001:

- `handbag` remains current; `purse` is also common in American English for this kind of bag. Example: “I left my keys in my purse.” Do not equate every bag with a purse or present the terms as interchangeable in every dialect.
- `Pardon?` is valid and polite but can sound formal; a casual alternative is “Sorry?” or “Sorry, I didn't catch that.” Preserve “Pardon?” when the exercise requires it.
- `Thank you very much` is current; `Thanks` is a common casual shorter alternative, not a universal replacement.

Lesson 002 words such as pen, pencil, book, watch, coat, dress, skirt, shirt, car, and house are current vocabulary. Give natural examples such as “Can I borrow your pen?”, “I left my watch at home.”, and “Where did you park your car?”; there is no need to invent replacements for ordinary words.

Record vocabulary and supplemental material in `lesson.json`, in the exact position of the HTML vocabulary section. Follow later HTML sections after it. Keep only the three standard audio filenames; never create a separate vocabulary script or WAV unless the user changes this preference.

## Practice lessons and images

Determine the lesson type from its sections and instructions, not just its number. For a picture/exercise lesson, inventory every section, example, item, image, prompt, and answer before preparing audio. Adapt each section's instruction into a short spoken introduction and preserve its task:

- Picture-to-question: identify the pictured object, allow a response pause, then speak the complete target question. This target question is the exercise answer. Do not automatically add an affirmative ownership answer when the section only asks for question formation.
- Ask-and-answer: supply both the question and the required response, with distinct voices and a pause. Follow affirmative/negative cues from the prompt or answer key.
- Word ordering: read the given words in their original order with short pauses, then the completed sentence. Do not read slash separators.
- Situations: read the situation naturally, pause, then the appropriate expression.
- Copying: read each complete printed sentence, preserving sequence and allowing time to pause and write.

Use existing answer sentences first, checking answer-key scans/PDFs when available. Inspect the actual local image with the image viewing tool when visual information matters; filenames and alt text alone are not visual verification. If no answer is supplied, derive a sentence from the visible content and section instructions. Store its source and whether it is inferred in JSON metadata, never in spoken text. If a picture does not establish ownership or another required fact, give a clearly identified model response or ask for clarification; do not present a guess as a source answer. Keep roles consistent with visible speakers where practical without adding unrelated characters.

Record `source_item` on segments so all original items, including examples, can be checked for coverage. Lesson 002 was verified against both textbook image pages, the workbook and its key, and grammar PDF pages 18–19 and 439–440. Its lesson audio contains ten picture cues with completed questions, then ten vocabulary entries with examples, then seven copy sentences; practice contains eleven question-formation items including the example and four situations; grammar contains ten word-order items and fourteen question/answer items.

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

The reusable cast pool has **five male voices and four female voices**. Read [assets/roles-template.json](assets/roles-template.json) when preparing a lesson with multiple characters; copy only the required entries to that lesson's `roles.json`, rename IDs to actual character names, and preserve metadata about original language.

| Template role | Preset | Group | Original language |
| --- | --- | --- | --- |
| man_1 | Ryan | Male | English |
| man_2 | Aiden | Male | English |
| man_3 | Uncle_Fu | Male | Chinese |
| man_4 | Dylan | Male | Chinese, Beijing dialect preset |
| man_5 | Eric | Male | Chinese, Sichuan dialect preset |
| woman_1 | Serena | Female | Chinese |
| woman_2 | Vivian | Female | Chinese |
| woman_3 | Ono_Anna | Female | Japanese |
| woman_4 | Sohee | Female | Korean |

Cast allocation:

- List distinct characters, their source gender when known, and relationships before assigning voices. Use separate presets for characters speaking in the same scene whenever possible. Do not stop at two voices per gender when more characters are present.
- Keep the existing accepted Ryan/Serena pairing for the first lesson. For new scenes, prefer Ryan/Aiden for English male voices and Serena/Vivian as the established female options; draw additional actors from the pool as needed. Select based on actual sample clarity, not the preset's name.
- Record a stable delivery style in a role's `instructions` when helpful: calm teacher, friendly shop assistant, curious student, or polite customer. Sentence instructions then express the immediate question or response. These are delivery directions, not additional independent voices or guaranteed age changes. Avoid exaggerated acting and artificial pitch shifts.
- Keep the same character's speaker and general delivery consistent across lesson, practice, and grammar. For recurring named characters, reuse an established mapping from earlier lessons unless there is a reason to change.
- Non-English presets can synthesize English; test their accent and clarity rather than assuming a native American accent. Do not use an unclear voice solely to fill all nine slots. This model has nine preset identities, not unlimited independent voices; if a scene exceeds the usable pool, explain the limitation and choose another model or explicitly plan scene-separated reuse.
- A narrator may share a preset when clearly separated from dialogue. Do not invent extra characters just to use more voices, and never read role labels.

The nine-preset comparison script is `audio/scripts/examples/nine-voices.json`, rendered to `audio/examples/nine-voices.wav`; its sequence and timestamps are documented in `audio/examples/voices.md`. Every preset reads identical question and answer lines to make comparison easier. The original four-character scene remains at `audio/examples/four-roles.wav` as a dialogue example. New presets are candidates, not learner-approved native American voices; do not make new approval a prerequisite to requested generation.

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

Repeat with `practice.json` → `001-2-practice.wav` and `grammar.json` → `001-3-gramar.wav`. Vocabulary segments live in `lesson.json` with `section: "vocabulary"`; use `vocabulary_words` to check completeness. Intermediate segments and `manifest.json` go to `<output parent>/work/<output stem>/`; `--work-dir` overrides this location. Existing first-lesson scripts contain the completed answers and repaired generation parameters.

For a fresh setup, create a separate Python 3.11 environment and install `mlx-audio==0.6.4` plus `soundfile`. Download `mlx-community/Qwen3-TTS-12Hz-1.7B-CustomVoice-4bit`, including `speech_tokenizer/` (approximately 2.3 GB total). ModelScope hosts this repository and worked when HF mirror large-file downloads stalled. Verify sizes and SHA256 against repository metadata, then load the local directory. No API key, ffmpeg, macOS say, or pitch shifting is needed.

## Batch generation

For several lessons, inventory every source HTML section and prepare reviewed JSON scripts before rendering. Include fixed dialogue lines outside answer fields (for example, `section-intro` paragraphs); answer-field coverage alone does not prove a complete conversation. Fill missing words into complete sentences, choose and identify model responses for personal questions, and keep both questions with the same speaker when one turn contains consecutive questions. Read IPA sound groups through whole-word examples rather than spelling out the symbols. If a lesson has no New words section, preserve its actual vocabulary or word-form review in the notes instead of inventing a new textbook section.

Use `scripts/render_qwen3_batch.py` to load the local model once and render a range of prepared lessons:

```sh
HF_HUB_OFFLINE=1 /Users/admin/.local/share/nce1-qwen3-tts/bin/python \
  skills/nce1-lesson-audio/scripts/render_qwen3_batch.py \
  --start 4 --end 24 \
  --model "$HOME/.cache/nce1-models/Qwen3-TTS-12Hz-1.7B-CustomVoice-4bit"
```

The batch helper caches exact text, voice, instructions, model location and generation parameters under ignored `audio/work/speech-cache/`. Re-running resumes through this cache; edited speech gets a new cache key. Effective generation seeds and temperatures are saved in the lesson scripts. Excessively long short sentences are retried up to three times and remaining duration concerns are recorded for review. This check does not detect all wrong words: perform content checks and repair affected segments before delivery. Batch intermediate segment names use three digits.

For connected speech, ask for light reductions of unstressed function words and natural linking at a normal pace. Preserve full forms when an exercise explicitly contrasts them with contractions. A short word plus a natural example in the same generation can be clearer than an unstable isolated word; keep the word audible before its example. Bare numerals can also produce unstable speech: spell out the number and use a brief natural context when needed, such as “That makes five” for a sum. Check number answers separately from digit-by-digit writing cues. If an isolated exercise word remains unclear, use a task-appropriate short sentence such as “The plural is skirts” or “The opposite is cold,” keeping the target answer intact. Do not infer correct linking, pitch, or accent from successful speech recognition.

## Validation

Check WAV decoding, sample rate, duration, and nonempty finite audio. Review unusually long short sentences, especially outputs at the generation token limit. Regenerate suspicious segments and preserve their selected seed/temperature in the source JSON.

Use speech recognition for content checks when available. Repetitive exercises can cause whole-file recognition omissions: check affected segments separately before deciding speech is missing. Record initial findings, repairs, and final checks under `work/NNN-checks/`. Do not claim subjective listening or accent validation from file headers or ASR. Report the generated file links and durations, noting that vocabulary is included in lesson audio.

For long runs through many lessons, use the [large-batch pipeline](references/batch-pipeline.md). It includes a deterministic HTML compiler, contemporary vocabulary assets, bounded ASR-assisted repair, resumable job records, and a publisher that commits/pushes each small reviewed batch when authorized. Read that reference instead of reconstructing one-off watcher scripts. Inspect both nested articles and prose outside `.spoken`; source-field coverage cannot detect missing prose. Keep only compact exception reports in the conversation to reduce token use.
