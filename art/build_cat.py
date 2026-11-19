"""Build the collectible cat, its looped animation, and the matching web assets.

Run with: blender -b -t 4 -P art/build_cat.py
"""
from math import cos, pi, sin
from pathlib import Path
import sys

import bpy
from mathutils import Vector
from mathutils.geometry import interpolate_bezier

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "art"
sys.dont_write_bytecode = True
sys.path.insert(0, str(ART))
WEB = ROOT / "dist" / "assets"
WEB.mkdir(parents=True, exist_ok=True)

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)


def material(name, hex_color, roughness, metallic=0.0):
    rgb = [int(hex_color[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    rgb = [v / 12.92 if v < .04045 else ((v + .055) / 1.055) ** 2.4 for v in rgb]
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*rgb, 1)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = mat.diffuse_color
    shader.inputs["Roughness"].default_value = roughness
    shader.inputs["Metallic"].default_value = metallic
    return mat


ivory = material("01 / Warm porcelain vinyl", "F3DFBD", .38)
belly = material("02 / Oat vinyl", "F9E9CF", .42)
ink = material("03 / Ink", "1F1C20", .44)
rubber = material("04 / Soft black headband", "211F23", .50)
hardware = material("05 / Brushed graphite", "524B48", .36, .25)
red = material("06 / Tomato neckerchief", "D83D29", .55)
bright = material("07 / Vermilion piping", "F05D37", .48)
fold = material("08 / Cloth folds", "992D24", .55)
pink = material("09 / Warm ear inset", "E7A38A", .53)
blush = material("10 / Cheek print", "D7957C", .60)
whisker = material("11 / Brown vinyl print", "72554A", .55)
shine = material("12 / Eye highlights", "FFEFDA", .28)
ear_rim = material("13 / Honey edge", "EDC69F", .42)


def finish(obj, name, mat, parent=None):
    obj.name = name
    if mat:
        obj.data.materials.append(mat)
    if parent:
        obj.parent = parent
    if obj.type == "MESH":
        for face in obj.data.polygons:
            face.use_smooth = True
    return obj


def pivot(name, xyz, parent=None):
    obj = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(obj)
    obj.empty_display_size = .12
    obj.location = xyz
    if parent:
        obj.parent = parent
    return obj


def oval(name, xyz, shape, mat, parent, rotation=(0, 0, 0), sides=28):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=sides, ring_count=sides // 2, location=xyz)
    obj = finish(bpy.context.object, name, mat, parent)
    obj.scale = shape
    obj.rotation_euler = rotation
    return obj


def stroke(name, points, radius, mat, parent, mesh=True, ends=True, resolution=6):
    """A smooth tube with optional radii at each point."""
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = resolution
    curve.bevel_depth = radius
    curve.bevel_resolution = 3
    curve.use_fill_caps = ends
    spline = curve.splines.new("BEZIER")
    spline.bezier_points.add(len(points) - 1)
    for knot, pt in zip(spline.bezier_points, points):
        knot.co = pt[:3]
        knot.handle_left_type = knot.handle_right_type = "AUTO"
        knot.radius = pt[3] if len(pt) > 3 else 1
    obj = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(obj)
    finish(obj, name, mat, parent)
    if mesh:
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.convert(target="MESH")
        finish(obj, name, None)
    return obj


def rounded_outline(corners, roundness=.18, samples=6):
    pts = [Vector(p) for p in corners]
    result = []
    for i, middle in enumerate(pts):
        start = middle.lerp(pts[i - 1], roundness)
        end = middle.lerp(pts[(i + 1) % len(pts)], roundness)
        for j in range(samples):
            t = j / (samples - 1)
            result.append(start * (1 - t) ** 2 + 2 * middle * t * (1 - t) + end * t ** 2)
    return result


def padded_patch(name, outline, depth, mat, parent, roundness=.19):
    """A closed, inflated shape from an outline in the XZ plane."""
    border = rounded_outline(outline, roundness)
    center = sum(border, Vector((0, 0, 0))) / len(border)
    steps = 12
    count = len(border)
    verts = [tuple(center + Vector((0, depth, 0)))]
    for step in range(1, steps):
        ang = pi * step / steps
        for point in border:
            pos = center.lerp(point, sin(ang))
            verts.append((pos.x, pos.y + depth * cos(ang), pos.z))
    verts.append(tuple(center - Vector((0, depth, 0))))
    faces = []
    for i in range(count):
        ni = (i + 1) % count
        faces.append((0, 1 + i, 1 + ni))
        for tier in range(steps - 2):
            j = 1 + count * tier
            faces.append((j + i, j + count + i, j + count + ni, j + ni))
        j = 1 + count * (steps - 2)
        faces.append((j + ni, j + i, len(verts) - 1))
    data = bpy.data.meshes.new(name)
    data.from_pydata(verts, [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    return finish(obj, name, mat, parent)


root = pivot("CollectibleCat", (0, 0, 0))
motion = pivot("FetchRoot", (0, 0, 0), root)
motion["fetchHandoffSeconds"] = 8.42
body = pivot("Breath", (0, 0, .49), motion)
head_motion = pivot("HeadMotion", (-.055, -.018, 1.51), motion)
head = pivot("HeadPivot", (0, 0, 0), head_motion)
tail = pivot("TailPivot", (.47, .21, .33), motion)

# Torso and paws keep their original seated silhouettes. The walking pose
# articulates each limb with a separate upper section, hock, and foot.
torso = oval("Seated torso", (-.06, .10, .13), (.66, .50, .65), ivory, body, (0, -.14, -.08), 40)
bib = oval("Belly inset", (-.055, -.300, .065), (.464, .132, .451), belly, body, (-.11, 0, -.08))
legs = []
for side, specs in (
    ("Left", (-.399, -.470, .160, (.291, .339, .153), (.02, -.02, -.17),
              (-.33, -.330, .027), (.219, .252, .467), (-.32, -.18, .06),
              (-.49, .135, .276), (.324, .394, .280), (0, -.17, -.16))),
    ("Right", (.298, -.539, .154, (.226, .328, .149), (.02, .02, .13),
               (.257, -.344, .015), (.200, .220, .421), (-.43, .21, -.02),
               (.40, .20, .261), (.351, .402, .263), (0, .19, .2))),
):
    x, y, z, paw_shape, paw_rotation, fore_location, fore_shape, fore_rotation, haunch_location, haunch_shape, haunch_rotation = specs
    foot = pivot(f"{side} front foot", (x, y, z), motion)
    paw = oval(f"{side} forepaw", (0, 0, 0), paw_shape, ivory, foot, paw_rotation)
    for i in (-1, 1):
        toe_x = i * .069
        stroke(f"{side} toe seam {i}", [(toe_x, -.269, .241 - z, .46), (toe_x + .009, -.292, .214 - z),
            (toe_x + .013, -.308, .181 - z, .3)], .010, ear_rim, foot)
    fore_location = Vector(fore_location) + body.location
    fore = oval(f"{side} foreleg", fore_location, fore_shape, ivory, motion, fore_rotation)
    haunch = oval(f"{side} haunch", haunch_location, haunch_shape, ivory, motion, haunch_rotation)
    rear_position = (haunch_location[0], haunch_location[1] + .06, .19)
    rear_foot = pivot(f"{side} rear foot", rear_position, motion)
    oval(f"{side} rear paw", (0, 0, 0), (.171, .232, .134), ivory, rear_foot)
    rear_foot.scale = (.025, .025, .025)
    fore_shin = oval(f"{side} front shin", (x, y, z), (.004, .004, .004), ivory, motion)
    rear_shin = oval(f"{side} rear hock", rear_position, (.004, .004, .004), ivory, motion)
    legs.append((side, False, fore, fore_shin, foot))
    legs.append((side, True, haunch, rear_shin, rear_foot))

# Tail curls forward. A separate dark cap follows the underlying tapered tube.
tail_shape = [
    (0, 0, 0, .87), (.27, .014, -.084, 1.05), (.534, .018, -.114, 1),
    (.78, -.126, -.06, .91), (.864, -.322, .068, .83), (.799, -.507, .217, .78),
    (.660, -.574, .328, .60), (.568, -.554, .339, .40), (.534, -.531, .326, .08),
]
# Build the taper in rings so the dark tip ends at one clean boundary.
tail_curve = stroke("Tail centerline", tail_shape, .17, ivory, tail, mesh=False)
knots = tail_curve.data.splines[0].bezier_points
points = []
for j, (first, second) in enumerate(zip(knots, knots[1:])):
    segment = interpolate_bezier(first.co, first.handle_right, second.handle_left, second.co, 9)
    for n, center in enumerate(segment[:-1]):
        r = first.radius + (second.radius - first.radius) * n / 8
        points.append((center, r))
points.append((knots[-1].co.copy(), knots[-1].radius))
bpy.data.objects.remove(tail_curve, do_unlink=True)
sides = 18
verts = []
faces = []
for j, (center, r) in enumerate(points):
    tangent = (points[min(j + 1, len(points) - 1)][0] - points[max(j - 1, 0)][0]).normalized()
    normal = tangent.cross(Vector((0, 0, 1))).normalized()
    across = tangent.cross(normal).normalized()
    for i in range(sides):
        theta = i * 2 * pi / sides
        verts.append(center + .17 * r * (cos(theta) * normal + sin(theta) * across))
    if j:
        for i in range(sides):
            k = (i + 1) % sides
            faces.append(((j - 1) * sides + i, (j - 1) * sides + k, j * sides + k, j * sides + i))
faces.extend((tuple(reversed(range(sides))), tuple(range(len(verts) - sides, len(verts)))))
tail_data = bpy.data.meshes.new("Two-tone tail")
tail_data.from_pydata(verts, [], faces)
tail_data.update()
tail_mesh = bpy.data.objects.new("Curled tail / two-tone vinyl", tail_data)
bpy.context.collection.objects.link(tail_mesh)
finish(tail_mesh, tail_mesh.name, ivory, tail)
tail_data.materials.append(ink)
for polygon in tail_data.polygons:
    if (34 * sides <= polygon.index < len(faces) - 2) or polygon.index == len(faces) - 1:
        polygon.material_index = 1

# Neckwear wraps the body and ends in an off-center knot and two short folds.
scarf = pivot("Neckerchief", (0, 0, .115), body)
stroke("Neckerchief roll", [
    (-.49, .148, .492, .86), (-.55, -.158, .492), (-.365, -.407, .451),
    (-.045, -.535, .437), (.277, -.465, .482), (.488, -.256, .543), (.443, .071, .550, .76),
], .102, red, scarf)
padded_patch("Neckerchief front", [
    (-.471, -.450, .487), (-.270, -.583, .437), (.105, -.626, .442),
    (.390, -.446, .479), (.135, -.651, .118), (.036, -.681, .063), (-.089, -.648, .147),
], .079, red, scarf)
stroke("Neckerchief edge stitching", [(-.269, -.618, .348, .3), (-.162, -.677, .242),
    (.027, -.706, .102), (.226, -.665, .293), (.286, -.607, .346, .45)], .010, bright, scarf)
stroke("Neckerchief fold", [(-.352, -.577, .457, .19), (-.214, -.649, .387, .85),
    (.009, -.673, .352), (.195, -.605, .400, .2)], .016, fold, scarf)
oval("Neckerchief knot", (.435, -.338, .456), (.145, .128, .094), bright, scarf, (.14, .36, .42))
padded_patch("Knot upper tie", [(.431, -.371, .441), (.668, -.305, .481), (.613, -.391, .320)],
    .043, red, scarf)
padded_patch("Knot lower tie", [(.447, -.405, .437), (.586, -.411, .368), (.544, -.450, .225),
    (.474, -.436, .277)], .039, fold, scarf)

# Head parts share a neck-height pivot, left free for pointer tracking.
oval("Oversized vinyl head", (0, 0, .363), (.797, .600, .641), ivory, head, (0, -.051, -.018), 48)
for side, shift, angle in ((-1, -.023, -.04), (1, .033, .03)):
    signed = lambda x: side * x
    ear = [
        (signed(.300), .034, .752), (signed(.580), .021, 1.215 + shift),
        (signed(.695), .017, 1.273 + shift), (signed(.791), -.002, 1.160 + shift),
        (signed(.819), -.030, .780), (signed(.632), -.089, .707),
    ]
    padded_patch(f"Ear {side:+}", ear, .175, ivory, head, .24)
    inset = [
        (signed(.471), -.164, .867), (signed(.675), -.146, 1.160 + shift),
        (signed(.739), -.132, 1.140 + shift), (signed(.776), -.150, .872),
        (signed(.672), -.180, .821),
    ]
    padded_patch(f"Inner ear {side:+}", inset, .052, pink, head, .28)

# Oversized black headphones have an inset headband and coin-like driver shells.
arc = [(cos(t) * .863, .099, .467 + sin(t) * .569) for t in
       [pi + .16, pi * .86, pi * .70, pi * .55, pi * .39, pi * .24, pi * .07, -.16]]
stroke("Headphones / arch", arc, .072, rubber, head)
stroke("Headphones / crown pad", [(x * .966, y - .012, z - .041, r) for (x, y, z), r in
    zip(arc[2:6], (.38, 1, 1, .38))], .078, ink, head)
for side in (-1, 1):
    cup = pivot(f"Headphones / {'left' if side < 0 else 'right'} housing", (side * .771, -.077, .390), head)
    cup.rotation_euler = (.039, side * -.115, side * -.11)
    oval("Padded ear seal", (side * .009, .023, .006), (.209, .274, .325), rubber, cup, sides=36)
    oval("Housing shell", (side * .137, .010, .013), (.207, .247, .296), ink, cup, sides=40)
    oval("Turned outer edge", (side * .258, .008, .013), (.093, .192, .225), hardware, cup)
    oval("Driver face", (side * .289, .004, .015), (.078, .180, .209), rubber, cup)
    oval("Round red enamel mark", (side * .363, .003, .008), (.016, .059, .059), red, cup, sides=24)
    oval("Enamel center", (side * .376, .003, .008), (.008, .019, .019), bright, cup, sides=20)
    stroke("Floating bracket", [(side * .068, .150, .301), (side * .169, .168, .261),
        (side * .250, .148, .183), (side * .276, .125, .098)], .032, hardware, cup)
    for z in (-.152, -.125, -.098):
        stroke("Driver grille", [(side * .354, -.062, z, .36), (side * .359, -.035, z),
            (side * .358, -.006, z, .40)], .008, hardware, cup)

# Face print and raised sculpted muzzle.
for side in (-1, 1):
    x = side * .272
    eye_z = .435 + side * .016
    oval("Oval lacquered eye", (x, -.551, eye_z), (.079, .050, .119), ink, head, (0, side * -.105, side * .32))
    oval("Large eye reflection", (x - .022, -.594, eye_z + .042), (.023, .013, .027), shine, head, sides=24)
    oval("Small eye reflection", (x + .021, -.595, eye_z - .033), (.009, .008, .010), shine, head, sides=20)
    stroke("Expressive eyebrow", [(x - .064, -.517, eye_z + .177, .24), (x, -.539, eye_z + .197),
        (x + .056, -.523, eye_z + .184, .23)], .023, whisker, head)
    oval("Warm cheek mark", (side * .448, -.483, .290), (.080, .016, .034), blush, head, (0, side * -.13, side * -.47), 24)
    for i in range(2):
        z = .265 - .060 * i
        stroke("Whisker print", [(side * .495, -.456, z, .58), (side * .566, -.417, z + .015),
            (side * .616, -.373, z + .032, .25)], .011, whisker, head)
oval("Left muzzle pad", (-.104, -.558, .249), (.166, .094, .105), belly, head, (0, .19, .08))
oval("Right muzzle pad", (.091, -.558, .249), (.166, .096, .106), belly, head, (0, -.16, -.07))
padded_patch("Small ink nose", [(-.071, -.648, .314), (.067, -.647, .311), (.002, -.673, .246)],
    .023, ink, head, .29)
stroke("Smile center", [(0, -.674, .264), (0, -.667, .220), (.004, -.647, .193, .8)], .015, ink, head)
stroke("Smile left curl", [(.004, -.647, .193), (-.049, -.650, .183), (-.100, -.641, .210, .6),
    (-.111, -.637, .228, .25)], .015, ink, head)
stroke("Smile right curl", [(.004, -.647, .193), (.061, -.649, .185), (.114, -.633, .216, .6),
    (.121, -.630, .235, .25)], .015, ink, head)
oval("Nose glint", (-.016, -.673, .307), (.024, .009, .008), hardware, head, sides=20)

from cat_motion import LAST_FRAME, arrange_animation, author_fetch
scene = bpy.context.scene
fetch_parts = author_fetch(scene, root, motion, body, torso, bib, scarf, head_motion, tail, legs, material, pivot)
idle_parts = (body, tail)
for part in idle_parts:
    part.animation_data.action = None
scene.render.fps = 24
scene.frame_start, scene.frame_end = 0, 228
for frame, breath, tail_a, tail_b in (
     (0, 1.0, -.06, -.02), (30, 1.015, .035, .040), (60, 1.0, .12, .0),
     (90, 1.012, .010, -.045), (120, 1.0, -.06, -.02),
):
    body.scale = (2 - breath, 2 - breath, breath)
    body.keyframe_insert(data_path="scale", frame=frame)
    tail.rotation_euler = (.05, tail_b, tail_a)
    tail.keyframe_insert(data_path="rotation_euler", frame=frame)
    for part in (body, tail):
        part.animation_data.action.name = f"Idle / {part.name}"
idle_actions = {part: part.animation_data.action for part in idle_parts}
arrange_animation(fetch_parts, idle_actions, idle_start=240)
scene.frame_set(0)

# Studio lights and an orthographic three-quarter camera for the transparent fallback.
def point(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def area(name, xyz, aim, power, color, size):
    bpy.ops.object.light_add(type="AREA", location=xyz)
    light = bpy.context.object
    light.name = name
    light.data.energy = power
    light.data.color = color
    light.data.shape = "DISK"
    light.data.size = size
    point(light, aim)


bpy.ops.object.camera_add(location=(4.0, -9.35, 4.25))
camera = bpy.context.object
camera.name = "Portrait camera"
camera.data.type = "ORTHO"
camera.data.ortho_scale = 3.65
point(camera, (.105, -.025, 1.425))
scene.camera = camera
bpy.ops.object.camera_add(location=(.48, -14, 5.7))
preview_camera = bpy.context.object
preview_camera.name = "Fetch camera"
preview_camera.data.type = "ORTHO"
preview_camera.data.ortho_scale = 5.70
point(preview_camera, (.93, -.05, 1.40))
scene.camera = preview_camera
area("Warm key", (-3.4, -4.5, 6.0), (0, 0, 1.45), 570, (1.0, .86, .74), 4.7)
area("Cool fill", (4.5, -2.1, 3.2), (0, 0, 1.45), 210, (.74, .84, 1.0), 4.3)
area("Edge light", (2.1, 3.0, 5.3), (0, 0, 1.65), 600, (1.0, .78, .57), 3.7)
area("Softbox reflection", (0, -5.5, 3.3), (0, 0, 1.4), 58, (1.0, .92, .84), 3.5)
scene.world.use_nodes = True
scene.world.node_tree.nodes["Background"].inputs[0].default_value = (.23, .21, .20, 1)
scene.world.node_tree.nodes["Background"].inputs[1].default_value = .48
scene.render.engine = "CYCLES"
scene.cycles.samples = 40
scene.cycles.use_denoising = True
scene.render.threads_mode = "FIXED"
scene.render.threads = 4
scene.render.film_transparent = True
scene.render.resolution_x = scene.render.resolution_y = 840
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
scene.render.filepath = "//../dist/assets/cat.png"
scene.view_settings.view_transform = "AgX"
scene.view_settings.look = "AgX - Medium High Contrast"

# Keep the editable scene in camera view when opened.
for screen in bpy.data.screens:
    for viewport in screen.areas:
        if viewport.type == "VIEW_3D":
            viewport.spaces.active.region_3d.view_perspective = "CAMERA"
            viewport.spaces.active.shading.color_type = "MATERIAL"

bpy.ops.object.select_all(action="DESELECT")
bpy.context.view_layer.objects.active = head
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(ART / "collectible-cat.blend"), compress=True)

# Merge drawables by animated parent for web. The saved Blender file keeps
# the original editable parts and materials.
for part in (scarf, head, tail, *(leg[4] for leg in legs)):
    parts = [obj for obj in part.children_recursive if obj.type == "MESH" and
             (part != root or obj.parent == root)]
    if not parts:
        continue
    bpy.ops.object.select_all(action="DESELECT")
    for obj in parts:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    if len(parts) > 1:
        bpy.ops.object.join()
    merged = bpy.context.object
    transform = merged.matrix_world.copy()
    merged.parent = part
    merged.matrix_world = transform
    merged.name = f"{part.name} geometry"
for empty in list(root.children_recursive):
    if empty.type == "EMPTY" and not empty.children:
        bpy.data.objects.remove(empty, do_unlink=True)
bpy.ops.object.select_all(action="DESELECT")
for obj in [root] + list(root.children_recursive):
    obj.select_set(True)
arrange_animation(fetch_parts, idle_actions, idle_start=0)
scene.frame_set(0)
bpy.ops.export_scene.gltf(filepath=str(WEB / "cat.glb"), export_format="GLB",
                          use_selection=True, export_cameras=False, export_lights=False,
                          export_animation_mode="NLA_TRACKS", export_merge_animation="NLA_TRACK",
                          export_texcoords=False, export_optimize_animation_size=True, export_extras=True)
if "--poster" in sys.argv:
    scene.camera = camera
    scene.render.filepath = str(WEB / "cat.png")
    bpy.ops.render.render(write_still=True)
