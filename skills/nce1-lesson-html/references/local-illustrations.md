# Local color lesson illustrations

Use this workflow when the user asks to add generated lesson artwork. Canonical
content is `lessons/lesson-NNN.json`; only images referenced by
`sections.lesson` are in scope. A pending practice image (for example Lesson 61)
must not accidentally enter the generation queue. Lessons 45–143 have 50 odd
narrative lessons and 127 lesson image slots; Lesson 75's two old monochrome
crops also need replacement. Preserve the original source scans and old crops.

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

`illustrate_lessons.py plan` produces the queue without loading the model.
Multiple scenes use a cast reference image, conditioned through
`Flux2KleinEdit.image_paths`. The same seed alone does not preserve identity.
Scenes without recurring people do not need reference conditioning. Single
image lessons use the fixed character descriptions directly.

## Generate, inspect, publish

```sh
python3 skills/nce1-lesson-html/scripts/illustrate_lessons.py plan \
  --from 45 --to 49
~/.local/share/nce1-imagegen/bin/python \
  skills/nce1-lesson-html/scripts/illustrate_lessons.py generate \
  --from 45 --to 49
```

The initial output is 768×512, 4 steps. Measure actual generation duration and
MLX peak allocation on this machine; don't extrapolate CPU RAM from MLX alone.
Only one GPU generation process should run at a time. Candidates live under
ignored `illustrations/work/candidates/`. One loaded model serves the queue.
Unchanged completed candidates are skipped using prompt/settings/reference and
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
