# RevAnew / youtube-product-pack-generator

One YouTube video in, a sellable digital asset pack out. Two lanes share one transcript.

## Lane A: asset pack (text + page products)
`02_AUTOMATION/revanew_pipeline/pipeline.py` — fetch -> analyze -> generate -> package.
Produces: blog post, ebook, 5-email sequence, 5 social clip scripts, landing page,
market avatar worksheet, messaging blueprint, flashcards, audio overview script,
implementation checklist. Output lands in `03_PRODUCTION/<slug>-<timestamp>/`.

```bash
cd 02_AUTOMATION/revanew_pipeline
cp .env.example .env        # fill keys over SSH; never paste keys in chat
python3 pipeline.py "https://www.youtube.com/watch?v=VIDEOID" --mock   # plumbing test, no tokens
python3 pipeline.py "https://www.youtube.com/watch?v=VIDEOID"          # real run
python3 pipeline.py URL --only blog,email,landing                      # subset
```

LLM backend: Anthropic-compatible. Either `ANTHROPIC_API_KEY` direct or
`ANTHROPIC_AUTH_TOKEN` + `ANTHROPIC_BASE_URL` for the Abliterated proxy.

## Lane B: Blender videos (Claude writes bpy, Blender renders)
Claude generates Python (bpy) scripts; headless Blender renders them to MP4 with ffmpeg.
Install with `01_SCRIPTS/install-blender.sh`. Verified working on this VPS with Cycles CPU.

## Rules
- Publish is manual. This repo generates drafts; nothing auto-posts.
- No invented stats or testimonials in any asset (enforced in the generator prompts).
- `.env` and `03_PRODUCTION/` are gitignored.

## History
`legacy/revanew_engine.py` is the original Streamlit GPT-4 concept stub (Oct 2026),
kept for reference. The pipeline replaces it and no longer needs OpenAI or Streamlit.
