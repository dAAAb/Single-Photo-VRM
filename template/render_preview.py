"""Blender: render front + side orthographic previews of a built template .blend (QA helper).

    blender -b out.blend --python render_preview.py -- out.png
"""
import math
import sys

import bpy
from mathutils import Vector

out = sys.argv[sys.argv.index("--") + 1]
body = bpy.data.objects["Body"]
scn = bpy.context.scene
pts = [body.matrix_world @ v.co for v in body.data.vertices]
lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
c = (lo + hi) / 2
size = max(hi.x - lo.x, hi.z - lo.z) * 1.08
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
scn.collection.objects.link(cam)
scn.camera = cam
cam.data.type = "ORTHO"
cam.data.ortho_scale = size
scn.render.engine = "BLENDER_WORKBENCH"
scn.display.shading.light = "STUDIO"
scn.display.shading.color_type = "TEXTURE"  # image texture where present, material colour otherwise
scn.render.resolution_x = scn.render.resolution_y = 700
for name, loc, rot in (("front", (c.x, c.y - 5, c.z), (90, 0, 0)), ("side", (c.x + 5, c.y, c.z), (90, 0, 90)),
                       ("back", (c.x, c.y + 5, c.z), (90, 0, 180))):
    cam.location = loc
    cam.rotation_euler = tuple(math.radians(a) for a in rot)
    scn.render.filepath = out.replace(".png", f"_{name}.png")
    bpy.ops.render.render(write_still=True)
