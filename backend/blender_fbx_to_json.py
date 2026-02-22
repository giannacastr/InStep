"""
Blender script: FBX → InStep mocap JSON

Run this script INSIDE Blender (Scripting workspace → Open this file → Run Script).

- Loads a single .fbx or all .fbx files in a folder.
- Steps through the animation frame-by-frame.
- Exports global 3D positions of armature bones.
- Writes JSON in the same format as sample_mocap_template.json for mocap_loader.py.

File organization (recommended):
  input_fbx/   → put your .fbx files here (or set FBX_INPUT_PATH)
  output_json/ → converted .json files appear here (or set JSON_OUTPUT_PATH)

Single file: set FBX_FILE_PATH and run. Batch: set FBX_INPUT_PATH (folder) and run.
"""

import bpy
import json
import os
from pathlib import Path
from mathutils import Vector

# -----------------------------------------------------------------------------
# CONFIGURATION – set these before running in Blender
# -----------------------------------------------------------------------------

# Option A: Single file conversion
FBX_FILE_PATH = ""  # e.g. "C:/mocap/dance_01.fbx"

# Option B: Batch – convert all .fbx in a folder
FBX_INPUT_PATH = "backend/references/fbx"  # e.g. "C:/mocap/fbx"
JSON_OUTPUT_PATH = "backend/references/json"  # e.g. "C:/mocap/json" (default: same as FBX_INPUT_PATH if empty)

# FPS of the Blender scene (used for "time" in seconds). Leave 0 to use scene FPS.
EXPORT_FPS = 30  # 0 = use bpy.context.scene.render.fps

# Coordinate system for exported JSON. InStep template uses Y-up (y = height).
# "blender" = export as-is (Blender Z-up: x, y, z).
# "y_up"    = convert to Y-up for InStep: [x, z, -y] so y becomes height.
COORDINATE_SYSTEM = "y_up"

# Bone name mapping: FBX/Mixamo bone names → InStep template joint names
# Mixamo often uses prefix like "mixamorig:" or "Armature|mixamorig|"
CANONICAL_JOINTS = [
    "Hips", "LeftUpLeg", "RightUpLeg", "LeftLeg", "RightLeg",
    "LeftFoot", "RightFoot", "Spine", "Spine1", "Neck", "Head",
    "LeftShoulder", "LeftArm", "LeftForeArm", "LeftHand",
    "RightShoulder", "RightArm", "RightForeArm", "RightHand"
]

def _normalize_bone_name(name):
    """Strip common Mixamo/FBX prefixes and return clean bone name."""
    s = name
    for prefix in ("mixamorig:", "mixamorig|", "Armature|", "mixamo|", ":"):
        if prefix in s:
            s = s.split(prefix, 1)[-1]
    return s.strip()

def _match_canonical(fbx_bone_name):
    """Map FBX bone name to canonical joint name, or None if no match."""
    normalized = _normalize_bone_name(fbx_bone_name)
    if normalized in CANONICAL_JOINTS:
        return normalized
    # Try case-insensitive and without extra suffixes
    base = normalized.split(".")[0]
    for canon in CANONICAL_JOINTS:
        if base.lower() == canon.lower():
            return canon
    return None

def get_armature():
    """Return the first armature in the scene."""
    for obj in bpy.context.scene.objects:
        if obj.type == "ARMATURE":
            return obj
    return None

def get_bone_world_head(arm_obj, bone_name):
    """Get world-space position of the bone head for the current frame."""
    if arm_obj is None or bone_name not in arm_obj.pose.bones:
        return None
    pose_bone = arm_obj.pose.bones[bone_name]
    # Head in bone local space is (0,0,0); in world = arm_obj.matrix_world @ pose_bone.matrix @ Vector((0,0,0))
    local_head = Vector((0, 0, 0))
    world_head = arm_obj.matrix_world @ (pose_bone.matrix @ local_head)
    x, y, z = world_head.x, world_head.y, world_head.z
    if COORDINATE_SYSTEM == "y_up":
        # Blender is Z-up; InStep template expects Y-up: export as (x, z, -y)
        return [x, z, -y]
    return [x, y, z]

def collect_frame_joints(arm_obj, frame_num):
    """Collect all canonical joint positions for current frame."""
    bpy.context.scene.frame_set(frame_num)
    joints = {}
    for bone in arm_obj.pose.bones:
        canon = _match_canonical(bone.name)
        if canon is None:
            continue
        pos = get_bone_world_head(arm_obj, bone.name)
        if pos is not None:
            joints[canon] = pos
    return joints

def get_timeline_range():
    """Return (start_frame, end_frame) from the scene."""
    start = bpy.context.scene.frame_start
    end = bpy.context.scene.frame_end
    return int(start), int(end)

def get_export_fps():
    if EXPORT_FPS and EXPORT_FPS > 0:
        return EXPORT_FPS
    return bpy.context.scene.render.fps

def clear_scene_objects():
    """Remove all objects (used before importing a new FBX)."""
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

def export_fbx_to_json(fbx_path, json_path, fps):
    """
    Load one FBX, export pose_keypoints_3d per frame to JSON.
    JSON format: { "frames": [ { "time": t, "joints": { "Hips": [x,y,z], ... } }, ... ] }
    """
    fbx_path = os.path.abspath(fbx_path)
    if not os.path.isfile(fbx_path):
        raise FileNotFoundError(f"FBX file not found: {fbx_path}")

    # Clear and import
    clear_scene_objects()
    bpy.ops.import_scene.fbx(filepath=fbx_path)

    arm = get_armature()
    if arm is None:
        raise RuntimeError("No armature found in the FBX. Ensure the FBX contains a rig.")

    start_frame, end_frame = get_timeline_range()
    frames_out = []

    for frame_num in range(start_frame, end_frame + 1):
        joints = collect_frame_joints(arm, frame_num)
        if not joints:
            continue
        t = (frame_num - start_frame) / fps
        frames_out.append({
            "time": round(t, 6),
            "joints": {k: [round(v[0], 6), round(v[1], 6), round(v[2], 6)] for k, v in joints.items()}
        })

    os.makedirs(os.path.dirname(json_path) or ".", exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"frames": frames_out}, f, indent=2)

    return len(frames_out)

def run_single():
    """Convert one FBX file (set FBX_FILE_PATH)."""
    if not FBX_FILE_PATH or not FBX_FILE_PATH.strip():
        print("Set FBX_FILE_PATH at the top of the script and run again.")
        return
    fps = get_export_fps()
    base = os.path.splitext(os.path.basename(FBX_FILE_PATH))[0]
    out_dir = JSON_OUTPUT_PATH or os.path.dirname(FBX_FILE_PATH)
    json_path = os.path.join(out_dir, base + ".json")
    n = export_fbx_to_json(FBX_FILE_PATH, json_path, fps)
    print(f"Exported {n} frames to {json_path}")

def run_batch():
    """Convert all .fbx files in FBX_INPUT_PATH."""
    if not FBX_INPUT_PATH or not os.path.isdir(FBX_INPUT_PATH):
        print("Set FBX_INPUT_PATH to a folder containing .fbx files and run again.")
        return
    out_dir = JSON_OUTPUT_PATH or FBX_INPUT_PATH
    fps = get_export_fps()
    count = 0
    for name in sorted(os.listdir(FBX_INPUT_PATH)):
        if not name.lower().endswith(".fbx"):
            continue
        fbx_path = os.path.join(FBX_INPUT_PATH, name)
        if not os.path.isfile(fbx_path):
            continue
        base = os.path.splitext(name)[0]
        json_path = os.path.join(out_dir, base + ".json")
        try:
            n = export_fbx_to_json(fbx_path, json_path, fps)
            print(f"OK: {name} -> {base}.json ({n} frames)")
            count += 1
        except Exception as e:
            print(f"SKIP: {name} - {e}")
    print(f"Batch done. Converted {count} files.")

# -----------------------------------------------------------------------------
# ENTRY POINT – run single file or batch
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    if FBX_FILE_PATH and FBX_FILE_PATH.strip():
        run_single()
    elif FBX_INPUT_PATH and FBX_INPUT_PATH.strip():
        run_batch()
    else:
        print("Set either FBX_FILE_PATH (single file) or FBX_INPUT_PATH (folder) at the top of the script.")
