# Source speech metadata

The grammar compiler optionally reads the canonical lesson JSON alongside rendered HTML. Keep the JSON and HTML synchronized before compiling.

- Question `audio_segments`: ordered completed turns, overriding generic exercise inference. Each segment automatically receives the question ID as `source_item`.
- Exercise block `audio_context`: ordered fixed material before questions, such as a printed conversation opening or diary table. Give each segment a distinct `source` ID so its coverage is reviewable.
- Segment fields: `text`, `role`, optional `pause` (seconds), `extra` (delivery guidance), `section`, and provenance flags such as `supplemental`. `pause` is the compiler input; rendered script output uses `pause_after`.
- Keep role labels, blank markers, item codes and alternative-answer slashes out of spoken `text`. Select one valid spoken answer while preserving printed alternatives in the HTML key.

```json
{
  "id": "grammar-ii",
  "audio_context": [
    {"text": "The bus arrived at seven.", "role": "narrator", "pause": 1.2, "source": "diary-opening"}
  ],
  "questions": [{
    "id": "grammar-ii-1",
    "prompt": "When did the bus arrive?",
    "answer": "It arrived at seven.",
    "audio_segments": [
      {"text": "When did the bus arrive?", "role": "prompt", "pause": 1.6},
      {"text": "It arrived at seven.", "role": "answer", "pause": 1.2}
    ]
  }]
}
```

The example omits unrelated required lesson/block fields. Long turns may split at sentence boundaries while retaining their source IDs. Speech metadata must be reviewed against the actual prompt and key; explicit turns are not proof of correctness by themselves.
