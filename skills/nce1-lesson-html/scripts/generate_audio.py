#!/usr/bin/env python3
"""Generate TTS audio (macOS `say` + Samantha) for NCE1 lessons with SRT subtitles.

Usage:
    python3 generate_audio.py --lesson 143
    python3 generate_audio.py --lesson 143 --lesson 144
    python3 generate_audio.py --range 45-144
    python3 generate_audio.py --range 45-144 --output /path/to/dir

For each lesson, produces:
    audio/lesson-NNN.mp3   — concatenated audio
    audio/lesson-NNN.srt   — subtitle file aligned to audio

Audio is generated with macOS `say` (Samantha, en_US) at 155 wpm.
Multi-choice answers ("A / B") are expanded into separate sentences.
"""
import argparse
import json
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

SAY_VOICE = "Samantha"
RATE = 155
MP3_BITRATE = "48k"
GAP_S = 0.5  # silence gap between subtitle lines


def tts_batch(lines: list[str], out_aiff: Path) -> float:
    """Generate AIFF for a list of lines using `say -f`. Returns duration."""
    txt = out_aiff.with_suffix(".txt")
    txt.write_text("\n".join(lines), encoding="utf-8")
    subprocess.run(
        ["say", "-v", SAY_VOICE, "-r", str(RATE), "-f", str(txt), "-o", str(out_aiff)],
        check=True, capture_output=True,
    )
    txt.unlink(missing_ok=True)
    r = subprocess.run(["afinfo", str(out_aiff)], capture_output=True, text=True)
    m = re.search(r"estimated duration: ([\d.]+) sec", r.stdout)
    return float(m.group(1)) if m else 0.0


def make_silence(out_aiff: Path, duration: float) -> None:
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=22050:cl=mono",
         "-t", str(duration), "-codec:a", "pcm_s16le", "-ar", "22050", str(out_aiff)],
        check=True, capture_output=True,
    )


def concat_mp3(parts: list[Path], out_mp3: Path) -> None:
    """Concatenate AIFF/MP3 files into one MP3 using ffmpeg concat demuxer."""
    lst = out_mp3.with_suffix(".txt")
    lst.write_text("".join(f"file '{p}'\n" for p in parts), encoding="utf-8")
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
         "-codec:a", "libmp3lame", "-b:a", MP3_BITRATE, str(out_mp3)],
        check=True, capture_output=True,
    )
    lst.unlink(missing_ok=True)


def expand_answer(answer: str) -> list[str]:
    """Expand multi-choice answers into separate spoken sentences.

    'They've / They have already been emptied.' → ['They have already been emptied.']
    'No. It hasn't been repaired yet. / It has already been repaired.' → 2 sentences
    'They have already been put there/on the shelf.' → ['They have already been put there.']
    'No, not yet, but I/we will be served soon.' → ['No, not yet, but I will be served soon.']
    """
    answer = answer.strip()
    if "/" not in answer:
        return [answer]

    parts = re.split(r"\s*/\s*", answer)
    if len(parts) < 2:
        return [answer]

    # Full-sentence alternatives: both parts start with capital/quote → speak all
    if all(re.match(r"^[A-Z'\"]", p.strip()) for p in parts if p.strip()):
        return [p.strip() for p in parts if p.strip()]

    # Two-part: left / right
    left, right = parts[0].strip(), parts[1].strip()

    # left ends with period → two separate sentences
    # e.g. "No. It hasn't been repaired yet. / It has already been repaired."
    if left.endswith("."):
        return [left, right if right.endswith(".") else right + "."]

    # left is a short contraction/word, right is a full alternative
    # e.g. "They've / They have already been emptied." → prefer "They have..."
    #      "It will / It'll be done soon." → prefer "It will be done soon."
    if right[0].isupper():
        # Both are full alternatives → pick the longer (more formal/natural)
        return [right if len(right) >= len(left) else left]

    # right continues left (lowercase): inline substitution
    # e.g. "I/we will be served soon." → "I will be served soon."
    #      "there/on the shelf." → "there."
    # Pick the first (left) variant, which is the shorter/more natural one
    return [left + ("." if right.endswith(".") else "")]


def strip_chinese(text: str) -> str:
    """Remove Chinese characters and fullwidth punctuation."""
    text = re.sub(r"[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]+", "", text)
    text = re.sub(r"\s{2,}", " ", text).strip()
    return text


def split_sentences(text: str) -> list[str]:
    """Split text into individual sentences."""
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z\"'(])", text)
    return [p.strip() for p in parts if p.strip()]


def build_script(lesson_data: dict) -> list[dict]:
    """Build list of {text, subtitle} items from lesson JSON."""
    items = []

    def add(text, subtitle, section=""):
        text = text.strip()
        if text:
            items.append({"text": text, "subtitle": subtitle or text, "section": section})

    for sec_name in ("lesson", "practice", "grammar"):
        for blk in lesson_data["sections"].get(sec_name, []):
            btype = blk["type"]
            btitle = blk.get("title", "")

            if btype == "text":
                en = strip_chinese(blk["text"])
                add(en, en, btype)

            elif btype == "vocabulary":
                for it in blk["items"]:
                    add(it["word"], it["word"], "vocabulary")

            elif btype == "notes":
                for it in blk["items"]:
                    en = strip_chinese(it.get("text", ""))
                    add(en, en, "notes")

            elif btype == "exercise":
                for q in blk.get("questions", blk.get("items", [])):
                    prompt = q.get("prompt", "")
                    prompt = re.sub(r"^Picture \d+:\s*", "", prompt)
                    add(prompt, prompt, btitle)
                    for sent in expand_answer(q.get("answer", "")):
                        add(sent, sent, btitle)

    return items


def srt_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int(round((seconds - int(seconds)) * 1000))
    if ms >= 1000:
        ms = 999
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def generate_lesson_audio(lesson_num: int, output_dir: Path, repo_root: Path) -> Path | None:
    """Generate audio + SRT for one lesson."""
    lesson_path = repo_root / "lessons" / f"lesson-{lesson_num:03d}.json"
    if not lesson_path.exists():
        print(f"  SKIP: not found")
        return None

    lesson_data = json.loads(lesson_path.read_text())
    items = build_script(lesson_data)
    print(f"  {len(items)} subtitle lines")

    out_dir = output_dir / "audio"
    out_dir.mkdir(parents=True, exist_ok=True)
    mp3_path = out_dir / f"lesson-{lesson_num:03d}.mp3"
    srt_path = out_dir / f"lesson-{lesson_num:03d}.srt"

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        silence = tmp / "silence.aiff"
        make_silence(silence, GAP_S)

        # Group items into TTS chunks (max ~400 chars per chunk for say)
        chunks: list[list[int]] = []  # each chunk = list of item indices
        cur: list[int] = []
        cur_len = 0
        for i, item in enumerate(items):
            line_len = len(item["text"])
            if cur and cur_len + line_len > 400:
                chunks.append(cur)
                cur, cur_len = [], 0
            cur.append(i)
            cur_len += line_len + 1  # newline
        if cur:
            chunks.append(cur)

        print(f"  {len(chunks)} TTS chunks")

        # Generate each chunk
        chunk_aiffs = []
        chunk_durations = []
        for ci, chunk in enumerate(chunks):
            lines = [items[i]["text"] for i in chunk]
            aiff = tmp / f"chunk_{ci:03d}.aiff"
            t0 = time.time()
            dur = tts_batch(lines, aiff)
            chunk_aiffs.append(aiff)
            chunk_durations.append(dur)
            if ci % 10 == 0:
                print(f"    chunk {ci}/{len(chunks)} ({time.time()-t0:.1f}s)")

        # Build concat list with silences between chunks
        concat_parts = []
        for ci, aiff in enumerate(chunk_aiffs):
            concat_parts.append(aiff)
            if ci < len(chunk_aiffs) - 1:
                concat_parts.append(silence)

        concat_mp3(concat_parts, mp3_path)

    # Build SRT: estimate per-item durations within chunks
    srt_entries = []
    t = 0.0
    for ci, chunk in enumerate(chunks):
        chunk_dur = chunk_durations[ci]
        # Proportional allocation by character count
        total_chars = sum(len(items[i]["text"]) for i in chunk) or 1
        for i in chunk:
            item_dur = chunk_dur * len(items[i]["text"]) / total_chars
            # Add gap for all but the very last item
            is_last = (ci == len(chunks) - 1 and i == chunk[-1])
            srt_entries.append((len(srt_entries) + 1, t, t + item_dur, items[i]["subtitle"]))
            t += item_dur + (0 if is_last else GAP_S)
        # Gap between chunks
        if ci < len(chunks) - 1:
            t += GAP_S

    with open(srt_path, "w", encoding="utf-8") as f:
        for idx, start, end, text in srt_entries:
            f.write(f"{idx}\n{srt_time(start)} --> {srt_time(end)}\n{text}\n\n")

    size_mb = mp3_path.stat().st_size / 1024 / 1024
    print(f"  → {mp3_path.name} ({size_mb:.1f} MB, {srt_path.name}: {len(srt_entries)} cues)")
    return mp3_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lesson", type=int, action="append", help="Lesson number(s)")
    parser.add_argument("--range", dest="rng", help="Range like 45-144")
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    args = parser.parse_args()

    repo = args.repo.resolve()
    lessons = list(args.lesson or [])
    if args.rng:
        a, b = args.rng.split("-")
        lessons.extend(range(int(a), int(b) + 1))
    if not lessons:
        parser.error("Specify --lesson or --range")

    output_dir = args.output or repo
    print(f"Audio: {len(lessons)} lesson(s) → {output_dir/'audio'}/")
    t0 = time.time()
    for n in lessons:
        print(f"Lesson {n}:")
        generate_lesson_audio(n, output_dir, repo)
    print(f"\nDone in {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
