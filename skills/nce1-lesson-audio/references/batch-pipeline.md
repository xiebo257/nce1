# Large local batches

Use this workflow when continuing through many lessons. Run from the repository root. It reuses source answer fields and a reviewed vocabulary bank rather than asking an LLM to rewrite every exercise.

## Prepare and inspect

```sh
python3 skills/nce1-lesson-audio/scripts/prepare_lessons.py --start 25 --end 144
```

The compiler reads nested `section//article`, both `.spoken` dialogue and odd-lesson prose in `.reading-prompt`, vocabulary in DOM order, and every answer field including examples. It combines progressive blanks when adjacent fields contain successive parts of the same sentence, recording all IDs in `source_items`. Never split a multiword answer like `was sitting` across unrelated blanks. Source coverage alone does not prove that narrative text or static conversation turns are present.

Assets separate reusable content from exceptions:

- `vocabulary-examples.json`: modern examples; original target words remain intact.
- `vocabulary-usage.json`: contextual regional/register alternatives.
- `speech-overrides.json`: completed personal models and individual source corrections, with provenance.
- `passage-overrides.json`: complete text restored from scans where HTML is abbreviated.

Compilation fails on unresolved blanks, unknown vocabulary examples, Chinese in speech, or missing answer items. The compact exception report is `audio/work/batch-025-144/compile-errors.json`. Inspect exceptions and linked scans; do not fill malformed source items by blindly concatenating keys. Lessons 135 and 141 have abbreviated HTML passages; 137 B has misaligned HTML keys. Their corrected audio content is based on the actual textbook/workbook scans, not inferred from malformed prompts.

ASR compares speech to the prepared script, so a matching transcript does not establish that the script correctly completed the workbook. Audit source ellipsis blanks, verb/preposition sorting tables, printed item codes, and quoted dialogue independently. The reviewed overrides cover lessons 070, 110–116 and other known source exceptions. Preserve complete filled answers and alternating dialogue turns; never read an unfinished sentence followed by an isolated missing word as though that were a completed answer. Time cues such as `8.05` must retain the hour rather than being stripped as question numbering.

Do not recompile scripts currently being rendered: the renderer writes effective seeds back into them. Recompilation preserves exact `(source_item, role, text)` repairs, but changes in role assignment or instructions invalidate speech cache entries. Keep a consistent named cast across a range and inspect same-scene voice collisions.

## Render, check, and publish small batches

When the user has authorized incremental commits and pushes:

```sh
python3 skills/nce1-lesson-audio/scripts/run_audio_queue.py \
  --start 26 --end 144 --batch-size 2
```

The queue loads the local Qwen3 model for each small batch, renders using the content cache, runs local Whisper on grouped segments, and individually rechecks recognition differences. It retries unresolved segments at most twice with deterministic new seeds and lower temperature, retains the best checked version, and records residual differences in `review-NNN-NNN.json`. An agent should inspect residuals and either repair actual omissions/substitutions or record recognition-only differences in `accept-NNN-NNN.json`. This marker is an internal review record, not a user permission request. The queue continues preparing later batches while a batch awaits review; publish reviewed batches promptly.

To publish a reviewed batch:

```sh
python3 skills/nce1-lesson-audio/scripts/publish_audio_batch.py \
  --start 26 --end 27 --publish
```

The publisher checks source coverage, vocabulary order, role references, WAV decoding, 24 kHz mono PCM16, finite nonempty audio, segment counts, generation parameters, exact assembled frame counts, and GitHub's per-file size limit. It writes source notes and an idempotent listening index, then commits only the batch's files and pushes. Preserve unrelated staged changes; never use a broad `git add .` or commit the whole index. Only use `--publish` when the session authorizes commits/pushes.

Queue state files and logs live under ignored `audio/work/`. A successful queue batch records `pushed: true`. If publishing manually, update that batch's queue record after checking the push result. A failed push is not completion; retry the push rather than generating another commit for unchanged files.

## Cost, speed, and quality limits

- No remote LLM calls, API keys, ffmpeg, or new model downloads are needed on the configured machine.
- Exact speech reuse is keyed by text, voice, instructions, model, seed, and temperature. Silence is added at assembly time.
- Intermediate segment files hard-link to cached speech where possible, reducing duplicated disk use. Final WAVs remain independent files.
- Keep one TTS worker; a filesystem lock prevents competing model loads. The optional `--prefetch` mode generates the next two lessons during ASR. Enable it only after measuring throughput: shared GPU contention slowed synthesis in the observed run, so sequential processing remains the default.
- Use compact counts, log tails, and exception reports instead of loading every HTML file and every recognition transcript into the conversation.
- ASR normalizes common contractions and spelling variants. It cannot prove that a required full form was articulated distinctly, or that accent, linking, reduction, and intonation sound natural. Preserve contrast instructions in the script and use listening when that distinction matters.
- Bare numerals and isolated function words may be unstable. Use a short appropriate frame without changing the answer. Proper names, weak vowels, and homophones can produce recognition differences; do not retry endlessly merely to force a spelling.
- Spell telephone numbers and other leading-zero identifiers digit by digit, preserving every zero. For verb sorting exercises, reconstruct the complete correct collocation from the printed table; HTML may incorrectly attach the same verb to every cue (lesson 061).

Recovered vocabulary is recorded in `recovered-vocabulary.json` with the inspected scan path. Keep the HTML word list in order and add the verified missing textbook words within its vocabulary block; if the HTML omits the block entirely, add the recovered list after the reading. Do not claim that missing HTML vocabulary never existed in the textbook.

Lesson 113 has six individual male characters and two female passengers. The local model has five male presets, so its two later scenes reuse one preset for different characters; the role identities remain separate. The first and second passengers and the two later travelers are visibly separate groups. Do not describe nine presets as unlimited distinct actors.
