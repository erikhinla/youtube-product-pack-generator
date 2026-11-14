#!/usr/bin/env python3
"""RevAnew pipeline: one YouTube video -> full digital asset pack.

Stages: fetch -> analyze -> generate -> package   (publish is manual by policy)

Usage:
  python3 pipeline.py <youtube-url> [--slug NAME] [--mock] [--only blog,email,...]

Keys come from .env next to this file or the environment (see .env.example).
--mock runs the whole flow with placeholder text so you can verify plumbing
without spending tokens.
"""
import argparse
import datetime as dt
import json
import os
import re
import shutil
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent          # repo root
PROD = ROOT / "03_PRODUCTION"

# name -> (filename, what the LLM should produce)
ASSET_DEFS = {
    "blog":        ("blog-post.md",            "Long-form blog post (800-1200 words) with H2/H3 structure, faithful to the video's frameworks."),
    "ebook":       ("ebook.md", "Short ebook (1500-2500 words): first line 'TITLE: <book title>', second line 'SUBTITLE: <one line>', then chapters each starting with '## Chapter N: <name>', every chapter ends with an 'ACTION STEP:' line."),
    "email":       ("email-sequence.md",       "5-email nurture sequence. Each email: subject, preview text, body (150-250 words), single CTA."),
    "social":      ("social-clips.md",         "5 short-form video scripts (30-60s each): hook line, beats, on-screen text suggestions, CTA."),
    "landing":     ("landing-page.html",       "Single-file landing page, HTML + inline CSS, dark background, sells the pack at the analyzed price. No stock images, no fake testimonials. Copy only from the analyzed frameworks."),
    "avatar":      ("market-avatar-worksheet.md", "Market avatar worksheet: 8 sections. Each section starts with '## Section name' then 2-4 prompt questions as lines starting with '- '. This becomes a fill-in printable worksheet."),
    "blueprint":   ("messaging-blueprint.md",  "Messaging blueprint: audience, pain, promise, proof points, voice notes, offer ladder."),
    "flashcards":  ("framework-flashcards.md", "Framework flashcards, EXACTLY this structure, 12 cards: each card starts with '### Card N' on its own line, next line starts with 'Q: ' (the question), following lines are the answer as plain text."),
    "audio":       ("audio-overview-script.md", "Script for a 5-minute audio overview of the pack, spoken-word style, no music cues needed."),
    "checklist":   ("implementation-checklist.md", "One-page implementation checklist a buyer can tick off in order."),
}


def log(msg: str):
    print(f"[revanew] {msg}", flush=True)


def load_env():
    envf = HERE / ".env"
    if envf.exists():
        for line in envf.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                import os
                os.environ.setdefault(k.strip(), v.strip())


def slugify(url_or_name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", url_or_name.lower()).strip("-")
    return s[:50] or "revanew-pack"


EMOJI_RE = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27BF\U0001F170-\U0001F178\uFE0F]+")


def sanitize(text: str, is_html: bool) -> str:
    """Final-file hygiene: strip LLM preamble chatter, code fences, emoji markers."""
    t = text.strip()
    t = re.sub(r"^```[a-zA-Z]*\n", "", t)
    t = re.sub(r"\n```\s*$", "", t)
    if is_html:
        low = t.lower()
        i = low.find("<!doctype")
        if i == -1:
            i = low.find("<html")
        if i != -1:
            t = t[i:]
        k = t.lower().rfind("</html>")
        if k != -1:
            t = t[: k + 7]
    else:
        lines = t.splitlines()
        for n, l in enumerate(lines):
            s = l.strip()
            if s.startswith("# ") or s.startswith("## ") or s.startswith("TITLE:"):
                t = "\n".join(lines[n:])
                break
    return EMOJI_RE.sub("", t).strip() + "\n"


# ---------- stages ----------

def stage_fetch(url: str, outdir: Path, mock: bool, transcript_file: str = "") -> str:
    tp = outdir / "transcript.txt"
    if transcript_file:
        text = Path(transcript_file).read_text(errors="ignore")
        log(f"manual transcript: {len(text)} chars from {transcript_file}")
    elif mock:
        text = "MOCK TRANSCRIPT: In this video we cover the three-step framework for automating at scale. Step one: capture. Step two: package. Step three: liquidate the ad cost with a self-liquidating offer. " * 10
    else:
        sys.path.insert(0, str(HERE))
        from transcript import fetch_transcript
        text = fetch_transcript(url)
    tp.write_text(text)
    log(f"transcript: {len(text)} chars -> {tp}")
    return text


def stage_analyze(text: str, outdir: Path, mock: bool) -> dict:
    board = outdir / "concept-board.json"
    if mock:
        cb = {
            "video_summary": "Three-step framework to turn one video into a sellable asset ecosystem.",
            "core_frameworks": ["Capture", "Package", "Self-Liquidate"],
            "suggested_price": "$27",
            "target_audience": "Creators with an audience but no product shelf",
            "artifacts": [{"asset_name": k} for k in list(ASSET_DEFS)],
        }
    else:
        from llm import complete_json
        cb = complete_json(
            system="You are the RevAnew Engine. You extract the core frameworks from a creator's video transcript and design a sellable digital product ecosystem around them.",
            user=(
                "From this transcript return JSON: {video_summary, core_frameworks[], "
                "suggested_price, target_audience, voice_notes}. Transcript:\n" + text[:20000]
            ),
        )
    board.write_text(json.dumps(cb, indent=2))
    log(f"concept board -> {board}")
    return cb


def stage_generate(cb: dict, text: str, outdir: Path, only: list, mock: bool):
    pack = outdir / "pack"
    pack.mkdir(exist_ok=True)
    for key in only:
        fname, brief = ASSET_DEFS[key]
        dest = pack / fname
        if dest.exists() and dest.stat().st_size > 200:
            log(f"{key}: exists, skipping (delete to regenerate)")
            continue
        if mock:
            dest.write_text(f"# {fname}\n\nMOCK ASSET for {key}. Frameworks: {', '.join(cb['core_frameworks'])}. Price: {cb['suggested_price']}.\n\n" + "Filler paragraph for plumbing test. " * 10)
        else:
            from llm import complete
            raw = complete(
                system=(
                    "You are the RevAnew asset generator. Write in the creator's voice as described. "
                    "Use ONLY ideas grounded in the transcript. No invented statistics, no fake testimonials, "
                    "no made-up numbers. Do not use em dashes. "
                    "Output ONLY the file content: no preamble, no meta commentary, no code fences, no emojis.\n"
                    f"Concept board: {json.dumps(cb)}\n"
                ),
                user=f"Produce this asset: {brief}\n\nSource transcript:\n{text[:30000]}",
                max_tokens=12000,
            )
            dest.write_text(sanitize(raw, fname.endswith(".html")))
        log(f"{key}: {len(dest.read_text())} chars -> {dest}")


def stage_compile(outdir: Path):
    """Compile every pack asset to a final PDF in pack/pdf/ (markdown = source, PDF = product)."""
    pack = outdir / "pack"
    pdfdir = pack / "pdf"
    pdfdir.mkdir(exist_ok=True)
    sys.path.insert(0, str(HERE))
    from pdf_compile import compile_pdf
    from deliverables import cards_pdf, worksheet_pdf, ebook_pdf
    designed = {"framework-flashcards.md": cards_pdf,
                "market-avatar-worksheet.md": worksheet_pdf}
    n = 0
    for p in sorted(pack.iterdir()):
        if p.suffix not in (".md", ".html") or not p.is_file():
            continue
        title = p.stem.replace("-", " ").replace("_", " ").title()
        dest = pdfdir / (p.stem + ".pdf")
        made = False
        if p.name in designed:
            made = designed[p.name](p.read_text(), str(dest))
        elif p.name == "ebook.md":
            made = ebook_pdf(p.read_text(), str(dest), price=cb_price(outdir))
        if not made:
            dest.write_bytes(compile_pdf(title, p.read_text(), is_html=p.suffix == ".html"))
        log(f"pdf: {dest.name} ({dest.stat().st_size} bytes){' [designed]' if made else ''}")
        n += 1
    log(f"compiled {n} PDFs -> {pdfdir}")


def cb_price(outdir: Path) -> str:
    try:
        import json as _json
        return _json.loads((outdir / "concept-board.json").read_text()).get("suggested_price", "")
    except Exception:
        return ""


def stage_package(outdir: Path, slug: str):
    zip_path = outdir.parent / f"{slug}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted((outdir / "pack").rglob("*")):
            if p.is_file():
                z.write(p, p.relative_to(outdir))
    log(f"zip -> {zip_path} ({zip_path.stat().st_size} bytes)")
    return zip_path


GWS = "/root/.venv/gws/bin/python /root/.hermes/skills/productivity/google-workspace/scripts/google_api.py"


def stage_drive(zip_path: Path, outdir: Path, slug: str):
    """Upload zip + individual pack files to the RevAnew Drive folder. Non-fatal."""
    folder = os.environ.get("REVANEW_DRIVE_FOLDER", "")
    if not folder:
        log("REVANEW_DRIVE_FOLDER not set; skipping Drive upload (files stay in 03_PRODUCTION)")
        return
    import subprocess
    targets = [zip_path] + sorted((outdir / "pack" / "pdf").glob("*.pdf"))
    for p in targets:
        if not p.exists():
            continue
        name = f"{slug} - {p.name}" if p != zip_path else p.name
        cmd = GWS.split() + ["drive", "upload", str(p), "--parent", folder, "--name", name]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            ok = '"status": "uploaded"' in r.stdout
            log(f"drive {'UPLOADED' if ok else 'FAILED'}: {name}" + ("" if ok else f" :: {r.stdout[-200:]}{r.stderr[-200:]}"))
        except Exception as e:
            log(f"drive upload error for {name}: {e}")
    log(f"Drive folder: https://drive.google.com/drive/folders/{folder}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url", nargs="?", default="manual")
    ap.add_argument("--slug")
    ap.add_argument("--transcript-file", default="", help="path to a .txt you pasted from YouTube's transcript panel")
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--only", default=",".join(ASSET_DEFS))
    ap.add_argument("--force-new", action="store_true", help="reuse nothing, new run dir")
    args = ap.parse_args()
    load_env()

    base = slugify(args.slug or args.url)
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    run = PROD / f"{base}-{stamp}"
    if args.force_new or not run.exists():
        run.mkdir(parents=True)
    outdir = run

    only = [k.strip() for k in args.only.split(",") if k.strip()]
    bad = [k for k in only if k not in ASSET_DEFS]
    if bad:
        sys.exit(f"unknown asset keys: {bad}. valid: {list(ASSET_DEFS)}")

    text = stage_fetch(args.url, outdir, args.mock, args.transcript_file)
    cb = stage_analyze(text, outdir, args.mock)
    stage_generate(cb, text, outdir, only, args.mock)
    stage_compile(outdir)
    stage_package(outdir, f"{base}-{stamp}")
    stage_drive(PROD / f"{base}-{stamp}.zip", outdir, f"{base}-{stamp}")
    log(f"DONE. Pack at {outdir}")
    log("Publish is manual: review the pack, then load storefront/social drafts yourself.")


if __name__ == "__main__":
    main()
