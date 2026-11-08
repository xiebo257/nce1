# Local color lesson illustrations

Use this workflow when the user asks to add generated lesson artwork. Canonical
content is `lessons/lesson-NNN.json`; only images referenced by
`sections.lesson` are in scope. A pending practice image (for example Lesson 61)
must not accidentally enter the generation queue. Scope includes BOTH odd and even
lessons 45–144. Even lessons have picture-based Lesson content; do not confuse
that with the separate Practice tab. Existing `ready` textbook crops are not
generated color artwork. Preserve the original source scans and old crops.
Use `--parity odd` or `--parity even` only to schedule a batch, never to redefine
the requested scope. Prepare scene prompts from each Lesson block before running
a batch. For clock times, counts, comparisons and before/after scenes, verify
the exact teaching cue; a plausible decorative scene is insufficient.

## Hardware and model

The current machine is an Apple M4 MacBook Air with 16 GB unified memory.
`mflux==0.24.0` provides MLX/Metal inference. The first selected model is
`mlx-community/FLUX.2-Klein-4B-4bit`: 4 distilled steps, approximately 4.62 GB of
repository files, native image-reference editing as well as text-to-image.
Other candidates include Z-Image Turbo 6B (9 steps) and Anima 2B (illustration
style). They are alternatives, not locally validated models unless a separate
benchmark says so. Large 9B/20B models are less suitable for this machine.

Prefer the Chinese mirror:
https://modelscope.cn/models/mlx-community/FLUX.2-Klein-4B-4bit

Keep weights outside Git, at
`~/.cache/nce1-models/FLUX.2-Klein-4B-4bit`. Mirror downloads must preserve the
model's subdirectory names. Verify file sizes and SHA256 against the mirror's
file inventory. A partially downloaded or sparse `.part` file is not a complete
model. Downloads may resume by byte ranges only when the server returns the
exact requested `Content-Range`. Do not switch to an overseas host silently.

The isolated environment is `~/.local/share/nce1-imagegen`. To recreate:

```sh
python3.11 -m venv ~/.local/share/nce1-imagegen
~/.local/share/nce1-imagegen/bin/pip install \
  --index-url https://pypi.tuna.tsinghua.edu.cn/simple 'mflux==0.24.0'
```

Download or verify the pinned files (resumes completed ranges):

```sh
python3 skills/nce1-lesson-html/scripts/download_image_model.py
```

The checked file inventory is in `assets/flux2-klein-4b-model.json`. It records
actual mirror SHA256 values; a changed upstream file requires an explicit
inventory review rather than accepting a mismatched model.

No API key, Codex credentials or audio processing tools are needed. The runner
sets Hugging Face and Transformers offline mode after downloading the model.

## Plan from the actual text

For each lesson:

- Read the dialogue/narrative attached to each image slot. Existing image
  descriptions can contain mistakes or an entire multi-panel storyboard.
- Put fixed visual traits in `characters.*.illustration_appearance`: age range,
  face/hair, clothing colors, distinguishing props. Added appearance choices
  are illustrative, not claims about original textbook facts.
- Put the selected coherent moment in `images.*.illustration_scene`, with only
  the characters present in that scene listed in `characters`.
- Store a consistent color rendering style in `illustration_style`. Match the
  existing warm realistic color illustrations unless the user chooses another
  style. Use no speech balloons or incidental captions.
- Follow explicit source details: blue coat versus dress, who speaks or
  impersonates whom, where people sit, which object is exchanged. If source
  content conflicts, check the scan before producing an image. Do not infer
  story facts from a stale image prompt.

`illustration_inventory.py` audits both parities using provenance and file existence;
`ready` alone is insufficient. `--json` writes machine-readable progress. Lessons
with no Lesson image slots are reported explicitly, not counted as complete.

`illustrate_lessons.py plan` produces the queue without loading the model.
Multiple scenes use a cast reference image, conditioned through
`Flux2KleinEdit.image_paths`. The same seed alone does not preserve identity.
Prefer `illustration_cast_layout: portrait-strip`: one head-and-shoulders portrait
per equal-width panel, in the recorded order. Keep poses and scene actions out
of `illustration_appearance`; describing a child lying in bed caused extra
children and furniture in an early reference sheet.

The cast sheet is cropped into individual reference images for only the people
appearing in that scene, in the recorded left-to-right cast order. Inspect that
the cast sheet actually follows this order and that crops contain the correct
faces. Passing the entire cast into a two-person scene can substitute an absent
character, as the first Lesson 45 trial demonstrated. Scenes without recurring
people do not need reference conditioning. Single
image lessons use the fixed character descriptions directly.

## Generate, inspect, publish

```sh
python3 skills/nce1-lesson-html/scripts/illustrate_lessons.py plan \
  --from 45 --to 49
~/.local/share/nce1-imagegen/bin/python \
  skills/nce1-lesson-html/scripts/illustrate_lessons.py generate \
  --from 45 --to 49
```

The initial output is 768×512, 4 steps. The first measured cast image took 29.56 s
with 4.98 GB peak MLX allocation; the first reference scene took 49.11 s with
5.24 GB. These are initial samples, not a throughput guarantee. Measure actual generation duration and
MLX peak allocation on this machine; don't extrapolate CPU RAM from MLX alone.
Only one GPU generation process should run at a time. Candidates live under
ignored `illustrations/work/candidates/`. One active model serves the queue. Reuse it while the inference mode is unchanged;
switch between `Flux2Klein` for text-only images and `Flux2KleinEdit` for reference
images. In MFLUX 0.24.0 the edit class fails when `image_paths` is absent, so do
not use it for plain text-to-image. Release the previous model before switching.
Generation pauses before using a newly generated cast until its hash has a
visual approval record. Inspect the portrait count, identities, order and crop
boundaries, then run (this is the agent recording its inspection, not a request
for user permission):

```sh
~/.local/share/nce1-imagegen/bin/python \
  skills/nce1-lesson-html/scripts/illustrate_lessons.py approve-reference \
  --from 61 --to 61 --review-notes 'Record the observed cast count and order.'
```

Resume `generate` for the remaining range. Unchanged completed candidates are skipped using prompt/settings/reference and
file hashes; failures leave completed work available for resumption.

Inspect every lesson's full-size images or sufficiently detailed contact
sheets. Check scene accuracy, character count, face/hair/clothes, hands, props,
spatial relationships and unintended text. Compare all scenes with the cast
reference. Regenerate individual faulty scenes by adjusting the canonical scene
prompt. Do not publish uninspected output merely because inference succeeded.

After inspecting all candidates for a lesson, record concrete review notes:

```sh
~/.local/share/nce1-imagegen/bin/python \
  skills/nce1-lesson-html/scripts/illustrate_lessons.py publish \
  --from 45 --to 45 --review-notes 'Describe the actual visual checks and any limitations.'
python3 skills/nce1-lesson-html/scripts/render_lessons.py --repo . --from 45 --to 45
python3 skills/nce1-lesson-html/scripts/render_lessons.py --repo . --from 45 --to 45 --check
```

Published WebP images go to `html/assets/lesson-NNN/`, cast references to
`illustrations/references/`, reproducibility/review manifests to
`illustrations/manifests/`. The canonical slot becomes `ready` only at publish.
Render from JSON instead of editing generated HTML. Verify the practice and
grammar sections remain unchanged. Check representative desktop/mobile layouts
if a browser is available. Commit/push in small batches when session-authorized,
including the actual image assets, while preserving unrelated staged changes.

## Lessons from local trials

Use concise scene-first prompts (`illustration_prompt_version: 2`). State the
actual number and roles of people. Do not add generic “interaction” or unrelated
“two telephone locations” instructions to solitary scenes. Specify purchased
objects explicitly: a vague “finished purchase” became groceries in a stationery
shop. Use separate visual designs for incidental friends so the reference
character is not cloned.

Images with wrong people or core actions need regeneration. A clean crop may
remove an unrelated edge artifact while preserving the intended scene; inspect
the crop afterward. Record crop bounds, source hash and final `output_size` in
manifest `postprocess`, and preserve aspect ratio. Publishing uses the actual
postprocessed size. Do not accept an inaccurate teaching diagram, wrong clock
time, or large invented shop lettering as correct source content.

If the scene is otherwise correct, the same local model can edit a candidate to
remove a duplicate person or speech balloon while preserving the correct faces:

```sh
~/.local/share/nce1-imagegen/bin/python \
  skills/nce1-lesson-html/scripts/edit_illustration.py \
  --lesson 63 --slot lesson-063-scene-02 --seed 630222 \
  --instruction 'Remove the speech bubble and its text; preserve the boy, doctor, faces, clothing and room.'
```

Run one GPU process at a time. The editor preserves the original in ignored
`work/originals/`, records the edit instruction/seed/input and output hashes, and
leaves the result a candidate. Inspect the edited image before publishing; an
inference success is not a visual approval. For portrait strips, use
`illustration_reference_crop: panel` to trim white margins from each portrait:
otherwise dividers can be copied into a scene. Put the main subject first in a
scene's character references (for example the sick child before his parents).

Published cast references include the original `NNN-cast-source.png` as well as
the display WebP, so the exact model-conditioning pixels and file hash are kept.
