# Lesson JSON contract

`lessons/lesson-NNN.json` is the canonical content and image manifest. HTML is generated and uses the existing shared CSS and JS. All strings are plain text, never raw HTML; newlines render as line breaks. The renderer escapes content and attributes.

## Top level

- `number`: integer 45–144; must agree with filename.
- `status`: `draft` during transcription, `verified` only after checking sources. Renderer accepts only verified content.
- `title`, `translation`, `description`: English title, Chinese title, concise bilingual description.
- `answer_note`: provenance/alternative-answer notes included in the copied report.
- `expected_answers`: independently counted editable fields, excluding examples. A multi-blank sentence may be one field, with answers in order. Never silently drop a sub-question.
- `sections`: exactly `lesson`, `practice`, `grammar`; each is an ordered list of blocks.
- `sources`: objects with `label` and `href`, relative to `html/`; PDF links use 1-based `#page=N` viewer indices.
- `characters`: map of stable character ID to fixed appearance description for this lesson's future illustrations.
- `images`: map of stable image slot ID to image metadata. This is also the batch-image queue.

## Blocks

Every block has a unique document-wide `id`, a `type`, and a `source` pointing at the checked local scan/PDF. Optional `image` references a single slot in `images`. The block always renders its text, regardless of whether an image exists.

- `text`: `text`, optional `translation`. For picture exercises retain all numeric and grammatical cues, not just a short caption.
- `dialogue`: `lines` with `number`, `speaker`, `text`, `translation`. Keep original order and stable line numbers across scenes. A monologue can use an empty speaker string.
- `vocabulary`: `items` with `word`, `ipa`, `pos`, `meaning`.
- `notes`: `items` with `title`, `text`.
- `exercise`: `title`, `instruction`, `translation`, `source`, `expected_items` (including examples), `answer_kind`, optional `key_source`, optional `word_bank` string list, optional `context`, and `questions`.

Question fields:

```json
{
  "id": "practice-b-2",
  "number": "2",
  "prompt": "she / make cakes? – biscuits",
  "answer": "Can she make cakes?\nNo, she can’t make cakes, but she can make biscuits.",
  "rows": 3
}
```

- `example: true` makes a prefilled readonly example excluded from progress.
- `answer_kind` may be inherited from the exercise or overridden on a question:
  - `source-key`: checked printed answer; the exercise must have `key_source`.
  - `source-example`: an actual worked example printed in the source.
  - `suggested`: a supplied model answer when no official key was available, labelled in the copied report.
- If a group spans multiple source/key pages, link the first in the block and include all pages/range in top-level `sources`. Check every continuation page.
- Keep instructions, word banks, supplied cues and fixed dialogue lines. Use `context` for non-answer material. Do not convert a source example into a required question.
- Keep alternate accepted pronouns or answers from the key. Clarify ambiguous/source-imposed grammar drills in the instruction or answer note.

## Images

Pending scene example:

```json
{
  "scene-01": {
    "kind": "scene",
    "status": "pending",
    "description": "The boss calls Bob to his desk for a moment.",
    "characters": ["boss", "bob"],
    "source": "../img/lesson-045-01-text.jpg",
    "reason": "Odd lesson: text first; illustration deferred."
  }
}
```

Ready image adds `src`, `width`, `height`, optional `caption`, and changes status to `ready`. `src` is relative to `html/`, e.g. `assets/lesson-046/picture-01.webp`. Pending slots have no src. There is no broken `<img>` or empty visible placeholder for them.

`kind` is one of `scene`, `item`, `action`. `characters` may be empty for independent people or object-only images. When the same person recurs, reuse the character ID; don't merge all unrelated exercise people into one character.

For source crops record `origin: textbook-crop`, `source_size: [width,height]`, and either `crop: [left,top,right,bottom]` or `quad` in Pillow QUAD order (upper left, lower left, lower right, upper right; flat x/y values in original source pixels). A straightforward Pillow crop is enough; don't spend the lesson budget restoring the scan.

## Generation and validation limits

`render_lessons.py --from N --to M` reads verified JSON; it does **not** transcribe scans, perform OCR, query an LLM or generate images. The skill guides Codex through the source-to-JSON work; the script automates repeated HTML and checks.

`--check` checks schema invariants, question totals, local links/assets, IDs, labels, JS hooks and byte-for-byte agreement with generated HTML without writing. It cannot prove the transcription is faithful: visually check source coverage before marking verified. Future supported block types may be added as needed without changing existing question IDs.

After appending another range, `sync_navigation.py` connects it to the previous page. Re-rendering an earlier range computes navigation from all currently available HTML pages. Missing next lessons remain disabled; lesson 144 has no next-lesson link.
