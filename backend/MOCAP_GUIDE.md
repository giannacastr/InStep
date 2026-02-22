# Motion Capture Reference System Guide

This system allows you to use pre-recorded motion capture data as reference instead of extracting poses from videos. This provides **pristine, high-quality reference data** for more accurate grading.

## Supported Formats

### 1. CMU Graphics Lab Motion Capture Database
- **Format**: JSON (converted from BVH)
- **Source**: http://mocap.cs.cmu.edu/
- **Example**: Download a dance animation, convert BVH to JSON

### 2. AIST++ Dance Motion Dataset
- **Format**: JSON
- **Source**: https://google.github.io/aistplusplus_dataset/
- **Features**: 10.1 million frames, 1,408 dance sequences, 10 genres

### 3. Adobe Mixamo
- **Format**: FBX → JSON (conversion via Blender script)
- **Source**: https://www.mixamo.com/
- **Conversion**: Use `blender_fbx_to_json.py` inside Blender (see below)

### 4. Cloud API Outputs
- **DeepMotion Animate 3D API**: JSON format
- **Move AI API**: JSON/CSV format
- **RADiCAL Core API**: JSON format

## File organization (FBX → JSON)

**Recommended layout:**

```
InStep/
  backend/
    blender_fbx_to_json.py   # Run this script inside Blender
  references/                 # or mocap_sources/
    fbx/                      # Put all .fbx files here (Mixamo, etc.)
      dance_01.fbx
      dance_02.fbx
    json/                     # Output: one .json per .fbx (same name)
      dance_01.json
      dance_02.json
```

**How to run:**

1. **Batch (recommended):** Put every FBX in one folder. In the script set:
   - `FBX_INPUT_PATH = "C:/path/to/InStep/references/fbx"`
   - `JSON_OUTPUT_PATH = "C:/path/to/InStep/references/json"`
   Then in Blender: Scripting workspace → Open `blender_fbx_to_json.py` → Run Script.  
   All `.fbx` in `fbx/` are converted; each writes to `json/<name>.json`.

2. **Single file:** Set `FBX_FILE_PATH = "C:/path/to/dance_01.fbx"` (and optionally `JSON_OUTPUT_PATH`). Run script once per file.

**Why one folder for FBX and one for JSON?**

- Keeps source FBX untouched.
- Clear place for InStep to load references from (`references/json/`).
- Batch run converts everything in one go; add new FBX later and re-run.

**Using the JSON with InStep:** Point `mocap_ref_path` (or your loader) at a file in `references/json/`, e.g. `references/json/dance_01.json`. The format matches `sample_mocap_template.json` and `mocap_loader.py`.

---

## FBX → JSON with Blender

Use the script **inside Blender** (Scripting tab → Open `backend/blender_fbx_to_json.py` → Run Script).

1. **Single file:** Set at top of script:
   - `FBX_FILE_PATH = "C:/full/path/to/your/file.fbx"`
   - Optionally `JSON_OUTPUT_PATH = "C:/path/to/output_dir"`
2. **Batch:** Set:
   - `FBX_INPUT_PATH = "C:/path/to/folder/with/fbx_files"`
   - `JSON_OUTPUT_PATH = "C:/path/to/output_folder"` (or leave empty to write next to each FBX)
3. Run the script. It will:
   - Import each FBX (clearing the scene first in batch),
   - Step through the timeline frame-by-frame,
   - Read global 3D positions of armature bone heads,
   - Map Mixamo/FBX bone names to the template joint names (Hips, LeftUpLeg, …),
   - Export a JSON with `{"frames": [{"time": t, "joints": {...}}, ...]}` matching `sample_mocap_template.json`.

**Config at top of script:**

- `EXPORT_FPS`: FPS used for `time` (seconds). Default 30; use 0 to use Blender scene FPS.
- `COORDINATE_SYSTEM`: `"y_up"` (default) converts Blender Z-up to Y-up so heights match the InStep template; use `"blender"` to keep Blender’s axes.

**Bone names:** The script maps common Mixamo/FBX names (with optional `mixamorig:` prefix) to: Hips, LeftUpLeg, RightUpLeg, LeftLeg, RightLeg, LeftFoot, RightFoot, Spine, Spine1, Neck, Head, LeftShoulder, LeftArm, LeftForeArm, LeftHand, RightShoulder, RightArm, RightForeArm, RightHand. Unmapped bones are skipped.

---

## JSON Format Examples

### CMU Format
```json
{
  "frames": [
    {
      "time": 0.0,
      "joints": {
        "Hips": [0.0, 1.0, 0.0],
        "LeftUpLeg": [-0.1, 0.9, 0.0],
        "RightUpLeg": [0.1, 0.9, 0.0],
        "LeftLeg": [-0.1, 0.5, 0.0],
        "RightLeg": [0.1, 0.5, 0.0],
        "LeftFoot": [-0.1, 0.1, 0.0],
        "RightFoot": [0.1, 0.1, 0.0],
        "Spine": [0.0, 1.2, 0.0],
        "Spine1": [0.0, 1.4, 0.0],
        "Neck": [0.0, 1.6, 0.0],
        "Head": [0.0, 1.8, 0.0],
        "LeftShoulder": [-0.2, 1.5, 0.0],
        "LeftArm": [-0.4, 1.3, 0.0],
        "LeftForeArm": [-0.6, 1.1, 0.0],
        "RightShoulder": [0.2, 1.5, 0.0],
        "RightArm": [0.4, 1.3, 0.0],
        "RightForeArm": [0.6, 1.1, 0.0]
      }
    }
  ]
}
```

### AIST++ Format
```json
{
  "fps": 60,
  "poses": [
    {
      "frame": 0,
      "joints": {
        "pelvis": [0.0, 1.0, 0.0],
        "l_hip": [-0.1, 0.9, 0.0],
        "r_hip": [0.1, 0.9, 0.0],
        "l_knee": [-0.1, 0.5, 0.0],
        "r_knee": [0.1, 0.5, 0.0],
        "l_ankle": [-0.1, 0.1, 0.0],
        "r_ankle": [0.1, 0.1, 0.0],
        "spine_1": [0.0, 1.2, 0.0],
        "spine_2": [0.0, 1.4, 0.0],
        "neck": [0.0, 1.6, 0.0],
        "head": [0.0, 1.8, 0.0],
        "l_shoulder": [-0.2, 1.5, 0.0],
        "l_elbow": [-0.4, 1.3, 0.0],
        "l_wrist": [-0.6, 1.1, 0.0],
        "r_shoulder": [0.2, 1.5, 0.0],
        "r_elbow": [0.4, 1.3, 0.0],
        "r_wrist": [0.6, 1.1, 0.0]
      }
    }
  ]
}
```

## Usage

### Python API

```python
from mocap_reference import analyze_with_mocap_reference

result = analyze_with_mocap_reference(
    mocap_ref_path="references/dance_move_cmu.json",
    prac_video_path="uploads/practice/user_video.mp4",
    offset=0.5,  # From audio sync
    mocap_format="cmu",  # Optional: auto-detected if not specified
    mocap_fps=30.0
)

print(f"Overall Score: {result['overallScore']}%")
for move in result['moves']:
    print(f"{move['timestamp']}: {move['status']} - {move['feedback']}")
```

### REST API

```bash
POST /analyze-mocap
Content-Type: application/json

{
  "mocap_ref_path": "references/dance_move_cmu.json",
  "prac_path": "uploads/practice/user_video.mp4",
  "offset": 0.5,
  "mocap_format": "cmu",  # Optional
  "mocap_fps": 30.0
}
```

### Loading and Converting Data

```python
from mocap_loader import load_mocap_data, mocap_to_dataframe

# Load mocap data
poses = load_mocap_data("dance_move.json", format_type="cmu", fps=30.0)

# Convert to DataFrame for analysis
df = mocap_to_dataframe(poses)

# Analyze with pandas
print(df.describe())
print(df.groupby('timestamp').mean())

# Convert back to poses
from mocap_loader import dataframe_to_poses
poses_restored = dataframe_to_poses(df)
```

## Benefits

1. **Higher Quality**: Mocap data is clean, precise, and noise-free
2. **Consistent**: Same reference data every time (no video quality variations)
3. **Professional**: Uses industry-standard motion capture data
4. **Scalable**: Can build a library of reference moves
5. **Accurate**: No pose detection errors in reference (only in practice video)

## Next Steps

1. **Download Sample Data**: Get a dance animation from Mixamo or CMU database
2. **Convert Format**: If needed, convert BVH/FBX to JSON
3. **Test**: Use `/analyze-mocap` endpoint with sample practice video
4. **Build Library**: Collect reference moves for common dance styles

## Converting BVH to JSON

If you have BVH files from CMU database, you can convert them:

```python
# Example conversion script (requires bvh library)
import bvh
import json

bvh_data = bvh.Bvh("animation.bvh")
frames = []
for frame_idx in range(len(bvh_data.frames)):
    frame = {"time": frame_idx / bvh_data.frame_time, "joints": {}}
    for joint in bvh_data.get_joints():
        frame["joints"][joint.name] = joint.get_position(frame_idx).tolist()
    frames.append(frame)

with open("animation.json", "w") as f:
    json.dump({"frames": frames}, f)
```

## Converting FBX to JSON

For Mixamo FBX files, you'll need an FBX parser:

```python
# Example using pyfbx (may need manual installation)
import pyfbx
import json

fbx = pyfbx.Fbx("animation.fbx")
# Extract joint positions per frame
# Convert to JSON format
```

## Integration with Existing System

The mocap system is designed as a drop-in replacement:
- Uses same pose format (33 MediaPipe landmarks)
- Same analysis functions (`analyze_move_quality`, etc.)
- Same output format
- Can be used alongside video-based references
