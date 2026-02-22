"""
Motion Capture Data Loader for Pre-Recorded Dance References

Supports multiple motion capture formats:
- CMU Graphics Lab Motion Capture Database (BVH/JSON)
- AIST++ Dance Motion Dataset (JSON)
- Mixamo FBX (via conversion to JSON)
- Custom JSON formats from cloud APIs (DeepMotion, Move AI, RADiCAL)

Converts all formats to MediaPipe-compatible pose format (33 landmarks).
"""
import os
import json
import numpy as np
from typing import List, Dict, Optional, Tuple
import pandas as pd


# MediaPipe Pose landmark indices (33 landmarks)
MP_LANDMARKS = {
    'nose': 0, 'left_eye_inner': 1, 'left_eye': 2, 'left_eye_outer': 3,
    'right_eye_inner': 4, 'right_eye': 5, 'right_eye_outer': 6,
    'left_ear': 7, 'right_ear': 8,
    'mouth_left': 9, 'mouth_right': 10,
    'left_shoulder': 11, 'right_shoulder': 12,
    'left_elbow': 13, 'right_elbow': 14,
    'left_wrist': 15, 'right_wrist': 16,
    'left_pinky': 17, 'right_pinky': 18,
    'left_index': 19, 'right_index': 20,
    'left_thumb': 21, 'right_thumb': 22,
    'left_hip': 23, 'right_hip': 24,
    'left_knee': 25, 'right_knee': 26,
    'left_ankle': 27, 'right_ankle': 28,
    'left_heel': 29, 'right_heel': 30,
    'left_foot_index': 31, 'right_foot_index': 32
}

# Common skeleton joint mappings for different formats
SKELETON_MAPPINGS = {
    'cmu': {
        'Hips': 'hip_center',
        'LeftUpLeg': 'left_hip',
        'LeftLeg': 'left_knee',
        'LeftFoot': 'left_ankle',
        'RightUpLeg': 'right_hip',
        'RightLeg': 'right_knee',
        'RightFoot': 'right_ankle',
        'Spine': 'spine_mid',
        'Spine1': 'spine_upper',
        'Neck': 'neck',
        'Head': 'nose',
        'LeftShoulder': 'left_shoulder',
        'LeftArm': 'left_elbow',
        'LeftForeArm': 'left_wrist',
        'LeftHand': 'left_wrist',
        'RightShoulder': 'right_shoulder',
        'RightArm': 'right_elbow',
        'RightForeArm': 'right_wrist',
        'RightHand': 'right_wrist',
    },
    'aist': {
        'pelvis': 'hip_center',
        'l_hip': 'left_hip',
        'l_knee': 'left_knee',
        'l_ankle': 'left_ankle',
        'r_hip': 'right_hip',
        'r_knee': 'right_knee',
        'r_ankle': 'right_ankle',
        'spine_1': 'spine_mid',
        'spine_2': 'spine_upper',
        'neck': 'neck',
        'head': 'nose',
        'l_shoulder': 'left_shoulder',
        'l_elbow': 'left_elbow',
        'l_wrist': 'left_wrist',
        'r_shoulder': 'right_shoulder',
        'r_elbow': 'right_elbow',
        'r_wrist': 'right_wrist',
    },
    'mixamo': {
        'Hips': 'hip_center',
        'LeftUpLeg': 'left_hip',
        'LeftLeg': 'left_knee',
        'LeftFoot': 'left_ankle',
        'RightUpLeg': 'right_hip',
        'RightLeg': 'right_knee',
        'RightFoot': 'right_ankle',
        'Spine': 'spine_mid',
        'Spine1': 'spine_upper',
        'Neck': 'neck',
        'Head': 'nose',
        'LeftShoulder': 'left_shoulder',
        'LeftArm': 'left_elbow',
        'LeftForeArm': 'left_wrist',
        'RightShoulder': 'right_shoulder',
        'RightArm': 'right_elbow',
        'RightForeArm': 'right_wrist',
    }
}


def map_to_mediapipe_landmarks(joint_positions: Dict[str, np.ndarray], 
                                skeleton_type: str = 'cmu') -> np.ndarray:
    """
    Map skeleton joints from various formats to MediaPipe 33-landmark format.
    
    Args:
        joint_positions: Dict mapping joint names to 3D positions (x, y, z)
        skeleton_type: Type of skeleton ('cmu', 'aist', 'mixamo', 'mediapipe')
    
    Returns:
        numpy array of shape (33, 3) with MediaPipe landmark positions
    """
    landmarks = np.zeros((33, 3))
    
    if skeleton_type == 'mediapipe':
        # Already in MediaPipe format
        if isinstance(joint_positions, np.ndarray):
            if joint_positions.shape[0] == 33:
                return joint_positions
        # If dict, assume it's already mapped
        for i in range(33):
            if i in joint_positions:
                landmarks[i] = joint_positions[i]
        return landmarks
    
    mapping = SKELETON_MAPPINGS.get(skeleton_type, SKELETON_MAPPINGS['cmu'])
    
    # Helper to get joint position or estimate from parent
    def get_pos(joint_name: str, fallback: Optional[str] = None) -> Optional[np.ndarray]:
        if joint_name in joint_positions:
            return joint_positions[joint_name]
        if fallback and fallback in joint_positions:
            return joint_positions[fallback]
        return None
    
    # Core body landmarks (required)
    hip_center = get_pos('Hips') or get_pos('pelvis') or get_pos('hip_center')
    if hip_center is None:
        # Estimate from left/right hips
        left_hip = get_pos('LeftUpLeg') or get_pos('l_hip') or get_pos('left_hip')
        right_hip = get_pos('RightUpLeg') or get_pos('r_hip') or get_pos('right_hip')
        if left_hip is not None and right_hip is not None:
            hip_center = (left_hip + right_hip) / 2
        else:
            return None  # Can't proceed without hip center
    
    # Hips (23, 24)
    left_hip_pos = get_pos('LeftUpLeg') or get_pos('l_hip') or get_pos('left_hip')
    right_hip_pos = get_pos('RightUpLeg') or get_pos('r_hip') or get_pos('right_hip')
    if left_hip_pos is None:
        left_hip_pos = hip_center + np.array([-0.1, 0, 0])  # Estimate
    if right_hip_pos is None:
        right_hip_pos = hip_center + np.array([0.1, 0, 0])  # Estimate
    landmarks[23] = left_hip_pos
    landmarks[24] = right_hip_pos
    
    # Legs
    landmarks[25] = get_pos('LeftLeg') or get_pos('l_knee') or get_pos('left_knee') or landmarks[23] + np.array([0, 0.3, 0])
    landmarks[26] = get_pos('RightLeg') or get_pos('r_knee') or get_pos('right_knee') or landmarks[24] + np.array([0, 0.3, 0])
    landmarks[27] = get_pos('LeftFoot') or get_pos('l_ankle') or get_pos('left_ankle') or landmarks[25] + np.array([0, 0.3, 0])
    landmarks[28] = get_pos('RightFoot') or get_pos('r_ankle') or get_pos('right_ankle') or landmarks[26] + np.array([0, 0.3, 0])
    landmarks[29] = landmarks[27] + np.array([0, 0.05, 0])  # Heel estimate
    landmarks[30] = landmarks[28] + np.array([0, 0.05, 0])
    landmarks[31] = landmarks[27] + np.array([0, -0.05, 0])  # Foot index estimate
    landmarks[32] = landmarks[28] + np.array([0, -0.05, 0])
    
    # Spine and head
    spine_mid = get_pos('Spine') or get_pos('spine_1') or hip_center + np.array([0, 0.2, 0])
    spine_upper = get_pos('Spine1') or get_pos('spine_2') or spine_mid + np.array([0, 0.2, 0])
    neck = get_pos('Neck') or get_pos('neck') or spine_upper + np.array([0, 0.1, 0])
    head = get_pos('Head') or get_pos('head') or neck + np.array([0, 0.15, 0])
    
    # Nose (0) - use head position
    landmarks[0] = head
    
    # Shoulders (11, 12)
    left_shoulder = get_pos('LeftShoulder') or get_pos('l_shoulder') or get_pos('left_shoulder')
    right_shoulder = get_pos('RightShoulder') or get_pos('r_shoulder') or get_pos('right_shoulder')
    if left_shoulder is None:
        left_shoulder = neck + np.array([-0.15, 0, 0])
    if right_shoulder is None:
        right_shoulder = neck + np.array([0.15, 0, 0])
    landmarks[11] = left_shoulder
    landmarks[12] = right_shoulder
    
    # Arms
    landmarks[13] = get_pos('LeftArm') or get_pos('l_elbow') or get_pos('left_elbow') or landmarks[11] + np.array([-0.2, 0.2, 0])
    landmarks[14] = get_pos('RightArm') or get_pos('r_elbow') or get_pos('right_elbow') or landmarks[12] + np.array([0.2, 0.2, 0])
    landmarks[15] = get_pos('LeftForeArm') or get_pos('LeftHand') or get_pos('l_wrist') or get_pos('left_wrist') or landmarks[13] + np.array([-0.2, 0.2, 0])
    landmarks[16] = get_pos('RightForeArm') or get_pos('RightHand') or get_pos('r_wrist') or get_pos('right_wrist') or landmarks[14] + np.array([0.2, 0.2, 0])
    
    # Hand landmarks (estimate from wrist)
    landmarks[17] = landmarks[15] + np.array([-0.02, 0, 0])  # Left pinky
    landmarks[18] = landmarks[16] + np.array([0.02, 0, 0])  # Right pinky
    landmarks[19] = landmarks[15] + np.array([-0.03, 0, 0])  # Left index
    landmarks[20] = landmarks[16] + np.array([0.03, 0, 0])  # Right index
    landmarks[21] = landmarks[15] + np.array([-0.01, 0, 0])  # Left thumb
    landmarks[22] = landmarks[16] + np.array([0.01, 0, 0])  # Right thumb
    
    # Face landmarks (estimate from head)
    head_offset = head - neck
    landmarks[1] = head + np.array([-0.02, -0.02, 0])  # Left eye inner
    landmarks[2] = head + np.array([-0.03, -0.01, 0])  # Left eye
    landmarks[3] = head + np.array([-0.04, 0, 0])  # Left eye outer
    landmarks[4] = head + np.array([0.02, -0.02, 0])  # Right eye inner
    landmarks[5] = head + np.array([0.03, -0.01, 0])  # Right eye
    landmarks[6] = head + np.array([0.04, 0, 0])  # Right eye outer
    landmarks[7] = head + np.array([-0.05, 0.01, 0])  # Left ear
    landmarks[8] = head + np.array([0.05, 0.01, 0])  # Right ear
    landmarks[9] = head + np.array([-0.02, 0.03, 0])  # Mouth left
    landmarks[10] = head + np.array([0.02, 0.03, 0])  # Mouth right
    
    return landmarks


def load_cmu_mocap_json(json_path: str, fps: float = 30.0) -> List[Dict]:
    """
    Load CMU Motion Capture Database JSON format.
    
    Expected format:
    {
        "frames": [
            {
                "time": 0.0,
                "joints": {
                    "Hips": [x, y, z],
                    "LeftUpLeg": [x, y, z],
                    ...
                }
            },
            ...
        ]
    }
    """
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    poses = []
    frames = data.get('frames', [])
    
    for frame_data in frames:
        timestamp = frame_data.get('time', len(poses) / fps)
        joints = frame_data.get('joints', {})
        
        # Convert joint dict to numpy arrays
        joint_positions = {}
        for joint_name, pos in joints.items():
            if isinstance(pos, list) and len(pos) >= 3:
                joint_positions[joint_name] = np.array(pos[:3])
        
        landmarks = map_to_mediapipe_landmarks(joint_positions, skeleton_type='cmu')
        if landmarks is not None:
            poses.append({
                'timestamp': float(timestamp),
                'landmarks': landmarks,
                'confidence': 1.0  # Mocap data is always high confidence
            })
    
    return poses


def load_aist_json(json_path: str, fps: float = 60.0) -> List[Dict]:
    """
    Load AIST++ Dance Motion Dataset JSON format.
    
    Expected format:
    {
        "fps": 60,
        "poses": [
            {
                "frame": 0,
                "joints": {
                    "pelvis": [x, y, z],
                    "l_hip": [x, y, z],
                    ...
                }
            },
            ...
        ]
    }
    """
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    poses = []
    file_fps = data.get('fps', fps)
    pose_data = data.get('poses', [])
    
    for frame_data in pose_data:
        frame_num = frame_data.get('frame', len(poses))
        timestamp = frame_num / file_fps
        joints = frame_data.get('joints', {})
        
        joint_positions = {}
        for joint_name, pos in joints.items():
            if isinstance(pos, list) and len(pos) >= 3:
                joint_positions[joint_name] = np.array(pos[:3])
        
        landmarks = map_to_mediapipe_landmarks(joint_positions, skeleton_type='aist')
        if landmarks is not None:
            poses.append({
                'timestamp': float(timestamp),
                'landmarks': landmarks,
                'confidence': 1.0
            })
    
    return poses


def load_cloud_api_json(json_path: str, api_type: str = 'deepmotion', fps: float = 30.0) -> List[Dict]:
    """
    Load JSON from cloud APIs (DeepMotion, Move AI, RADiCAL).
    
    These APIs typically return standardized formats with frame-by-frame pose data.
    """
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    poses = []
    
    # Try different common formats
    if 'frames' in data:
        frames = data['frames']
    elif 'poses' in data:
        frames = data['poses']
    elif isinstance(data, list):
        frames = data
    else:
        raise ValueError(f"Unknown JSON format in {json_path}")
    
    for i, frame_data in enumerate(frames):
        # Extract timestamp
        timestamp = frame_data.get('timestamp', frame_data.get('time', i / fps))
        
        # Extract joint positions (try different field names)
        joints = frame_data.get('joints', frame_data.get('keypoints', frame_data.get('landmarks', {})))
        
        joint_positions = {}
        if isinstance(joints, dict):
            for joint_name, pos in joints.items():
                if isinstance(pos, (list, np.ndarray)) and len(pos) >= 3:
                    joint_positions[joint_name] = np.array(pos[:3])
        elif isinstance(joints, list):
            # Assume ordered list matching MediaPipe format
            if len(joints) >= 33:
                landmarks = np.array([np.array(j[:3]) if isinstance(j, (list, np.ndarray)) else np.zeros(3) 
                                     for j in joints[:33]])
                poses.append({
                    'timestamp': float(timestamp),
                    'landmarks': landmarks,
                    'confidence': 1.0
                })
                continue
        
        landmarks = map_to_mediapipe_landmarks(joint_positions, skeleton_type='cmu')
        if landmarks is not None:
            poses.append({
                'timestamp': float(timestamp),
                'landmarks': landmarks,
                'confidence': 1.0
            })
    
    return poses


def load_mocap_data(file_path: str, format_type: Optional[str] = None, fps: float = 30.0) -> List[Dict]:
    """
    Universal loader that auto-detects format and loads motion capture data.
    
    Args:
        file_path: Path to mocap file (JSON, BVH, etc.)
        format_type: Optional format hint ('cmu', 'aist', 'mixamo', 'deepmotion', etc.)
        fps: Frames per second (used if not specified in file)
    
    Returns:
        List of pose dicts compatible with MediaPipe format
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Motion capture file not found: {file_path}")
    
    ext = os.path.splitext(file_path)[1].lower()
    
    # Auto-detect format if not specified
    if format_type is None:
        if 'cmu' in file_path.lower() or 'bvh' in file_path.lower():
            format_type = 'cmu'
        elif 'aist' in file_path.lower():
            format_type = 'aist'
        elif 'mixamo' in file_path.lower():
            format_type = 'mixamo'
        elif ext == '.json':
            format_type = 'json'  # Will try to auto-detect JSON format
    
    if ext == '.json' or format_type in ['cmu', 'aist', 'deepmotion', 'moveai', 'radical']:
        # Try different JSON loaders
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            # Detect format from structure
            if 'fps' in data and 'poses' in data:
                return load_aist_json(file_path, fps)
            elif 'frames' in data:
                if format_type == 'aist':
                    return load_aist_json(file_path, fps)
                elif format_type == 'cmu':
                    return load_cmu_mocap_json(file_path, fps)
                else:
                    return load_cloud_api_json(file_path, api_type=format_type or 'deepmotion', fps=fps)
            else:
                return load_cloud_api_json(file_path, api_type=format_type or 'deepmotion', fps=fps)
        except Exception as e:
            raise ValueError(f"Failed to parse JSON mocap file: {e}")
    else:
        raise ValueError(f"Unsupported file format: {ext}. Supported: .json (CMU, AIST++, cloud APIs)")


def mocap_to_dataframe(poses: List[Dict]) -> pd.DataFrame:
    """
    Convert pose list to Pandas DataFrame for analysis.
    
    Returns DataFrame with columns:
    - timestamp: float
    - landmark_0_x, landmark_0_y, landmark_0_z: float
    - landmark_1_x, landmark_1_y, landmark_1_z: float
    - ... (for all 33 landmarks)
    - confidence: float
    """
    rows = []
    for pose in poses:
        row = {'timestamp': pose['timestamp'], 'confidence': pose.get('confidence', 1.0)}
        landmarks = pose['landmarks']
        for i in range(33):
            row[f'landmark_{i}_x'] = landmarks[i, 0]
            row[f'landmark_{i}_y'] = landmarks[i, 1]
            row[f'landmark_{i}_z'] = landmarks[i, 2]
        rows.append(row)
    
    return pd.DataFrame(rows)


def dataframe_to_poses(df: pd.DataFrame) -> List[Dict]:
    """
    Convert DataFrame back to pose list format.
    """
    poses = []
    for _, row in df.iterrows():
        landmarks = np.zeros((33, 3))
        for i in range(33):
            landmarks[i, 0] = row[f'landmark_{i}_x']
            landmarks[i, 1] = row[f'landmark_{i}_y']
            landmarks[i, 2] = row[f'landmark_{i}_z']
        
        poses.append({
            'timestamp': row['timestamp'],
            'landmarks': landmarks,
            'confidence': row.get('confidence', 1.0)
        })
    
    return poses
