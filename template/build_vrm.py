"""Blender (headless) builder: anny_tpose.npz → template VRM 1.0 + VRM 0.x with Perfect Sync.

    BLENDER_USER_RESOURCES=../build/blender_user blender -b --python build_vrm.py -- \
        ../build/anny_tpose.npz ../build/template
"""
import json
import os
import sys

import bpy
import numpy as np
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
NPZ, OUT = argv[0], argv[1]
TEX = json.load(open(argv[2])) if len(argv) > 2 else None  # optional texture.json from fit/texture.py
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


def to_mtoon(mat, rgba=None, image=None, mask=False, double_sided=False):
    """VRM-native MToon: photo textures already contain lighting, so keep shading gentle
    (light shade colour, strong GI equalisation) instead of PBR darkening the photo."""
    mt = mat.vrm_addon_extension.mtoon1
    mt.enabled = True
    pbr = mt.pbr_metallic_roughness
    if rgba is not None:
        pbr.base_color_factor = rgba
    ext_ = mt.extensions.vrmc_materials_mtoon
    if image is not None:
        pbr.base_color_texture.index.source = image
        ext_.shade_multiply_texture.index.source = image
    ext_.shade_color_factor = (0.86, 0.84, 0.84)
    ext_.shading_toony_factor = 0.6
    ext_.shading_shift_factor = -0.15
    ext_.gi_equalization_factor = 0.9
    if mask:
        mt.alpha_mode = "MASK"
        mt.alpha_cutoff = 0.5
    mt.double_sided = double_sided


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
    group = d["face_group"] if "face_group" in d else np.zeros(len(faces), np.int32)
    pmats = json.loads(str(d["proxy_mats"])) if "proxy_mats" in d else []
    comp = components(len(verts), faces[group == 0])
    body_verts = np.zeros(len(verts), bool)
    body_verts[faces[group == 0].reshape(-1)] = True
    comp[~body_verts] = -1
    labels, counts = np.unique(comp[body_verts], return_counts=True)
    body_label = labels[np.argmax(counts)]
    tongue_mask = np.abs(d["deltas"][ARKIT.index("tongueOut")]).sum(1) > 1e-5
    teeth_mask = d["teeth"] if "teeth" in d else np.zeros(len(verts), bool)
    mats = {k: make_material(k, c) for k, c in {
        "Skin": (0.86, 0.68, 0.58, 1), "Mouth": (0.72, 0.36, 0.38, 1), "Teeth": (0.93, 0.91, 0.86, 1),
        "Sclera": (0.78, 0.76, 0.74, 1), "Iris": (0.33, 0.22, 0.13, 1), "Pupil": (0.02, 0.02, 0.02, 1)}.items()}
    if TEX:
        skin = mats["Skin"]
        nt = skin.node_tree
        img = bpy.data.images.load(TEX["texture"])
        img.pack()
        node = nt.nodes.new("ShaderNodeTexImage")
        node.image = img
        nt.links.new(node.outputs["Color"], nt.nodes["Principled BSDF"].inputs["Base Color"])
        if TEX.get("iris"):
            r, g, b = (c / 255 for c in TEX["iris"])
            mats["Iris"].node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (r, g, b, 1)
            mats["Iris"].diffuse_color = (r, g, b, 1)
    for pm in pmats:  # MakeHuman proxies: textured, alpha-clipped (glTF alphaMode MASK)
        m = make_material(pm["name"], tuple(c / 255 for c in pm["color"]) + (1,) if pm.get("color") else (0.3, 0.2, 0.15, 1))
        if pm.get("texture"):
            nt = m.node_tree
            bsdf = nt.nodes["Principled BSDF"]
            img = bpy.data.images.load(pm["texture"])
            img.pack()
            tex = nt.nodes.new("ShaderNodeTexImage")
            tex.image = img
            nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
            gt = nt.nodes.new("ShaderNodeMath")  # alpha > 0.5 → exported as MASK with cutoff
            gt.operation = "GREATER_THAN"
            gt.inputs[1].default_value = 0.5
            nt.links.new(tex.outputs["Alpha"], gt.inputs[0])
            nt.links.new(gt.outputs[0], bsdf.inputs["Alpha"])
            m.use_backface_culling = False
        mats[pm["name"]] = m
    # MToon for everything (after the node setup above, which MToon reads/rebuilds)
    skin_img = bpy.data.images.get(os.path.basename(TEX["texture"])) if TEX else None
    for name, m in mats.items():
        base = tuple(m.diffuse_color)
        if name == "Skin":
            to_mtoon(m, (1, 1, 1, 1) if skin_img else base, skin_img)
        elif any(pm["name"] == name for pm in pmats):
            pm = next(pm for pm in pmats if pm["name"] == name)
            img = bpy.data.images.get(os.path.basename(pm["texture"])) if pm.get("texture") else None
            to_mtoon(m, (1, 1, 1, 1) if img else base, img, mask=img is not None, double_sided=True)
        else:
            to_mtoon(m, base)
    for m in mats.values():
        me.materials.append(m)
    order = list(mats)
    eye_centers = {}
    for lab in labels:
        if lab == body_label or lab < 0:
            continue
        vs = np.where(comp == lab)[0]
        if tongue_mask[vs].mean() > 0.5 or teeth_mask[vs].mean() > 0.5:
            continue
        eye_centers[lab] = verts[vs].mean(0)
    for p in me.polygons:
        f = faces[p.index]
        lab = comp[f[0]]
        if group[p.index] > 0:
            p.material_index = order.index(pmats[group[p.index] - 1]["name"])
            continue
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
            p.material_index = order.index("Pupil" if ang < 13 else "Iris" if ang < 31 else "Sclera")  # human-like iris size

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


def hair_chains(arm, ob, n_seg=4):
    """Bone chains for the hanging part of the hair (ponytail, long hair, braids) so it can swing.

    Hanging = hair vertices below ear level; clustered by azimuth around the head (back / left /
    right). Each cluster gets a chain following its centre line from the scalp down; vertices are
    weighted along the chain and blended with the head near the root."""
    group = d["face_group"] if "face_group" in d else None
    pmats = json.loads(str(d["proxy_mats"])) if "proxy_mats" in d else []
    hair_groups = [k + 1 for k, pm in enumerate(pmats) if pm["kind"] == "hair"]
    if group is None or not hair_groups:
        return []
    faces = d["faces"]
    hv = np.unique(faces[np.isin(group, hair_groups)].reshape(-1))
    V = d["verts"]
    li = LABELS.index
    head_c = d["heads"][li("head")] + np.array([0, 0, 0.09])  # ~ middle of the head
    ear_z = d["heads"][li("head")][2] + 0.02
    hang = hv[V[hv, 2] < ear_z]
    if len(hang) < 40:
        return []
    rel = V[hang] - head_c
    az = np.degrees(np.arctan2(rel[:, 0], rel[:, 1]))  # 0° = straight back (+Y)
    sectors = {"back": np.abs(az) <= 55, "left": az > 55, "right": az < -55}
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm.data.edit_bones
    chains = []
    weights = {}
    for sname, m in sectors.items():
        vs = hang[m]
        if len(vs) < 30:
            continue
        z = V[vs, 2]
        top, bot = z.max() + 0.01, z.min()
        if top - bot < 0.06:
            continue
        # centre line: centroids of height bands, starting at the scalp attachment
        levels = np.linspace(top, bot, n_seg + 1)
        pts = [V[hv][np.abs(V[hv, 2] - top) < 0.03].mean(0) if sname == "back" else V[vs][z > top - 0.03].mean(0)]
        for a, b in zip(levels[1:-1], levels[2:]):
            band = vs[(z <= a + 0.02) & (z >= b - 0.02)]
            pts.append(V[band].mean(0) if len(band) else pts[-1] + np.array([0, 0, -(top - bot) / n_seg]))
        pts.append(V[vs][z < bot + 0.02].mean(0))
        names = []
        parent = eb["head"]
        for k in range(n_seg):
            b = eb.new(f"hair_{sname}_{k}")
            b.head, b.tail = Vector(pts[k].tolist()), Vector(pts[k + 1].tolist())
            if (b.tail - b.head).length < 0.01:
                b.tail = b.head + Vector((0, 0, -0.02))
            b.parent = parent
            b.use_connect = False
            parent = b
            names.append(b.name)
        # weights along the chain (by height), blended with the head near the root
        t = np.clip((top - z) / (top - bot), 0, 1)
        for vi, tv in zip(vs, t):
            f = tv * n_seg
            k = min(int(f), n_seg - 1)
            frac = f - k
            root = min(1.0, tv / 0.15)
            ws = {names[k]: (1 - frac) * root}
            if k + 1 < n_seg:
                ws[names[k + 1]] = frac * root
            weights[int(vi)] = (root, ws)
        chains.append(names)
    bpy.ops.object.mode_set(mode="OBJECT")
    for vi, (root, ws) in weights.items():
        for g in ob.vertex_groups:  # scale down the original (head / body) influence
            try:
                wv = g.weight(vi)
            except RuntimeError:
                continue
            g.add([vi], wv * (1 - root), "REPLACE")
        for name, wv in ws.items():
            vg = ob.vertex_groups.get(name) or ob.vertex_groups.new(name=name)
            vg.add([vi], wv, "ADD")
    return chains


SPRING = dict(stiffness=1.2, gravity_power=0.15, drag_force=0.45, hit_radius=0.02)
COLLIDERS = [("head", 0.1, (0.0, 0.07, 0.0)), ("neck01", 0.06, (0.0, 0.0, 0.0)),
             ("spine01", 0.11, (0.0, 0.0, 0.0)), ("clavicle.L", 0.06, (0.0, 0.1, 0.0)),
             ("clavicle.R", 0.06, (0.0, 0.1, 0.0))]


def setup_springs_vrm1(arm, chains):
    sb = ext(arm).spring_bone1
    if not chains or len(sb.springs):
        return
    ctx = bpy.context
    cg = sb.add_collider_group()
    cg.vrm_name = "body"
    for bone, r, off in COLLIDERS:
        c = sb.add_collider(ctx, arm)
        c.node.bone_name = bone
        c.shape.sphere.radius = r
        c.shape.sphere.offset = off
        cg.add_collider().collider_uuid = c.uuid
    for names in chains:
        sp = sb.add_spring()
        sp.vrm_name = names[0].rsplit("_", 1)[0]
        for n in names:
            j = sp.add_joint()
            j.node.bone_name = n
            j.stiffness, j.gravity_power = SPRING["stiffness"], SPRING["gravity_power"]
            j.drag_force, j.hit_radius = SPRING["drag_force"], SPRING["hit_radius"]
        sp.add_collider_group().collider_group_uuid = cg.uuid


def setup_springs_vrm0(arm, chains):
    import uuid as _uuid
    sa = ext(arm).vrm0.secondary_animation
    if not chains or len(sa.bone_groups):
        return
    cgs = []
    for bone, r, _ in COLLIDERS:
        cg = sa.collider_groups.add()
        cg.uuid = _uuid.uuid4().hex
        cg.node.bone_name = bone
        empty = bpy.data.objects.new(f"collider_{bone}", None)
        bpy.context.scene.collection.objects.link(empty)
        empty.parent = arm
        empty.parent_type = "BONE"
        empty.parent_bone = bone
        empty.empty_display_type = "SPHERE"
        empty.empty_display_size = r
        pb = arm.data.bones[bone]
        empty.location = (0, -pb.length + (0.07 if bone == "head" else 0.0), 0)  # parent is the bone tail
        cg.colliders.add().bpy_object = empty
        cgs.append(cg)
    for names in chains:
        g = sa.bone_groups.add()
        g.comment = names[0].rsplit("_", 1)[0]
        g.stiffiness, g.gravity_power = SPRING["stiffness"], SPRING["gravity_power"]
        g.drag_force, g.hit_radius = SPRING["drag_force"], SPRING["hit_radius"]
        g.bones.add().bone_name = names[0]
        for cg in cgs:
            g.collider_groups.add().collider_group_uuid = cg.uuid


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
CHAINS = hair_chains(arm, body)
print("HAIR CHAINS", CHAINS)
setup_vrm1(arm, body)
setup_springs_vrm1(arm, CHAINS)
export(OUT + ".vrm1.vrm", arm)
setup_vrm0(arm, body)
setup_springs_vrm0(arm, CHAINS)
export(OUT + ".vrm0.vrm")
bpy.ops.wm.save_as_mainfile(filepath=OUT + ".blend")
