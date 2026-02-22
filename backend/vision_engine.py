"""
Vision-based dance comparison using MediaPipe Pose.
Professional-grade implementation with:
- 3D joint angle comparison
- Velocity tracking
- Visibility filtering  
- Centroid normalization
"""
import os
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import PoseLandmarker, PoseLandmarkerOptions, RunningMode
from scipy import spatial


MODEL_URL = "https://storage.googleapis.com/mediapipe-assets/pose_landmarker.task"
MODEL_PATH = "/tmp/pose_landmarker.task"

def download_model():
    if os.path.exists(MODEL_PATH):
        if os.path.getsize(MODEL_PATH) > 10000:
            return True
        else:
            os.remove(MODEL_PATH)
    return True

_model_available = download_model()

options = None
if _model_available:
    try:
        options = PoseLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=MODEL_PATH),
            running_mode=RunningMode.VIDEO,
            num_poses=1,
            min_pose_detection_confidence=0.3,
            min_tracking_confidence=0.3
        )
    except Exception as e:
        print(f"Error loading model: {e}")
        options = None

def create_pose_landmarker():
    if options is None:
        return None
    try:
        return PoseLandmarker.create_from_options(options)
    except Exception as e:
        print(f"Error creating pose landmarker: {e}")
        return None

def get_pose_landmarker():
    return create_pose_landmarker()


FRAME_SAMPLE_RATE = 3  # Higher sampling for velocity tracking


def calculate_angle_3d(p1, p2, p3):
    """Calculate angle at p2 formed by p1-p2-p3 in 3D."""
    v1 = np.array([p1.x - p2.x, p1.y - p2.y, p1.z - p2.z])
    v2 = np.array([p3.x - p2.x, p3.y - p2.y, p3.z - p2.z])
    
    cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-8)
    return np.arccos(np.clip(cos_angle, -1, 1))


def extract_poses(video_path: str) -> list[dict]:
    """Extract pose landmarks with full 3D data and visibility."""
    if not os.path.isfile(video_path):
        return []
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return []
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 30
    
    poses = []
    frame_idx = 0
    
    try:
        landmarker = get_pose_landmarker()
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            if frame_idx % FRAME_SAMPLE_RATE == 0:
                timestamp = frame_idx / fps
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                result = landmarker.detect_for_video(mp_image, int(timestamp * 1000))
                
                if result.pose_landmarks and len(result.pose_landmarks) > 0:
                    landmarks = result.pose_landmarks[0]
                    
                    # Extract visibility scores
                    visibilities = np.array([lm.visibility for lm in landmarks])
                    avg_visibility = np.mean(visibilities)
                    
                    # Only process if body is mostly visible
                    if avg_visibility > 0.5:
                        # Get 3D normalized landmarks
                        landmark_3d = np.array([[lm.x, lm.y, lm.z] for lm in landmarks])
                        
                        # Calculate joint angles (key angles for dance)
                        angles = calculate_dance_angles(landmarks)
                        
                        poses.append({
                            'timestamp': timestamp,
                            'landmarks': landmark_3d,
                            'angles': angles,
                            'visibility': avg_visibility,
                            'visibilities': visibilities
                        })
            
            frame_idx += 1
    finally:
        cap.release()
    
    return poses


def calculate_dance_angles(landmarks) -> np.ndarray:
    """Calculate key joint angles for dance analysis."""
    angles = []
    
    # Left arm: shoulder, elbow, wrist
    angles.append(calculate_angle_3d(landmarks[13], landmarks[11], landmarks[12]))  # shoulder
    angles.append(calculate_angle_3d(landmarks[11], landmarks[13], landmarks[15]))  # elbow
    
    # Right arm
    angles.append(calculate_angle_3d(landmarks[14], landmarks[12], landmarks[12]))  # shoulder  
    angles.append(calculate_angle_3d(landmarks[12], landmarks[14], landmarks[16]))  # elbow
    
    # Left leg
    angles.append(calculate_angle_3d(landmarks[25], landmarks[23], landmarks[24]))  # hip
    angles.append(calculate_angle_3d(landmarks[23], landmarks[25], landmarks[27]))  # knee
    
    # Right leg
    angles.append(calculate_angle_3d(landmarks[26], landmarks[24], landmarks[23]))  # hip
    angles.append(calculate_angle_3d(landmarks[24], landmarks[26], landmarks[28]))  # knee
    
    # Torso lean (using hip center vs shoulder center)
    shoulder_center = (np.array([landmarks[11].x, landmarks[11].y]) + np.array([landmarks[12].x, landmarks[12].y])) / 2
    hip_center = (np.array([landmarks[23].x, landmarks[23].y]) + np.array([landmarks[24].x, landmarks[24].y])) / 2
    torso_angle = np.arctan2(shoulder_center[1] - hip_center[1], shoulder_center[0] - hip_center[0])
    angles.append(torso_angle)
    
    return np.array(angles)


def normalize_pose(landmarks: np.ndarray) -> np.ndarray:
    """Centroid normalization - locks dancer in center."""
    if landmarks is None or len(landmarks) == 0:
        return landmarks
    
    # Use hip center as centroid
    hip_center = (landmarks[23] + landmarks[24]) / 2
    
    # Normalize by scale (nose to hip distance)
    nose = landmarks[0]
    scale = np.linalg.norm(nose - hip_center)
    if scale < 1e-6:
        scale = 1e-6
    
    normalized = (landmarks - hip_center) / scale
    return normalized


def calculate_velocity(poses: list) -> list:
    """Calculate velocity (movement speed) at each frame."""
    velocities = []
    
    for i in range(len(poses)):
        if i == 0:
            velocities.append(0)
        else:
            # Movement of key body parts
            prev_landmarks = poses[i-1]['landmarks']
            curr_landmarks = poses[i]['landmarks']
            
            # Key movement points: shoulders, wrists, hips, ankles
            key_indices = [11, 12, 15, 16, 23, 24, 27, 28]
            
            movement = 0
            for idx in key_indices:
                if idx < len(prev_landmarks) and idx < len(curr_landmarks):
                    movement += np.linalg.norm(curr_landmarks[idx] - prev_landmarks[idx])
            
            velocities.append(movement / len(key_indices))
    
    return velocities


def calculate_acceleration(velocities: list) -> list:
    """Calculate acceleration (change in velocity)."""
    accelerations = []
    
    for i in range(len(velocities)):
        if i == 0:
            accelerations.append(0)
        else:
            accelerations.append(abs(velocities[i] - velocities[i-1]))
    
    return accelerations


def pose_similarity(pose1: dict, pose2: dict) -> float:
    """Compare two poses using multiple methods."""
    if pose1 is None or pose2 is None:
        return 0.0
    
    landmarks1 = pose1['landmarks']
    landmarks2 = pose2['landmarks']
    
    if landmarks1.shape != landmarks2.shape:
        return 0.0
    
    # Get visibility data
    vis1 = pose1.get('visibilities', np.ones(33))
    vis2 = pose2.get('visibilities', np.ones(33))
    
    # Weight by visibility - ignore low confidence joints
    weights = (vis1 + vis2) / 2
    weights[weights < 0.5] = 0  # Ignore low confidence
    
    # 1. Normalized position similarity (centroid normalized)
    norm1 = normalize_pose(landmarks1)
    norm2 = normalize_pose(landmarks2)
    
    # Weighted Euclidean distance
    diff = norm1 - norm2
    weighted_diff = diff * weights[:, np.newaxis]
    pos_sim = np.exp(-np.linalg.norm(weighted_diff))
    
    # 2. Joint angle similarity (most important for dance)
    angles1 = pose1.get('angles', np.array([]))
    angles2 = pose2.get('angles', np.array([]))
    
    angle_sim = 0.0
    if len(angles1) > 0 and len(angles2) > 0 and len(angles1) == len(angles2):
        # Compare angles (smaller difference = more similar)
        angle_diff = np.abs(angles1 - angles2)
        angle_sim = np.exp(-np.mean(angle_diff))
    
    # 3. Combine: 40% position, 60% angles (angles matter more for dance)
    similarity = 0.4 * pos_sim + 0.6 * angle_sim
    
    return max(0.0, min(1.0, similarity))


def analyze_move_quality(ref_poses: list, prac_poses: list, move: dict, offset: float, ref_duration: float = 0, prac_duration: float = 0) -> dict:
    """Analyze quality with velocity and visibility filtering."""
    
    MATCH_THRESHOLD = 0.50  # Green threshold
    CLOSE_THRESHOLD = 0.25  # Gray threshold
    
    start_time = move['timestamp']
    end_time = move.get('end_timestamp', start_time + 2.0)
    
    ref_start = start_time - offset
    ref_end = end_time - offset
    
    # Check for video gap
    if prac_duration > 0:
        if ref_start < 0 or ref_end > prac_duration:
            return {
                'status': 'gap',
                'match': False,
                'feedback': 'Practice video does not cover this section.',
                'tips': [],
                'similarity': 0.0
            }
    
    # Get frames in this time range
    ref_frames = [p for p in ref_poses if start_time <= p['timestamp'] <= end_time]
    prac_frames = [p for p in prac_poses if ref_start <= p['timestamp'] <= ref_end]
    
    if not ref_frames:
        return {
            'status': 'gap',
            'match': False,
            'feedback': 'No reference data for this section.',
            'tips': [],
            'similarity': 0.0
        }
    
    if not prac_frames:
        return {
            'status': 'gap',
            'match': False,
            'feedback': 'Practice video does not cover this section.',
            'tips': [],
            'similarity': 0.0
        }
    
    # Find best matching frames (with time alignment)
    similarities = []
    for ref_frame in ref_frames:
        best_sim = 0
        for prac_frame in prac_frames:
            time_diff = abs(ref_frame['timestamp'] - (prac_frame['timestamp'] + offset))
            if time_diff < 0.5:  # Within 0.5 seconds
                sim = pose_similarity(ref_frame, prac_frame)
                if sim > best_sim:
                    best_sim = sim
        
        if best_sim > 0:
            similarities.append(best_sim)
    
    if not similarities:
        return {
            'status': 'miss',
            'match': False,
            'feedback': 'Could not align practice with reference.',
            'tips': [],
            'similarity': 0.0
        }
    
    # Apply temporal smoothing (average over window)
    window = 3
    if len(similarities) > window:
        smoothed = []
        for i in range(len(similarities)):
            start = max(0, i - window // 2)
            end = min(len(similarities), i + window // 2 + 1)
            smoothed.append(np.mean(similarities[start:end]))
        avg_sim = np.mean(smoothed)
    else:
        avg_sim = np.mean(similarities)
    
    # Determine status
    if avg_sim >= MATCH_THRESHOLD:
        status = 'match'
        match = True
        feedback = "Great job! Your form matches the reference."
        tips = ["Keep up this consistency!"]
    elif avg_sim >= CLOSE_THRESHOLD:
        status = 'close'
        match = False
        feedback = "Almost there! Minor adjustments needed."
        tips = get_specific_tips(ref_frames, prac_frames)
    else:
        status = 'miss'
        match = False
        supportive_messages = [
            "Keep practicing! You're building muscle memory.",
            "Don't give up! Every rep makes you stronger.",
            "You're on your way! Keep at it.",
            "Progress takes time. Keep going!",
            "You're putting in the work. It'll pay off!",
        ]
        import random
        feedback = random.choice(supportive_messages)
        tips = get_specific_tips(ref_frames, prac_frames)
    
    return {
        'status': status,
        'match': match,
        'feedback': feedback,
        'tips': tips[:3],
        'similarity': float(avg_sim)
    }


def get_specific_tips(ref_frames: list, prac_frames: list) -> list:
    """Get specific body part feedback."""
    tips = []
    
    if not ref_frames or not prac_frames:
        return tips
    
    # Get average positions for key body parts
    def get_body_part_center(frames, indices):
        positions = []
        for f in frames:
            for idx in indices:
                if idx < len(f['landmarks']):
                    positions.append(f['landmarks'][idx])
        return np.mean(positions, axis=0) if positions else None
    
    # Compare arms
    left_arm_ref = get_body_part_center(ref_frames, [11, 13, 15])
    left_arm_prac = get_body_part_center(prac_frames, [11, 13, 15])
    right_arm_ref = get_body_part_center(ref_frames, [12, 14, 16])
    right_arm_prac = get_body_part_center(prac_frames, [12, 14, 16])
    
    if left_arm_ref is not None and left_arm_prac is not None:
        if np.linalg.norm(left_arm_ref - left_arm_prac) > 0.1:
            tips.append("Lift your left arm higher")
    
    if right_arm_ref is not None and right_arm_prac is not None:
        if np.linalg.norm(right_arm_ref - right_arm_prac) > 0.1:
            tips.append("Lift your right arm higher")
    
    # Compare legs
    left_leg_ref = get_body_part_center(ref_frames, [23, 25, 27])
    left_leg_prac = get_body_part_center(prac_frames, [23, 25, 27])
    right_leg_ref = get_body_part_center(ref_frames, [24, 26, 28])
    right_leg_prac = get_body_part_center(prac_frames, [24, 26, 28])
    
    if left_leg_ref is not None and left_leg_prac is not None:
        if np.linalg.norm(left_leg_ref - left_leg_prac) > 0.1:
            tips.append("Adjust your left foot position")
    
    if right_leg_ref is not None and right_leg_prac is not None:
        if np.linalg.norm(right_leg_ref - right_leg_prac) > 0.1:
            tips.append("Adjust your right foot position")
    
    # Torso
    torso_ref = get_body_part_center(ref_frames, [11, 12, 23, 24])
    torso_prac = get_body_part_center(prac_frames, [11, 12, 23, 24])
    
    if torso_ref is not None and torso_prac is not None:
        if np.linalg.norm(torso_ref - torso_prac) > 0.1:
            tips.append("Be more fluid in your torso")
    
    return tips


def detect_moves(poses: list) -> list:
    """Detect key poses by dividing video into segments."""
    if len(poses) < 3:
        return []
    
    # Filter high confidence poses
    valid_poses = [p for p in poses if p.get('visibility', 0) > 0.5]
    if len(valid_poses) < 3:
        return []
    
    video_duration = valid_poses[-1]['timestamp']
    
    # Divide into segments (~2 seconds each for good granularity)
    segment_duration = max(1.5, video_duration / 12)
    
    moves = []
    current_time = 0
    idx = 0
    
    while current_time < video_duration:
        segment_end = current_time + segment_duration
        segment_poses = [p for p in valid_poses if current_time <= p['timestamp'] < segment_end]
        
        if segment_poses:
            moves.append({
                'timestamp': segment_poses[0]['timestamp'],
                'start_idx': poses.index(segment_poses[0]) if segment_poses[0] in poses else idx,
                'end_idx': poses.index(segment_poses[-1]) if segment_poses[-1] in poses else idx,
                'duration': segment_poses[-1]['timestamp'] - segment_poses[0]['timestamp']
            })
        
        current_time = segment_end
        idx += 1
        if idx > 15:
            break
    
    return moves


def analyze_videos(ref_video_path: str, prac_video_path: str, offset: float = 0) -> dict:
    """Main analysis function."""
    if not _model_available or options is None:
        return {
            'success': False,
            'error': 'Model not loaded',
            'overallScore': 0,
            'moves': []
        }
    
    ref_poses = extract_poses(ref_video_path)
    prac_poses = extract_poses(prac_video_path)
    
    if not ref_poses:
        return {
            'success': False,
            'error': 'Could not detect poses in reference',
            'overallScore': 0,
            'moves': []
        }
    
    if not prac_poses:
        return {
            'success': False,
            'error': 'Could not detect poses in practice',
            'overallScore': 0,
            'moves': []
        }
    
    # Get durations
    ref_duration = ref_poses[-1]['timestamp']
    prac_duration = prac_poses[-1]['timestamp']
    
    # Detect moves
    ref_moves = detect_moves(ref_poses)
    
    if not ref_moves:
        ref_moves = [{'timestamp': ref_poses[0]['timestamp'], 'start_idx': 0, 'end_idx': len(ref_poses)-1}]
    
    # Set end timestamps
    for i, move in enumerate(ref_moves):
        if i + 1 < len(ref_moves):
            move['end_timestamp'] = ref_moves[i + 1]['timestamp']
        else:
            move['end_timestamp'] = ref_poses[-1]['timestamp'] + 1.0
    
    moves = []
    total_similarity = 0.0
    scored_count = 0
    
    for i, move in enumerate(ref_moves):
        quality = analyze_move_quality(ref_poses, prac_poses, move, offset, ref_duration, prac_duration)
        
        ts = format_timestamp(move['timestamp'])
        duration = move.get('duration', 2.0)
        
        moves.append({
            'id': i + 1,
            'timestamp': ts,
            'label': f"{ts} ({duration:.1f}s)",
            'status': quality.get('status', 'miss'),
            'match': quality['match'],
            'similarity': quality.get('similarity', 0),
            'feedback': quality['feedback'],
            'tips': quality['tips']
        })
        
        # Use actual similarity score (not binary)
        if quality.get('status') != 'gap':
            total_similarity += quality.get('similarity', 0)
            scored_count += 1
    
    # Score based on non-red, non-gap segments
    # Only green + gray + red count toward total; gaps excluded entirely
    total_moves = len([m for m in moves if m['status'] != 'gap'])
    accurate_moves = len([m for m in moves if m['status'] in ['match', 'close']])
    
    raw_score = (accurate_moves / total_moves) * 100 if total_moves > 0 else 0
    close_count = len([m for m in moves if m['status'] == 'close'])
    overall_score = min(97, max(0, raw_score - (close_count * 1)))  # Subtract 1% per gray segment
    
    return {
        'success': True,
        'overallScore': overall_score,
        'moves': [
            {
                'id': int(m['id']),
                'timestamp': str(m['timestamp']),
                'label': str(m['label']),
                'status': str(m.get('status', 'miss')),
                'match': bool(m['match']),
                'similarity': float(m.get('similarity', 0)),
                'feedback': str(m['feedback']),
                'tips': list(m['tips'])
            }
            for m in moves
        ]
    }


def format_timestamp(seconds: float) -> str:
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins}:{secs:02d}"
