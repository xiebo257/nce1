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

The default output is 768×512, 4 steps. Simple object slots can set
`illustration_width: 512` and `illustration_height: 384` to reduce generation
time while retaining enough detail for their displayed size. Keep larger scene
and cast images where faces and interactions need detail. Dimensions are part
of the resume fingerprint and are checked before publishing. The first measured cast image took 29.56 s
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

## Preserve picture-based teaching cues

Even lessons may use `illustration_source_reference` to colorize a verified source
crop with the local edit model. Preserve the crop in `illustrations/references/source/`,
record source coordinates, and include its SHA256 in the generation specification.
Inspect all panels: a source crop may omit the bottom row. Rebuild it from the
complete scan before generating. Model colorization still requires visual review.
For exact clock diagrams, `illustration_exact_diagram` preserves every original
hand and numeral using deterministic ink/background colorization; record origin
`local-diagram` and no model attribution. Do not describe these as model generated.

## Batch source-panel colorization

For even lessons with verified source references, `colorize_lesson_panels.py`
combines one lesson's panels into a shared reference sheet, uses one local model
pass, then splits candidates back into the original slots. It skips exact clock
diagrams and lessons without source references. Start with one lesson and inspect
both the full sheet and split candidates before running a range:

```sh
~/.local/share/nce1-imagegen/bin/python \
  skills/nce1-lesson-html/scripts/colorize_lesson_panels.py --from 52 --to 52
```

Use the optional lesson-level `illustration_palette` to give repeated characters
explicit clothing/hair colors. A generic consistency instruction alone allowed
one boy's shirt to change across panels. Inspect color consistency, panel order,
crop boundaries, counts and exact teaching cues. Remove stray text fragments
outside illustration borders; preserve meaningful labels inside pictures.
Long horizontal source strips need wide cells rather than tiny square thumbnails.
Shared-sheet generation metadata records the actual prompt, input/output hashes,
settings and per-slot split coordinates. When publishing, preserve the exact
source and colored sheet plus metadata under `illustrations/references/atlas/`.
Resume checks include the atlas recipe and palette as well as source hashes.

MFLUX `GeneratedImage.save()` defaults to `overwrite=False`: when regenerating,
it can silently save `colored_1.png` while a later split still reads the old
`colored.png`. The atlas runner must explicitly use `overwrite=True` and check
the saved dimensions. Validate the PNG's embedded prompt against the generation
record as well as its hash. `audit_published_illustrations.py --baseline REV`
checks all published assets and excluded sections; it complements visual review.

Use complete source pages: older `ready` crops can omit the final row. Detecting
rectangular frames is only a starting point; inspect the extracted sheet because
a shifted crop can still truncate a figure or reorder adjacent panels. Match
new images to the actual Lesson text; where old text disagrees with a scan,
verify the specific fact before changing it. Do not silently replace a lesson's
exercise content merely to fit a source illustration.

Do not assume a clean PDF is more accurate than the photographed book. The local
Lesson 122 PDF repeats picture 5 at position 6; the photograph correctly shows
road workers. Lessons 142/144 have faded PDF linework that the photographs can
restore. For photographed frames, perspective rectification removes sloping
caption fragments without cutting people or objects. Inspect numbered order
after frame detection: small differences in top edges put Lesson 124's kitten
before its book pictures when sorting boxes by raw y coordinates.

When a model changes a teaching action (for example turning sleeping children
into doctors), `preserve_panel_lineart.py --lesson N` can transfer model colors
into the source drawing's closed regions. It retains the source geometry, count,
clock hands and labels, and records the model color guide and source hashes.
Inspect the result: open outlines can merge face and hair regions; a color guide
can also give food the wrong hue. Use targeted region/color corrections only
after seeing the defect. Keep the untouched model sheet for provenance and
publish the final corrected candidates. This is model-assisted source
colorization, not a wholly model-redrawn scene. `--region SLOT:X:Y:COLOR`
selects a source region by a point in the split tile. A point on ink is rejected.

## Redraw blurred published pictures

When the user asks for clearer new artwork, source-ink color transfer retains
the coarse scan edges and is insufficient. Inspect the native pixel dimensions:
a 100–256px atlas tile becomes visibly blurred when enlarged in the page.
Generate at least twice the intended CSS width (the current individual redraw
workflow uses 512×320 output, displayed at 256px). Upsizing the old crop does not
count as a newly generated high-resolution picture.

The local 4B model followed single-picture redraw prompts more reliably than
four-picture prompts in the Lesson 52 trial. Keep each prompt short and describe
only people and objects in that picture. A generic reference to clocks, thought
bubbles or a cast member absent from the scene caused unwanted objects and
duplicate panels. Preserve hair/clothing with scene-specific constraints and
visually compare repeated people. A shared seed does not ensure identity.
For pure object pictures, omit generic face/person instructions altogether:
they caused faces on bread and bottles in the Lesson 60 trial. Describe raw
chicken as food rather than merely "a chicken", and verify labels instead of
accepting plausible-looking lettering.

For a before/after pair with the same people, an inspected clean first scene
can be the edit reference for the second. Change only the relevant object or
action, retaining the cast; independently redrawing both old source tiles can
change hair and clothes. If an edit must remove a person, verify the entire
body disappeared: one local trial removed only the head. Correct small clock
insets with photograph-verified diagram overlays, recording the operation via
`refine_redraw_candidates.py`, rather than trusting diffusion-generated hands.

`redraw_even_illustrations.py` maintains the 52–144 even-lesson redraw queue in
`reports/even-illustration-redraw/plan.json`. The plan records the original image
and photograph hashes. `generate --lessons ...` keeps one local model resident
and resumes matching candidates; `review --lessons ... --notes ...` records an
actual visual inspection against candidate hashes; `publish --lessons ...`
replaces only the referenced image metadata and renders HTML. Review is an agent
inspection step, not a user permission gate. Reusing artwork requires matching
the teaching action, count and relevant props, not merely similar file hashes.
Do not recreate an existing plan from already-redrawn outputs, and do not rerun
the earlier baseline-based photo-layout repair over these new assets.

Exact instructional clocks use the `diagrams` command with photograph-verified
times. If a photographed reading is ambiguous, keep that uncertainty explicit;
do not have a diffusion model invent a cleaner-looking time. Verify both source
coverage and browser pixel sizing before claiming a batch is complete.
