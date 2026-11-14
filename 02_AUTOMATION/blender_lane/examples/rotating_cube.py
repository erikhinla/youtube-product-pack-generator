"""Sample bpy script: rotating cube + camera move. Plumbing smoke test only, not brand creative."""
import bpy
import math


def build(scene):
    bpy.ops.mesh.primitive_cube_add(size=2)
    cube = bpy.context.object
    cube.name = "HeroCube"
    mat = bpy.data.materials.new("Pink")
    mat.diffuse_color = (0.82, 0.12, 0.59, 1)
    cube.data.materials.append(mat)

    cam_data = bpy.data.cameras.new("Cam")
    cam = bpy.data.objects.new("Cam", cam_data)
    scene.collection.objects.link(cam)
    cam.location = (5, -5, 3)
    direction = (cam.location[0] - 0, cam.location[1] - 0, cam.location[2] - 0)
    rot = mathutils_rotation(direction)
    cam.rotation_euler = rot
    scene.camera = cam

    if not scene.objects.get("Sun"):
        light = bpy.data.lights.new("Sun", "SUN")
        light.energy = 4
        lo = bpy.data.objects.new("Sun", light)
        scene.collection.objects.link(lo)
        lo.rotation_euler = (math.radians(45), 0, math.radians(30))


def mathutils_rotation(direction):
    from mathutils import Vector
    return Vector(direction).to_track_quat('-Z', 'Y').to_euler()


def pose(scene, t):
    cube = bpy.data.objects["HeroCube"]
    cube.rotation_euler = (math.radians(90) * t, math.radians(180) * t, 0)
