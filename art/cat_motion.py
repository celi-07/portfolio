"""Keyframe the collectible's Fetch performance at 24 frames per second."""

from math import pi, sin

import bpy
from mathutils import Euler, Matrix, Vector


FPS = 24
LAST_FRAME = 228
NECK_REST = Vector((-.055, -.018, 1.51))


def ease(value):
    t = max(0, min(value, 1))
    return t * t * (3 - 2 * t)


def ease_between(time, start, end):
    return ease((time - start) / (end - start))


def route(time):
    """Floor position and yaw. The cat's local forward is Blender -Y."""
    outgoing = max(0, min((time - 1.75) / 1.65, 1))
    returning = max(0, min((time - 5.30) / 1.65, 1))
    x = 1.58 * (outgoing - returning)
    yaw = pi / 2 * (
        ease_between(time, .83, 1.75)
        - 2 * ease_between(time, 4.29, 5.30)
        + ease_between(time, 6.95, 7.74)
    )
    return Vector((x, 0, 0)), yaw


def heading(yaw):
    return Matrix.Rotation(yaw, 3, "Z")


def stepping_target(time, stance, phase):
    """Choose the next world-space landing before swinging off the old one."""
    stages = (
        (.83, 1.75, 2, .105),
        (1.75, 3.40, 2, .219),
        (4.29, 5.30, 3, .115),
        (5.30, 6.95, 2, .219),
        (6.95, 7.74, 2, .105),
    )
    previous = 0

    def landing(at):
        position, yaw = route(at)
        return position + heading(yaw) @ stance

    for start, end, steps, lift in stages:
        if time < start:
            return landing(previous)
        if time <= end:
            cycle = (end - start) / steps
            old = start
            for i in range(steps):
                # On a straight walk the four offsets give a lateral sequence
                # with at least two paws supporting the cat throughout.
                takeoff = start + (i + .75 * phase) * cycle
                touchdown = takeoff + .30 * cycle
                target_time = min(touchdown + .25 * cycle, end) if i < steps - 1 else end
                if time < takeoff:
                    return landing(old)
                if time < touchdown:
                    progress = (time - takeoff) / (touchdown - takeoff)
                    target = landing(old).lerp(landing(target_time), ease(progress))
                    target.z += lift * sin(pi * progress) ** 2
                    return target
                old = target_time
            return landing(end)
        previous = end
    return landing(previous)


def pose_segment(start, end, width, depth, overlap):
    delta = end - start
    return (start.lerp(end, .5), delta.to_track_quat("Z", "Y").to_euler(),
            Vector((width, depth, delta.length / 2 + overlap)))


def capture(obj):
    return obj.location.copy(), obj.rotation_euler.copy(), obj.scale.copy()


def blend_pose(obj, rest, walking, amount):
    obj.location = rest[0].lerp(walking[0], amount)
    obj.rotation_euler = rest[1].to_quaternion().slerp(walking[1].to_quaternion(), amount).to_euler(
        "XYZ", obj.rotation_euler
    )
    obj.scale = rest[2].lerp(walking[2], amount)


def key_pose(obj, frame, paths=("location", "rotation_euler", "scale")):
    for path in paths:
        obj.keyframe_insert(data_path=path, frame=frame, group=obj.name)


def folder_mesh(pivot_fn, material_fn, root):
    folder = pivot_fn("ProjectFolder", (0, 0, 0), root)
    cover = material_fn("Folder / deep teal", "237677", .47)
    front = material_fn("Folder / teal", "479695", .49)
    paper = material_fn("Folder / ivory card", "FFEDC9", .65)
    rule = material_fn("Folder / ink rule", "245455", .64)

    def tile(name, location, dimensions, mat, radius):
        bpy.ops.mesh.primitive_cube_add(size=1)
        obj = bpy.context.object
        obj.name = name
        obj.parent = folder
        obj.location = location
        obj.dimensions = dimensions
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        bevel = obj.modifiers.new("Rounded corners", "BEVEL")
        bevel.width = radius
        bevel.segments = 3
        bpy.ops.object.modifier_apply(modifier=bevel.name)
        obj.data.materials.append(mat)

    tile("Folder back", (0, .030, -.02), (.66, .045, .42), cover, .017)
    tile("Folder tab", (.185, .029, .201), (.235, .038, .075), cover, .015)
    tile("Ivory project card", (-.018, .008, .060), (.553, .031, .314), paper, .009)
    tile("Folder reverse label", (-.115, .055, -.075), (.218, .009, .094), paper, .004)
    tile("Folder reverse rule", (-.125, .061, -.075), (.124, .007, .015), rule, .003)
    tile("Folder front", (0, -.028, -.068), (.66, .054, .326), front, .018)
    tile("Project label", (-.115, -.056, -.075), (.234, .010, .112), paper, .004)
    tile("Project label top line", (-.122, -.062, -.056), (.145, .007, .013), rule, .003)
    tile("Project label lower line", (-.147, -.062, -.092), (.093, .007, .013), rule, .003)
    return folder


def author_fetch(scene, root, motion, body, torso, bib, scarf, head, tail, legs, material, pivot):
    scene.render.fps = FPS
    folder = folder_mesh(pivot, material, root)
    parts = [motion, body, torso, bib, scarf, head, tail, folder]
    parts.extend(obj for _, _, *limb in legs for obj in limb)
    rest = {obj: capture(obj) for obj in parts}
    rest[tail] = (tail.location.copy(), Euler((.05, -.02, -.06)), tail.scale.copy())
    options = {
        ("Left", True): (.0, .39),
        ("Left", False): (.28, .37),
        ("Right", True): (.53, .39),
        ("Right", False): (.84, .37),
    }

    def head_pose(time, height, present):
        nod = ease_between(time, 3.40, 3.92) * (1 - ease_between(time, 3.95, 4.29))
        location = NECK_REST.lerp(Vector((-.03, -.53, .94 + height)), walking_amount(time))
        location += Vector((0, -.14 * nod - .13 * present, -.50 * nod - .05 * present))
        rotation = Euler((.65 * nod + .075 * present, 0, 0))
        return location, rotation

    carry_offset = Vector((.05, -.792, .124))
    carry_turn = Euler((.21, 0, -.63)).to_matrix()

    def carried_transform(position, yaw, neck, neck_rotation):
        face = heading(yaw) @ neck_rotation.to_matrix()
        center = position + heading(yaw) @ neck + face @ carry_offset
        return center, (face @ carry_turn).to_quaternion()

    contact = 3.92
    pickup_position, pickup_yaw = route(contact)
    neck, neck_rotation = head_pose(contact, 0, 0)
    ground_center, _ = carried_transform(pickup_position, pickup_yaw, neck, neck_rotation)
    ground_center.z = .055
    ground_rotation = Euler((pi / 2, 0, -.12)).to_quaternion()
    present_rotation = Euler((-.105, -.075, -.10)).to_quaternion()

    for frame in range(LAST_FRAME + 1):
        time = frame / FPS
        amount = walking_amount(time)
        presentation = ease_between(time, 8.04, 8.22) * (1 - ease_between(time, 8.76, 9.17))
        paw_raise = ease_between(time, 8.00, 8.24) * (1 - ease_between(time, 8.78, 9.25))
        position, yaw = route(time)
        gait = ((1.75 <= time <= 3.40) or (5.30 <= time <= 6.95))
        cycle_start = 1.75 if time < 4 else 5.30
        gait_fade = sin(pi * max(0, min((time - cycle_start) / 1.65, 1))) if gait else 0
        bob = .039 * gait_fade * sin(12 * pi * (time - cycle_start) / 1.65)
        roll = .037 * gait_fade * sin(6 * pi * (time - cycle_start) / 1.65)
        distance = .045 * sin(pi * ease_between(time, .05, .83))
        motion.location = position
        motion.rotation_euler = (0, 0, yaw)
        body.location = (0, -.045 * amount, .49 + amount * (.29 + bob) - distance)
        body.rotation_euler = (0, roll, 0)
        blend_pose(torso, rest[torso], (Vector((-.02, .09, -.015)), Euler((0, 0, 0)),
                                      Vector((.46, .88, .392))), amount)
        blend_pose(bib, rest[bib], (Vector((0, -.44, -.102)), Euler((.39, 0, 0)),
                                  Vector((.378, .205, .298))), amount)
        blend_pose(scarf, rest[scarf], (Vector((0, -.37, -.12)), Euler((.235, 0, 0)),
                                      Vector((.78, .82, .75))), amount)
        neck, neck_rotation = head_pose(time, bob, presentation)
        head.location = neck
        head.rotation_euler = neck_rotation
        blend_pose(tail, rest[tail], (Vector((.19, .66, .70 + bob)),
            Euler((.12, -.14, 1.25 + .17 * sin(time * 6))), Vector((.79, .79, .79))), amount)

        for side, rear, upper, lower, foot in legs:
            phase, width = options[side, rear]
            sign = -1 if side == "Left" else 1
            back = .61 if rear else -.57
            neutral = Vector((sign * width, back, .134 if rear else .148))
            landing = stepping_target(time, neutral, phase)
            stance = heading(-yaw) @ (landing - position)
            reaching = paw_raise if (side == "Left" and not rear) else 0
            seated = rest[foot][0] + Vector((-.06, -.43, .74)) * reaching
            foot.location = seated.lerp(stance, amount)
            foot.rotation_euler = (.26 * reaching, -.17 * reaching, .12 * reaching)
            foot.scale = rest[foot][2].lerp(Vector((1, 1, 1)) if rear else Vector((.69, .69, .96)), amount)
            joint = Vector((sign * (.33 if rear else .35), .52 if rear else -.40, .825 + bob))
            ankle = Vector((foot.location.x, foot.location.y, foot.location.z + .025))
            bend = joint.lerp(ankle, .47)
            bend.y += -.19 if rear else .117
            bend.x += sign * (.047 if rear else .028)
            upper_width = .246 if rear else .158
            upper_depth = .302 if rear else .164
            walk_upper = pose_segment(joint, bend, upper_width, upper_depth, .129)
            walk_lower = pose_segment(bend, ankle, .123 if rear else .131, .128, .106)
            blend_pose(upper, rest[upper], walk_upper, amount)
            blend_pose(lower, rest[lower], walk_lower, amount)
            if reaching:
                shoulder = Vector((-.32, -.25, .90))
                elbow = Vector((-.41, -.44, .62)).lerp(ankle, .30)
                blend_pose(upper, rest[upper], pose_segment(shoulder, elbow, .19, .183, .118), reaching)
                blend_pose(lower, rest[lower], pose_segment(elbow, ankle, .15, .148, .12), reaching)

        center, rotation = carried_transform(position, yaw, neck, neck_rotation)
        grab = ease_between(time, 3.84, 4.08)
        center = ground_center.lerp(center, grab)
        rotation = ground_rotation.slerp(rotation, ease_between(time, 3.97, 4.16))
        offered = Vector((-.10, -1.17, 1.12))
        center = center.lerp(offered, presentation)
        rotation = rotation.slerp(present_rotation, presentation)
        if time > 8.76:
            elapsed = time - 8.76
            center = offered + Vector((.16 * elapsed, -.13 * elapsed, max(-1.065, -7.1 * elapsed ** 2)))
            rotation = present_rotation.slerp(ground_rotation, ease_between(time, 8.76, 9.17))
        folder.location = center
        folder.rotation_euler = rotation.to_euler("XYZ", folder.rotation_euler)
        visibility = ease_between(time, .57, .88) * (1 - ease_between(time, 9.14, 9.34))
        # A zero-scale parent makes the exporter lose child transforms.
        folder.scale = (max(.001, visibility),) * 3

        for part in parts:
            key_pose(part, frame)

    for frame, name in (
        (0, "Seated"), (20, "Crouch and turn"), (42, "Stalk"), (82, "Reach the folder"),
        (94, "Pick up"), (127, "Carry home"), (167, "Turn front"), (186, "Sit"),
        (202, "Present to viewer"), (210, "Release"), (228, "Seated"),
    ):
        scene.timeline_markers.new(name, frame=frame)
    fetch_parts = {}
    for part in parts:
        action = part.animation_data.action
        action.name = f"Fetch / {part.name}"
        action.use_fake_user = True
        fetch_parts[part] = action
    scene.frame_set(0)
    return fetch_parts


def walking_amount(time):
    return ease_between(time, .04, .91) * (1 - ease_between(time, 7.74, 8.10))


def arrange_animation(fetch_actions, idle_actions, idle_start):
    for part, fetch in fetch_actions.items():
        animation = part.animation_data
        animation.action = None
        for track in list(animation.nla_tracks):
            animation.nla_tracks.remove(track)
        if part in idle_actions:
            idle_track = animation.nla_tracks.new()
            idle_track.name = "Idle"
            idle_strip = idle_track.strips.new(idle_actions[part].name, idle_start, idle_actions[part])
            idle_strip.extrapolation = "NOTHING"
        fetch_track = animation.nla_tracks.new()
        fetch_track.name = "Fetch"
        fetch_strip = fetch_track.strips.new(fetch.name, 0, fetch)
        fetch_strip.extrapolation = "NOTHING"
