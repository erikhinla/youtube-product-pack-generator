"""Render a Claude-authored bpy script into an MP4.

Usage:
  python3 render.py script.py --out out.mp4 --frames 60 --res 1080x1080 [--engine CYCLES|BLENDER_WORKBENCH]

The bpy script must define setup(scene) and frame_apply(scene, frame), or just
mutate the scene at import time with keyframes baked in.
Simplest contract: script defines `build(scene)` once and `pose(scene, t)` per frame.
"""
import argparse
import subprocess
import sys
from pathlib import Path

RUNNER = Path(__file__).parent / "_runner.py"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script")
    ap.add_argument("--out", default="render.mp4")
    ap.add_argument("--frames", type=int, default=60)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--res", default="1080x1080")
    ap.add_argument("--engine", default="BLENDER_WORKBENCH", help="WORKBENCH is fast on CPU; CYCLES for final quality")
    args = ap.parse_args()

    w, h = args.res.split("x")
    frames_dir = Path(args.out).with_suffix("") .as_posix() + "_frames"
    Path(frames_dir).mkdir(exist_ok=True)
    cmd = [
        "blender", "--background", "--factory-startup",
        "--python", str(RUNNER), "--python-exit-code", "1", "--",
        args.script, args.out, frames_dir, str(args.frames), args.fps, w, h, args.engine,
    ]
    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
