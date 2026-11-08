# Color lesson illustrations

The illustration source is `lessons/lesson-NNN.json`. Color artwork is added
only to the narrative/dialogue section of odd lessons 45–143. Practice and
grammar are excluded. Existing color artwork through Lesson 44 is preserved.

This batch has 50 lessons and 127 lesson image slots. A slot is complete only
when its canonical `status` is `ready` with `origin: local-model`. Candidate
images under ignored `work/` are not published artwork.

## Local model

Test machine: Apple M4 MacBook Air, 16 GB unified memory, 8 GPU cores.

| Model | Local suitability | Status |
| --- | --- | --- |
| FLUX.2 Klein 4B, MLX 4-bit | About 4.62 GB of files; 4 steps; text generation and reference editing | Downloaded from ModelScope, all files SHA256 verified, local inference tested |
| Z-Image Turbo 6B | Supported by MFLUX; 9 steps; alternative for text-to-image quality | Researched only, not downloaded or benchmarked |
| Anima 2B | Supported by MFLUX; illustration/anime-oriented alternative | Researched only, not downloaded or benchmarked |

Weights: [Chinese ModelScope mirror](https://modelscope.cn/models/mlx-community/FLUX.2-Klein-4B-4bit).
Weights and the Python environment stay outside Git. No remote image-generation
API or credential file is used. The initial 768×512 cast image took 29.56 s with
4.98 GB peak MLX allocation. A scene using a full cast reference took 49.11 s;
a scene with individual character crops took 42.17 s. MLX allocation is not total
system memory, and sustained speed varies by scene and thermal conditions.

## Character consistency and review

Each lesson has explicit hair, age and clothing designs. Later cast sheets use
one separate head-and-shoulders portrait per panel, visually checked before any
scene generation. Repeated scenes use these portraits as references for only the people
appearing in that scene. This prevents an absent character from being copied
into the scene as easily. It improves consistency but is not a guarantee: every
lesson still needs visual review. An early Lesson 45 candidate confused Bob and
Pamela; it was rejected and regenerated using individual references.

Final WebP artwork lives in `html/assets/lesson-NNN/`. Cast references live in
`illustrations/references/`. Per-image manifests record the exact prompt, seed,
reference hash, dimensions, timings, file hashes and actual review notes.
Illustrative appearance choices are distinguished from facts stated in the
textbook. Image metadata preserves the original source description separately
from the selected scene and accessible alt text.

See the [local illustration workflow](../skills/nce1-lesson-html/references/local-illustrations.md)
for verified mirror downloads, generation, resumption and publishing commands.
