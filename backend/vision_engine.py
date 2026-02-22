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
                    
                    visibilities = np.array([lm.visibility for lm in landmarks])
                    avg_visibility = np.mean(visibilities)
                    
                    if avg_visibility > 0.5:
                        landmark_3d = np.array([[lm.x, lm.y, lm.z] for lm in landmarks])
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
    
    # Torso lean
    shoulder_center = (np.array([landmarks[11].x, landmarks[11].y]) + np.array([landmarks[12].x, landmarks[12].y])) / 2
    hip_center = (np.array([landmarks[23].x, landmarks[23].y]) + np.array([landmarks[24].x, landmarks[24].y])) / 2
    torso_angle = np.arctan2(shoulder_center[1] - hip_center[1], shoulder_center[0] - hip_center[0])
    angles.append(torso_angle)
    
    return np.array(angles)


def normalize_pose(landmarks: np.ndarray) -> np.ndarray:
    """Centroid normalization - locks dancer in center."""
    if landmarks is None or len(landmarks) == 0:
        return landmarks
    
    hip_center = (landmarks[23] + landmarks[24]) / 2
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
            prev_landmarks = poses[i-1]['landmarks']
            curr_landmarks = poses[i]['landmarks']
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


def extract_bone_vectors(landmarks: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """
    Extract bone unit vectors and their importance weights.
    Limb-tip bones (forearms, shins, upper arms, thighs) are weighted highest
    because they are most discriminating for dance — a high kick vs standing
    still will differ most in these bones.
    """
    # (parent_idx, child_idx, weight)
    # Higher weight = more important for dance discrimination
    BONES = [
        (11, 13, 2.0), (13, 15, 3.0),   # left upper arm, forearm (tip = high weight)
        (12, 14, 2.0), (14, 16, 3.0),   # right upper arm, forearm
        (11, 12, 1.0),                   # shoulder span
        (23, 24, 1.0),                   # hip span
        (11, 23, 1.0), (12, 24, 1.0),   # torso sides
        (23, 25, 2.0), (25, 27, 3.0),   # left thigh, shin (tip = high weight)
        (24, 26, 2.0), (26, 28, 3.0),   # right thigh, shin
        (0,  11, 1.0), (0,  12, 1.0),   # head to shoulders
    ]
    vectors = []
    weights = []
    for (p, c, w) in BONES:
        v = landmarks[c] - landmarks[p]
        norm = np.linalg.norm(v)
        if norm > 1e-6:
            vectors.append(v / norm)
        else:
            vectors.append(np.zeros(3))
        weights.append(w)
    return np.array(vectors), np.array(weights)


def pose_similarity(pose1: dict, pose2: dict, ref_velocity: float = 0.0) -> float:
    """
    Compare two poses using:
      1. Weighted cosine similarity on bone vectors  — 50%
      2. Joint angle similarity                      — 30%
      3. Movement energy penalty                     — 20%
         (penalizes standing still when ref is actively moving)
    Returns a value in [0, 1] where 1.0 = perfect match.
    """
    if pose1 is None or pose2 is None:
        return 0.0

    landmarks1 = pose1['landmarks']
    landmarks2 = pose2['landmarks']

    if landmarks1.shape != landmarks2.shape:
        return 0.0

    # ── 1. Weighted bone vector cosine similarity ─────────────────────────────
    bones1, weights = extract_bone_vectors(landmarks1)
    bones2, _       = extract_bone_vectors(landmarks2)

    weighted_cos_sims = []
    total_weight = 0.0
    for b1, b2, w in zip(bones1, bones2, weights):
        if np.linalg.norm(b1) > 1e-6 and np.linalg.norm(b2) > 1e-6:
            cos_sim = np.dot(b1, b2)  # unit vectors, so this is cosine similarity
            weighted_cos_sims.append(((cos_sim + 1.0) / 2.0) * w)
            total_weight += w

    bone_sim = float(sum(weighted_cos_sims) / total_weight) if total_weight > 0 else 0.0

    # ── 2. Joint angle similarity ─────────────────────────────────────────────
    angles1 = pose1.get('angles', np.array([]))
    angles2 = pose2.get('angles', np.array([]))

    angle_sim = bone_sim  # fallback if no angle data
    if len(angles1) > 0 and len(angles2) > 0 and len(angles1) == len(angles2):
        angle_diff = np.abs(angles1 - angles2)
        angle_sim = 1.0 - float(np.mean(np.clip(angle_diff / np.pi, 0, 1)))

    # ── 3. Movement energy penalty ────────────────────────────────────────────
    # If the reference is actively moving but the user's pose is near-neutral
    # (standing still), penalize. Measured by how far limb landmarks deviate
    # from a neutral resting position.
    ACTIVE_VELOCITY_THRESHOLD = 0.02  # tune this if needed

    movement_score = 1.0
    if ref_velocity > ACTIVE_VELOCITY_THRESHOLD:
        # Measure how much the practice pose deviates from neutral standing
        # by checking variance of limb-tip positions relative to hip center
        hip_center = (landmarks2[23] + landmarks2[24]) / 2
        limb_tips = [landmarks2[15], landmarks2[16], landmarks2[27], landmarks2[28]]
        tip_distances = [np.linalg.norm(tip - hip_center) for tip in limb_tips]
        tip_variance = float(np.std(tip_distances))

        # Low variance = limbs all at similar distance from hip = standing still
        # Scale: variance < 0.05 → near-zero movement score; > 0.2 → full score
        movement_score = float(np.clip((tip_variance - 0.05) / 0.15, 0.0, 1.0))

    # ── 4. Weighted combination ───────────────────────────────────────────────
    similarity = 0.50 * bone_sim + 0.30 * angle_sim + 0.20 * movement_score

    return max(0.0, min(1.0, similarity))


def analyze_move_quality(ref_poses: list, prac_poses: list, move: dict, offset: float, ref_duration: float = 0, prac_duration: float = 0) -> dict:
    """Analyze quality using the InStep 3-tier grading rubric."""

    # ── InStep Grading Rubric thresholds ──────────────────────────────────────
    GREEN_THRESHOLD = 0.85   # 🟢 InStep Standard: joints within ~15° tolerance
    GRAY_THRESHOLD  = 0.60   # 🔘 Style Nitpick: right move, wrong sharpness/timing
    # Below GRAY_THRESHOLD  = 🔴 Major Discrepancy: completely different state
    # ──────────────────────────────────────────────────────────────────────────

    start_time = move['timestamp']
    end_time = move.get('end_timestamp', start_time + 2.0)
    
    ref_start = start_time - offset
    ref_end = end_time - offset
    
    if prac_duration > 0:
        if ref_start < 0 or ref_end > prac_duration:
            return {
                'status': 'gap',
                'color': 'gap',
                'match': False,
                'feedback': 'Practice video does not cover this section.',
                'tips': [],
                'similarity': 0.0,
                'points_docked': 0
            }
    
    ref_frames = [p for p in ref_poses if start_time <= p['timestamp'] <= end_time]
    prac_frames = [p for p in prac_poses if ref_start <= p['timestamp'] <= ref_end]
    
    if not ref_frames:
        return {
            'status': 'gap',
            'color': 'gap',
            'match': False,
            'feedback': 'No reference data for this section.',
            'tips': [],
            'similarity': 0.0,
            'points_docked': 0
        }
    
    if not prac_frames:
        return {
            'status': 'gap',
            'color': 'gap',
            'match': False,
            'feedback': 'Practice video does not cover this section.',
            'tips': [],
            'similarity': 0.0,
            'points_docked': 0
        }
    
    similarities = []
    ref_velocities = calculate_velocity(ref_frames)

    for i, ref_frame in enumerate(ref_frames):
        best_sim = 0
        ref_vel = ref_velocities[i] if i < len(ref_velocities) else 0.0
        for prac_frame in prac_frames:
            time_diff = abs(ref_frame['timestamp'] - (prac_frame['timestamp'] + offset))
            if time_diff < 0.5:
                sim = pose_similarity(ref_frame, prac_frame, ref_velocity=ref_vel)
                if sim > best_sim:
                    best_sim = sim
        if best_sim > 0:
            similarities.append(best_sim)
    
    if not similarities:
        return {
            'status': 'miss',
            'color': 'red',
            'match': False,
            'feedback': 'Could not align practice with reference.',
            'tips': [],
            'similarity': 0.0,
            'points_docked': 15  # mid-range red deduction
        }
    
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

    # ── Assign tier, feedback, and point deduction ────────────────────────────
    if avg_sim >= GREEN_THRESHOLD:
        # 🟢 InStep Standard
        status = 'match'
        color = 'green'
        match = True
        points_docked = 0
        feedback = "Great Sync! Your movement matches the reference style perfectly here."
        tips = ["Keep up this consistency!"]

    elif avg_sim >= GRAY_THRESHOLD:
        # 🔘 Style Nitpick — right move, wrong vibe/sharpness
        status = 'close'
        color = 'gray'
        match = False
        points_docked = 2  # mid-range of -1 to -3
        tips = get_specific_tips(ref_frames, prac_frames)
        # Tailor gray feedback based on specific issues found
        if tips:
            feedback = f"Form Adjustment: {tips[0].lower().rstrip('.')}; focus on sharper execution."
        else:
            feedback = "Form Adjustment: You have the right move — tighten up the sharpness and timing."

    else:
        # 🔴 Major Discrepancy — completely different state
        status = 'miss'
        color = 'red'
        match = False
        points_docked = 15  # mid-range of -10 to -20
        ts = format_timestamp(move['timestamp'])
        feedback = f"Missed Move: Your pose at {ts} does not match the reference choreography structure."
        tips = get_specific_tips(ref_frames, prac_frames)
    # ──────────────────────────────────────────────────────────────────────────

    return {
        'status': status,
        'color': color,
        'match': match,
        'feedback': feedback,
        'tips': tips[:3],
        'similarity': float(avg_sim),
        'points_docked': points_docked
    }


def get_specific_tips(ref_frames: list, prac_frames: list) -> list:
    """Get specific body part feedback."""
    tips = []
    
    if not ref_frames or not prac_frames:
        return tips
    
    def get_body_part_center(frames, indices):
        positions = []
        for f in frames:
            for idx in indices:
                if idx < len(f['landmarks']):
                    positions.append(f['landmarks'][idx])
        return np.mean(positions, axis=0) if positions else None
    
    left_arm_ref = get_body_part_center(ref_frames, [11, 13, 15])
    left_arm_prac = get_body_part_center(prac_frames, [11, 13, 15])
    right_arm_ref = get_body_part_center(ref_frames, [12, 14, 16])
    right_arm_prac = get_body_part_center(prac_frames, [12, 14, 16])
    
    if left_arm_ref is not None and left_arm_prac is not None:
        if np.linalg.norm(left_arm_ref - left_arm_prac) > 0.1:
            tips.append("Arms are slightly loose; try locking your left elbow for more 'snap'")
    
    if right_arm_ref is not None and right_arm_prac is not None:
        if np.linalg.norm(right_arm_ref - right_arm_prac) > 0.1:
            tips.append("Arms are slightly loose; try locking your right elbow for more 'snap'")
    
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
    
    valid_poses = [p for p in poses if p.get('visibility', 0) > 0.5]
    if len(valid_poses) < 3:
        return []
    
    video_duration = valid_poses[-1]['timestamp']
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
    
    ref_duration = ref_poses[-1]['timestamp']
    prac_duration = prac_poses[-1]['timestamp']
    
    ref_moves = detect_moves(ref_poses)
    
    if not ref_moves:
        ref_moves = [{'timestamp': ref_poses[0]['timestamp'], 'start_idx': 0, 'end_idx': len(ref_poses)-1}]
    
    for i, move in enumerate(ref_moves):
        if i + 1 < len(ref_moves):
            move['end_timestamp'] = ref_moves[i + 1]['timestamp']
        else:
            move['end_timestamp'] = ref_poses[-1]['timestamp'] + 1.0
    
    moves = []
    total_points_docked = 0

    for i, move in enumerate(ref_moves):
        quality = analyze_move_quality(ref_poses, prac_poses, move, offset, ref_duration, prac_duration)
        
        ts = format_timestamp(move['timestamp'])
        duration = move.get('duration', 2.0)

        # Accumulate deductions (gaps don't dock points)
        if quality.get('status') != 'gap':
            total_points_docked += quality.get('points_docked', 0)
        
        moves.append({
            'id': i + 1,
            'timestamp': ts,
            'label': f"{ts} ({duration:.1f}s)",
            'status': quality.get('status', 'miss'),
            'color': quality.get('color', 'red'),
            'match': quality['match'],
            'similarity': quality.get('similarity', 0),
            'feedback': quality['feedback'],
            'tips': quality['tips'],
            'points_docked': quality.get('points_docked', 0)
        })

    # ── InStep Scoring: start at 100, dock points per rubric ─────────────────
    overall_score = max(0, min(100, 100 - total_points_docked))
    # ──────────────────────────────────────────────────────────────────────────

    return {
        'success': True,
        'overallScore': overall_score,
        'moves': [
            {
                'id': int(m['id']),
                'timestamp': str(m['timestamp']),
                'label': str(m['label']),
                'status': str(m.get('status', 'miss')),
                'color': str(m.get('color', 'red')),
                'match': bool(m['match']),
                'similarity': float(m.get('similarity', 0)),
                'feedback': str(m['feedback']),
                'tips': list(m['tips']),
                'points_docked': int(m.get('points_docked', 0))
            }
            for m in moves
        ]
    }


def format_timestamp(seconds: float) -> str:
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins}:{secs:02d}"
