"""Inside-Blender runner: reads args after '--', loads the authored script, renders frames, muxes to MP4."""
import bpy
import sys
import os
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
script_path, out_mp4, frames_dir, frames, fps, w, h, engine = argv
frames, fps, w, h = int(frames), int(fps), int(w), int(h)

scene = bpy.context.scene
scene.render.resolution_x = w
scene.render.resolution_y = h
scene.render.fps = fps
scene.frame_start = 1
scene.frame_end = frames
scene.render.engine = "CYCLES" if engine == "CYCLES" else "BLENDER_WORKBENCH"
if engine == "CYCLES":
    scene.cycles.device = "CPU"
    scene.cycles.samples = 32

# load and run the authored script
namespace = {"__name__": "__user_script__"}
with open(script_path) as f:
    code = compile(f.read(), script_path, "exec")
exec(code, namespace)

build = namespace.get("build")
pose = namespace.get("pose")
if build:
    build(scene)

scene.render.image_settings.file_format = "PNG"
scene.render.filepath = os.path.join(frames_dir, "frame_")
for i in range(1, frames + 1):
    scene.frame_set(i)
    if pose:
        t = (i - 1) / float(frames)
        pose(scene, t)
    scene.render.filepath = os.path.join(frames_dir, f"frame_{i:04d}.png")
    bpy.ops.render.render(write_still=True)
    print(f"rendered frame {i}/{frames}", flush=True)

# mux with ffmpeg
os.system(f'ffmpeg -y -framerate {fps} -i "{frames_dir}/frame_%04d.png" -pix_fmt yuv420p "{out_mp4}"')
print("DONE", out_mp4, flush=True)
