"""Blender (headless) builder: anny_tpose.npz → template VRM 1.0 + VRM 0.x with Perfect Sync.

    BLENDER_USER_RESOURCES=../build/blender_user blender -b --python build_vrm.py -- \
        ../build/anny_tpose.npz ../build/template
"""
import json
import sys

import bpy
import numpy as np
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
NPZ, OUT = argv[0], argv[1]
d = np.load(NPZ)
ARKIT = [str(x) for x in d["arkit"]]
LABELS = [str(x) for x in d["labels"]]
VRM_MAP = json.loads(str(d["vrm_map"]))

# ARKit combinations for the standard VRM presets (for apps without Perfect Sync).
PRESETS = {
    "aa": {"jawOpen": 0.8, "mouthLowerDownLeft": 0.3, "mouthLowerDownRight": 0.3},
    "ih": {"jawOpen": 0.25, "mouthStretchLeft": 0.6, "mouthStretchRight": 0.6},
    "ou": {"jawOpen": 0.2, "mouthPucker": 0.9, "mouthFunnel": 0.3},
    "ee": {"jawOpen": 0.2, "mouthSmileLeft": 0.35, "mouthSmileRight": 0.35, "mouthStretchLeft": 0.4, "mouthStretchRight": 0.4},
    "oh": {"jawOpen": 0.45, "mouthFunnel": 0.8},
    "blink": {"eyeBlinkLeft": 1, "eyeBlinkRight": 1},
    "blinkLeft": {"eyeBlinkLeft": 1},
    "blinkRight": {"eyeBlinkRight": 1},
    "happy": {"mouthSmileLeft": 0.9, "mouthSmileRight": 0.9, "cheekSquintLeft": 0.6, "cheekSquintRight": 0.6, "eyeSquintLeft": 0.4, "eyeSquintRight": 0.4},
    "angry": {"browDownLeft": 0.9, "browDownRight": 0.9, "noseSneerLeft": 0.4, "noseSneerRight": 0.4, "mouthFrownLeft": 0.5, "mouthFrownRight": 0.5, "eyeSquintLeft": 0.3, "eyeSquintRight": 0.3},
    "sad": {"browInnerUp": 0.9, "mouthFrownLeft": 0.7, "mouthFrownRight": 0.7, "mouthShrugLower": 0.3},
    "relaxed": {"mouthSmileLeft": 0.5, "mouthSmileRight": 0.5, "eyeSquintLeft": 0.3, "eyeSquintRight": 0.3},
    "surprised": {"eyeWideLeft": 0.9, "eyeWideRight": 0.9, "browInnerUp": 0.8, "browOuterUpLeft": 0.8, "browOuterUpRight": 0.8, "jawOpen": 0.35},
    "lookUp": {"eyeLookUpLeft": 1, "eyeLookUpRight": 1},
    "lookDown": {"eyeLookDownLeft": 1, "eyeLookDownRight": 1},
    "lookLeft": {"eyeLookOutLeft": 1, "eyeLookInRight": 1},
    "lookRight": {"eyeLookInLeft": 1, "eyeLookOutRight": 1},
}
VRM0_PRESET = {"aa": "a", "ih": "i", "ou": "u", "ee": "e", "oh": "o", "blink": "blink", "blinkLeft": "blink_l",
               "blinkRight": "blink_r", "happy": "joy", "angry": "angry", "sad": "sorrow", "relaxed": "fun",
               "lookUp": "lookup", "lookDown": "lookdown", "lookLeft": "lookleft", "lookRight": "lookright"}
VRM0_NAME = {"aa": "A", "ih": "I", "ou": "U", "ee": "E", "oh": "O", "blink": "Blink", "blinkLeft": "Blink_L",
             "blinkRight": "Blink_R", "happy": "Joy", "angry": "Angry", "sad": "Sorrow", "relaxed": "Fun",
             "lookUp": "LookUp", "lookDown": "LookDown", "lookLeft": "LookLeft", "lookRight": "LookRight"}
SNAKE = lambda s: "".join("_" + c.lower() if c.isupper() else c for c in s)  # leftUpperArm → left_upper_arm


def clear_scene():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.armatures, bpy.data.materials):
        for x in list(coll):
            coll.remove(x)


def components(n_verts, faces):
    parent = np.arange(n_verts)
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for f in faces:
        r = [find(v) for v in f]
        for x in r[1:]:
            parent[x] = r[0]
    return np.array([find(v) for v in range(n_verts)])


def make_material(name, rgba):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = rgba
    bsdf.inputs["Roughness"].default_value = 0.6
    m.diffuse_color = rgba
    return m


def build():
    clear_scene()
    verts, faces = d["verts"], d["faces"]
    # --- mesh
    me = bpy.data.meshes.new("Body")
    me.from_pydata(verts.tolist(), [], faces.tolist())
    me.update()
    uv_layer = me.uv_layers.new(name="UVMap")
    uv_idx = d["uv_idx"].reshape(-1)
    uv_layer.data.foreach_set("uv", d["uv"][uv_idx].reshape(-1))
    ob = bpy.data.objects.new("Body", me)
    bpy.context.scene.collection.objects.link(ob)
    for p in me.polygons:
        p.use_smooth = True

    # --- materials: skin / tongue / eye (sclera, iris, pupil)
    comp = components(len(verts), faces)
    labels, counts = np.unique(comp, return_counts=True)
    body_label = labels[np.argmax(counts)]
    tongue_mask = np.abs(d["deltas"][ARKIT.index("tongueOut")]).sum(1) > 1e-5
    teeth_mask = d["teeth"] if "teeth" in d else np.zeros(len(verts), bool)
    mats = {k: make_material(k, c) for k, c in {
        "Skin": (0.86, 0.68, 0.58, 1), "Mouth": (0.72, 0.36, 0.38, 1), "Teeth": (0.93, 0.91, 0.86, 1),
        "Sclera": (0.95, 0.95, 0.93, 1), "Iris": (0.33, 0.22, 0.13, 1), "Pupil": (0.02, 0.02, 0.02, 1)}.items()}
    for m in mats.values():
        me.materials.append(m)
    order = list(mats)
    eye_centers = {}
    for lab in labels:
        if lab == body_label:
            continue
        vs = np.where(comp == lab)[0]
        if tongue_mask[vs].mean() > 0.5 or teeth_mask[vs].mean() > 0.5:
            continue
        eye_centers[lab] = verts[vs].mean(0)
    for p in me.polygons:
        f = faces[p.index]
        lab = comp[f[0]]
        if teeth_mask[f].all():
            p.material_index = order.index("Teeth")
        elif lab == body_label:
            p.material_index = order.index("Skin")
        elif tongue_mask[f].all():
            p.material_index = order.index("Mouth")
        else:
            c = eye_centers[lab]
            v = verts[f].mean(0) - c
            v /= np.linalg.norm(v) + 1e-9
            ang = np.degrees(np.arccos(np.clip(-v[1], -1, 1)))  # angle from forward (-Y)
            p.material_index = order.index("Pupil" if ang < 10 else "Iris" if ang < 24 else "Sclera")

    # --- shape keys (lowerCamel ARKit names; Warudo reads these directly)
    ob.shape_key_add(name="Basis")
    for k, name in enumerate(ARKIT):
        sk = ob.shape_key_add(name=name, from_mix=False)
        sk.data.foreach_set("co", (verts + d["deltas"][k]).reshape(-1))

    # --- armature
    arm_data = bpy.data.armatures.new("Armature")
    arm = bpy.data.objects.new("Armature", arm_data)
    bpy.context.scene.collection.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    ebs = []
    for i, n in enumerate(LABELS):
        eb = arm_data.edit_bones.new(n)
        eb.head = Vector(d["heads"][i].tolist())
        eb.tail = Vector(d["tails"][i].tolist())
        ebs.append(eb)
    for i, p in enumerate(d["parents"]):
        if p >= 0:
            ebs[i].parent = ebs[p]
            ebs[i].use_connect = False
    bpy.ops.object.mode_set(mode="OBJECT")

    # --- skin weights
    groups = [ob.vertex_groups.new(name=n) for n in LABELS]
    w_idx, w = d["w_idx"], d["w"]
    for vi in range(len(verts)):
        for j in range(w.shape[1]):
            if w[vi, j] > 1e-6:
                groups[w_idx[vi, j]].add([vi], float(w[vi, j]), "REPLACE")
    ob.parent = arm
    mod = ob.modifiers.new("Armature", "ARMATURE")
    mod.object = arm
    return arm, ob


def ext(arm):
    return arm.data.vrm_addon_extension


def set_meta_common(e, version):
    e.spec_version = version


def setup_vrm1(arm, ob):
    e = ext(arm)
    e.spec_version = "1.0"
    v1 = e.vrm1
    for anny_name, vrm_name in VRM_MAP.items():
        getattr(v1.humanoid.human_bones, SNAKE(vrm_name)).node.bone_name = anny_name
    m = v1.meta
    m.vrm_name = "Single-Photo-VRM Template"
    m.version = "0.1.0"
    if not len(m.authors):
        m.authors.add()
    m.authors[0].value = "Single-Photo-VRM"
    m.copyright_information = "Body/face: Anny (NAVER, Apache-2.0) with MakeHuman MPFB2 + Face Units assets (CC0)"
    m.third_party_licenses = "Anny code Apache-2.0; MPFB2 and faceunits01 assets CC0 1.0"
    m.avatar_permission = "everyone"
    m.commercial_usage = "corporation"
    m.credit_notation = "unnecessary"
    m.allow_redistribution = True
    m.modification = "allowModificationRedistribution"
    m.license_url = "https://vrm.dev/licenses/1.0/"

    exprs = v1.expressions
    exprs.initial_automatic_expression_assignment = False  # else export-time migration rebinds presets by name
    for name in ARKIT:  # Perfect Sync as custom expressions
        c = exprs.custom.add()
        c.custom_name = name
        b = c.morph_target_binds.add()
        b.node.mesh_object_name = ob.name
        b.index = name
        b.weight = 1.0
    for preset, combo in PRESETS.items():
        # Binding morphs to lookUp/Down/Left/Right makes the add-on migrate lookAt to "expression";
        # our eyes are driven by eye bones (eyelid shapes remain available via Perfect Sync eyeLook*).
        if preset.startswith("look"):
            continue
        ex = getattr(exprs.preset, SNAKE(preset))
        for shape, wgt in combo.items():
            b = ex.morph_target_binds.add()
            b.node.mesh_object_name = ob.name
            b.index = shape
            b.weight = float(wgt)
    for n in ("blink", "blinkLeft", "blinkRight"):
        getattr(exprs.preset, SNAKE(n)).is_binary = False
    la = v1.look_at
    la.type = "bone"
    la.offset_from_head_bone = (0.0, 0.06, 0.0)


def setup_vrm0(arm, ob):
    e = ext(arm)
    e.spec_version = "0.0"
    v0 = e.vrm0
    hb = v0.humanoid.human_bones
    hb.clear()
    for anny_name, vrm_name in VRM_MAP.items():
        if vrm_name.endswith("ThumbMetacarpal"):
            vrm0 = vrm_name.replace("ThumbMetacarpal", "ThumbProximal")
        elif vrm_name.endswith("ThumbProximal"):
            vrm0 = vrm_name.replace("ThumbProximal", "ThumbIntermediate")
        else:
            vrm0 = vrm_name
        b = hb.add()
        b.bone = vrm0
        b.node.bone_name = anny_name
    m = v0.meta
    for k, v in {"title": "Single-Photo-VRM Template", "version": "0.1.0", "author": "Single-Photo-VRM",
                 "allowed_user_name": "Everyone", "violent_ussage_name": "Disallow",
                 "sexual_ussage_name": "Disallow", "commercial_ussage_name": "Allow",
                 "license_name": "CC0", "other_license_url": ""}.items():
        try:
            setattr(m, k, v)
        except Exception as ex:  # field names differ between add-on versions
            print("meta skip", k, ex)
    groups = v0.blend_shape_master.blend_shape_groups
    groups.clear()
    for preset, combo in PRESETS.items():
        g = groups.add()
        g.name = VRM0_NAME.get(preset, preset[0].upper() + preset[1:])
        g.preset_name = VRM0_PRESET.get(preset, "unknown")  # VRM0 has no "surprised" preset
        for shape, wgt in combo.items():
            b = g.binds.add()
            b.mesh.mesh_object_name = ob.name
            b.index = shape
            b.weight = float(wgt)
    g = groups.add()
    g.name, g.preset_name = "Neutral", "neutral"
    for name in ARKIT:  # Perfect Sync clips: PascalCase (VSeeFace / VMagicMirror)
        g = groups.add()
        g.name = name[0].upper() + name[1:]
        g.preset_name = "unknown"
        b = g.binds.add()
        b.mesh.mesh_object_name = ob.name
        b.index = name
        b.weight = 1.0


def export(path, arm=None):
    if arm is not None:  # humanoid/expression updates can reset lookAt; set it last
        ext(arm).vrm1.look_at.type = "bone"
    bpy.ops.object.select_all(action="DESELECT")
    res = bpy.ops.export_scene.vrm(filepath=path)
    print("EXPORT", path, res)


arm, body = build()
setup_vrm1(arm, body)
export(OUT + ".vrm1.vrm", arm)
setup_vrm0(arm, body)
export(OUT + ".vrm0.vrm")
bpy.ops.wm.save_as_mainfile(filepath=OUT + ".blend")
