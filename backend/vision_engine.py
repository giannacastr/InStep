"""
Vision-based dance comparison using MediaPipe Pose.
Extracts pose landmarks from reference and practice videos,
compares them to detect moves and provide feedback.

NOTE: You need to download the pose_landmarker model file manually:
1. Go to https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker
2. Download the "Pose Landmarker (Lite)" model
3. Save it as /tmp/pose_landmarker.task
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
    
    print(f"Downloading MediaPipe pose model from {MODEL_URL}...")
    try:
        import urllib.request
        req = urllib.request.Request(MODEL_URL)
        with urllib.request.urlopen(req) as response:
            with open(MODEL_PATH, 'wb') as f:
                f.write(response.read())
        if os.path.getsize(MODEL_PATH) > 10000:
            print(f"Model downloaded to {MODEL_PATH}")
            return True
        else:
            print(f"Downloaded file too small - may be an error")
            return False
    except Exception as e:
        print(f"Could not download model automatically: {e}")
        print(f"Please download manually from: https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker")
        return False

_model_available = download_model()

options = None
if _model_available:
    try:
        options = PoseLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=MODEL_PATH),
            running_mode=RunningMode.VIDEO,
            num_poses=1,
            min_pose_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
    except Exception as e:
        print(f"Error loading model: {e}")
        options = None

pose_landmarker = None

def create_pose_landmarker():
    """Create a fresh PoseLandmarker instance for each video."""
    if options is None:
        return None
    try:
        return PoseLandmarker.create_from_options(options)
    except Exception as e:
        print(f"Error creating pose landmarker: {e}")
        return None

def get_pose_landmarker():
    return create_pose_landmarker()


FRAME_SAMPLE_RATE = 5


def extract_poses(video_path: str) -> list[dict]:
    """
    Extract pose landmarks from video frames.
    
    Returns list of dicts with:
        - timestamp: float (seconds)
        - landmarks: numpy array of shape (33, 3) - x, y, z normalized
        - confidence: float average confidence score
    """
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
    timestamp = 0.0
    
    try:
        landmarker = get_pose_landmarker()
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            if frame_idx % FRAME_SAMPLE_RATE == 0:
                # Use monotonically increasing timestamp (skip frames for timing)
                timestamp = frame_idx / fps
                
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                result = landmarker.detect_for_video(mp_image, int(timestamp * 1000))
                
                if result.pose_landmarks and len(result.pose_landmarks) > 0:
                    landmarks = np.array([[lm.x, lm.y, lm.z] for lm in result.pose_landmarks[0]])
                    confidences = [lm.visibility for lm in result.pose_landmarks[0]]
                    confidence = np.mean(confidences) if confidences else 0
                    
                    # Only add pose if confidence is high enough (body clearly visible)
                    MIN_POSE_CONFIDENCE = 0.3  # Lower threshold to get more poses
                    if confidence >= MIN_POSE_CONFIDENCE:
                        poses.append({
                            'timestamp': timestamp,
                            'landmarks': landmarks,
                            'confidence': confidence
                        })
            
            frame_idx += 1
    finally:
        cap.release()
    
    return poses


def calculate_joint_angles(landmarks: np.ndarray) -> np.ndarray:
    """
    Calculate joint angles for key body parts.
    Returns array of angles in radians.
    """
    if landmarks is None or len(landmarks) < 33:
        return np.array([])
    
    # Keypoint indices
    # Shoulders: 11, 12
    # Elbows: 13, 14  
    # Wrists: 15, 16
    # Hips: 23, 24
    # Knees: 25, 26
    # Ankles: 27, 28
    
    def angle(p1, p2, p3):
        """Calculate angle at p2 formed by p1-p2-p3"""
        v1 = p1 - p2
        v2 = p3 - p2
        cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-6)
        return np.arccos(np.clip(cos_angle, -1, 1))
    
    angles = []
    
    # Left arm angles
    angles.append(angle(landmarks[13], landmarks[11], landmarks[12]))  # Left shoulder
    angles.append(angle(landmarks[11], landmarks[13], landmarks[15]))  # Left elbow
    
    # Right arm angles
    angles.append(angle(landmarks[14], landmarks[12], landmarks[11]))  # Right shoulder
    angles.append(angle(landmarks[12], landmarks[14], landmarks[16]))  # Right elbow
    
    # Torso angle (shoulder midpoint to hip midpoint)
    shoulder_mid = (landmarks[11] + landmarks[12]) / 2
    hip_mid = (landmarks[23] + landmarks[24]) / 2
    torso_vec = shoulder_mid - hip_mid
    angles.append(np.arctan2(torso_vec[1], torso_vec[0]))  # Torso lean
    
    # Left leg angles
    angles.append(angle(landmarks[23], landmarks[25], landmarks[27]))  # Left hip
    angles.append(angle(landmarks[25], landmarks[27], landmarks[29]))  # Left knee
    
    # Right leg angles
    angles.append(angle(landmarks[24], landmarks[26], landmarks[28]))  # Right hip
    angles.append(angle(landmarks[26], landmarks[28], landmarks[30]))  # Right knee
    
    return np.array(angles)


def normalize_pose(landmarks: np.ndarray) -> np.ndarray:
    """
    Normalize pose to be scale and position invariant.
    Uses hip center as origin and nose-to-hip distance for scale.
    """
    if landmarks is None or len(landmarks) == 0:
        return landmarks
    
    hip_center = (landmarks[23] + landmarks[24]) / 2
    nose = landmarks[0]
    
    scale = np.linalg.norm(nose - hip_center)
    if scale < 1e-6:
        scale = 1e-6
    
    normalized = (landmarks - hip_center) / scale
    return normalized


def pose_similarity(pose1: np.ndarray, pose2: np.ndarray) -> float:
    """
    Calculate similarity between two poses.
    Returns value between 0 (completely different) and 1 (identical).
    """
    if pose1 is None or pose2 is None:
        return 0.0
    
    if pose1.shape != pose2.shape:
        return 0.0
    
    # Normalize poses
    norm1 = normalize_pose(pose1)
    norm2 = normalize_pose(pose2)
    
    # Position similarity - use Euclidean distance for more intuitive comparison
    pos_diff = np.linalg.norm(norm1 - norm2)
    pos_sim = np.exp(-pos_diff)  # Exponential decay
    
    # Angle similarity
    angles1 = calculate_joint_angles(pose1)
    angles2 = calculate_joint_angles(pose2)
    
    angle_sim = 0.0
    if len(angles1) > 0 and len(angles2) > 0 and len(angles1) == len(angles2):
        # Use angular difference (smaller is better)
        angle_diff = np.abs(angles1 - angles2)
        # Convert to similarity (0 to 1)
        angle_sim = np.exp(-np.mean(angle_diff))  # Exponential decay
    
    # Weighted combination: 50% position, 50% angles
    similarity = 0.5 * pos_sim + 0.5 * angle_sim
    
    return max(0.0, min(1.0, similarity))


def compute_frame_similarities(ref_poses: list, prac_poses: list, offset: float = 0) -> list:
    """
    Compute similarity scores between reference and practice frames.
    Applies time offset to align the videos.
    """
    similarities = []
    
    for ref_pose in ref_poses:
        ref_time = ref_pose['timestamp']
        prac_time = ref_time - offset
        
        best_sim = 0
        
        for prac_pose in prac_poses:
            if abs(prac_pose['timestamp'] - prac_time) < 0.5:
                sim = pose_similarity(ref_pose['landmarks'], prac_pose['landmarks'])
                if sim > best_sim:
                    best_sim = sim
        
        similarities.append({
            'ref_time': ref_time,
            'prac_time': prac_time,
            'similarity': best_sim
        })
    
    return similarities


def detect_moves(poses: list, threshold: float = 0.08) -> list:
    """
    Detect distinct key poses/moves based on significant pose changes.
    Simple approach: divide video into time segments and detect changes within.
    """
    if len(poses) < 3:
        return []
    
    # Filter to only high-confidence poses (body clearly visible)
    MIN_CONFIDENCE = 0.3
    valid_poses = [p for p in poses if p.get('confidence', 0) >= MIN_CONFIDENCE]
    if len(valid_poses) < 3:
        return []
    
    # Get video duration
    video_duration = valid_poses[-1]['timestamp']
    
    # Target ~10 moves per 30 seconds (adjustable)
    segment_duration = max(1.5, video_duration / 10)  # At least 1.5s per segment
    
    moves = []
    current_time = 0
    idx = 0
    
    while current_time < video_duration:
        # Find poses in this time segment
        segment_start = current_time
        segment_end = current_time + segment_duration
        
        segment_poses = [p for p in valid_poses if segment_start <= p['timestamp'] < segment_end]
        
        if segment_poses:
            # Find the most common/representative pose in this segment
            # and detect if there's a significant change
            if len(segment_poses) >= 3:
                moves.append({
                    'timestamp': segment_poses[0]['timestamp'],
                    'start_idx': valid_poses.index(segment_poses[0]),
                    'end_idx': valid_poses.index(segment_poses[-1]),
                    'duration': segment_poses[-1]['timestamp'] - segment_poses[0]['timestamp']
                })
        
        current_time = segment_end
        idx += 1
        
        # Limit to reasonable number
        if idx > 20:
            break
    
    # Ensure at least some moves
    if not moves:
        # Fallback: divide into equal segments
        num_segments = 10
        segment_size = len(valid_poses) // num_segments
        for i in range(num_segments):
            start_idx = i * segment_size
            end_idx = min((i + 1) * segment_size, len(valid_poses) - 1)
            moves.append({
                'timestamp': valid_poses[start_idx]['timestamp'],
                'start_idx': start_idx,
                'end_idx': end_idx,
                'duration': valid_poses[end_idx]['timestamp'] - valid_poses[start_idx]['timestamp']
            })
    
    return moves


def analyze_move_quality(ref_poses: list, prac_poses: list, move: dict, offset: float, ref_duration: float = 0, prac_duration: float = 0) -> dict:
    """
    Analyze quality of a specific move.
    Returns match status, feedback, and tips.
    
    Status values:
    - "match": Good match (above 70%)
    - "close": Close enough (50-70%) - counts towards score but not perfect
    - "miss": Poor match (below 50%)
    - "gap": No practice data (video gap from offset)
    """
    # Thresholds - more forgiving for better UX
    MATCH_THRESHOLD = 0.50  # Green - good match 
    CLOSE_THRESHOLD = 0.30  # Gray - close enough
    
    start_time = move['timestamp']
    end_time = move.get('end_timestamp', start_time + 2.0)
    
    ref_start = start_time - offset
    ref_end = end_time - offset
    
    # Check for video gap (no practice data available)
    if prac_duration > 0:
        # If practice video doesn't cover this time range, it's a gap
        if ref_start < 0 or ref_end > prac_duration:
            return {
                'status': 'gap',
                'match': False,
                'feedback': 'Practice video does not cover this section.',
                'tips': [],
                'similarity': 0.0
            }
    
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
    
    # Temporal smoothing: collect similarities with confidence weighting
    # Window size for temporal smoothing
    TEMPORAL_WINDOW = 3
    
    weighted_similarities = []
    for ref_frame in ref_frames:
        for prac_frame in prac_frames:
            if abs(ref_frame['timestamp'] - (prac_frame['timestamp'] + offset)) < 0.3:
                # Calculate confidence-weighted similarity
                ref_conf = ref_frame.get('confidence', 0.5)
                prac_conf = prac_frame.get('confidence', 0.5)
                avg_confidence = (ref_conf + prac_conf) / 2
                
                sim = pose_similarity(ref_frame['landmarks'], prac_frame['landmarks'])
                
                # Weight by confidence
                weighted_sim = sim * avg_confidence
                weighted_similarities.append({
                    'similarity': sim,
                    'weighted': weighted_sim,
                    'confidence': avg_confidence
                })
    
    if not weighted_similarities:
        return {
            'status': 'miss',
            'match': False,
            'feedback': 'Practice footage not aligned with reference for this move.',
            'tips': [],
            'similarity': 0.0
        }
    
    # Apply temporal smoothing: average over temporal window
    if len(weighted_similarities) > TEMPORAL_WINDOW:
        # Use moving average
        smoothed = []
        for i in range(len(weighted_similarities)):
            start = max(0, i - TEMPORAL_WINDOW // 2)
            end = min(len(weighted_similarities), i + TEMPORAL_WINDOW // 2 + 1)
            window = weighted_similarities[start:end]
            smoothed.append(np.mean([w['weighted'] for w in window]))
        avg_sim = np.mean(smoothed)
    else:
        avg_sim = np.mean([w['weighted'] for w in weighted_similarities])
    
    # Determine status based on thresholds
    if avg_sim >= MATCH_THRESHOLD:
        status = 'match'
        match = True
        feedback = "Great job! Your form closely matches the reference."
        tips = ["Keep up the good work!", "Try to maintain this consistency"]
    elif avg_sim >= CLOSE_THRESHOLD:
        status = 'close'
        match = False  # Not a "perfect" match but close enough
        feedback = "Good effort! You're on the right track."
        tips = ["Minor adjustments needed to perfect this move"]
    else:
        status = 'miss'
        match = False
        if avg_sim > 0.40:
            feedback = "Getting there! Keep practicing this section."
            tips = ["Focus on timing and body positioning"]
        else:
            feedback = "Needs work. Try breaking down the move into smaller parts."
            tips = ["Practice with a mirror", "Watch the reference video multiple times", "Focus on one body part at a time"]
    
    # Get detailed body part analysis for specific feedback
    body_analysis = get_detailed_body_feedback(ref_frames, prac_frames)
    
    # Add specific tips based on body part analysis
    tips.extend(body_analysis['tips'])
    
    # If we have very specific feedback, use it to enhance the main feedback
    if body_analysis['primary_issue']:
        feedback = body_analysis['primary_feedback']
    
    return {
        'status': status,
        'match': match,
        'feedback': feedback,
        'tips': tips[:4],  # Allow up to 4 tips now
        'similarity': float(avg_sim),
        'body_parts': body_analysis['summary']  # Include for debugging/display
    }


def get_detailed_body_feedback(ref_frames: list, prac_frames: list) -> dict:
    """
    Analyze specific body parts and provide detailed feedback.
    Returns tips for specific improvements.
    """
    if not ref_frames or not prac_frames:
        return {'tips': [], 'summary': {}, 'primary_issue': None, 'primary_feedback': ''}
    
    # Average landmarks for each body part
    def get_avg_landmarks(frames, indices):
        landmarks = [np.mean([f['landmarks'][i] for i in indices], axis=0) for f in frames]
        return np.mean(landmarks, axis=0) if landmarks else np.array([])
    
    # Body part definitions with specific landmark indices
    body_parts = {
        'left_arm': list(range(11, 17)),    # Left shoulder to wrist
        'right_arm': list(range(11, 17)),   # (use differently in analysis)
        'left_leg': [23, 25, 27, 29],      # Left hip, knee, ankle, foot
        'right_leg': [24, 26, 28, 30],     # Right hip, knee, ankle, foot  
        'torso': [11, 12, 23, 24],         # Shoulders and hips
        'shoulders': [11, 12],             # Just shoulders
        'hips': [23, 24],                  # Just hips
    }
    
    # Calculate differences for each body part
    differences = {}
    
    # Left arm (shoulder, elbow, wrist)
    ref_left_arm = get_avg_landmarks(ref_frames, [11, 13, 15])
    prac_left_arm = get_avg_landmarks(prac_frames, [11, 13, 15])
    if len(ref_left_arm) == 3 and len(prac_left_arm) == 3:
        diff = np.linalg.norm(ref_left_arm - prac_left_arm)
        differences['left_arm'] = diff
    
    # Right arm
    ref_right_arm = get_avg_landmarks(ref_frames, [12, 14, 16])
    prac_right_arm = get_avg_landmarks(prac_frames, [12, 14, 16])
    if len(ref_right_arm) == 3 and len(prac_right_arm) == 3:
        diff = np.linalg.norm(ref_right_arm - prac_right_arm)
        differences['right_arm'] = diff
    
    # Left leg
    ref_left_leg = get_avg_landmarks(ref_frames, [23, 25, 27])
    prac_left_leg = get_avg_landmarks(prac_frames, [23, 25, 27])
    if len(ref_left_leg) == 3 and len(prac_left_leg) == 3:
        diff = np.linalg.norm(ref_left_leg - prac_left_leg)
        differences['left_leg'] = diff
    
    # Right leg  
    ref_right_leg = get_avg_landmarks(ref_frames, [24, 26, 28])
    prac_right_leg = get_avg_landmarks(prac_frames, [24, 26, 28])
    if len(ref_right_leg) == 3 and len(prac_right_leg) == 3:
        diff = np.linalg.norm(ref_right_leg - prac_right_leg)
        differences['right_leg'] = diff
    
    # Torso/upper body
    ref_torso = get_avg_landmarks(ref_frames, [11, 12, 23, 24])
    prac_torso = get_avg_landmarks(prac_frames, [11, 12, 23, 24])
    if len(ref_torso) == 4 and len(prac_torso) == 4:
        # Check both position and orientation
        ref_shoulder_mid = (ref_frames[0]['landmarks'][11] + ref_frames[0]['landmarks'][12]) / 2
        prac_shoulder_mid = (prac_frames[0]['landmarks'][11] + prac_frames[0]['landmarks'][12]) / 2
        ref_hip_mid = (ref_frames[0]['landmarks'][23] + ref_frames[0]['landmarks'][24]) / 2
        prac_hip_mid = (prac_frames[0]['landmarks'][23] + prac_frames[0]['landmarks'][24]) / 2
        
        # Torso lean angle
        ref_torso_angle = np.arctan2(ref_shoulder_mid[1] - ref_hip_mid[1], 
                                      ref_shoulder_mid[0] - ref_hip_mid[0])
        prac_torso_angle = np.arctan2(prac_shoulder_mid[1] - prac_hip_mid[1],
                                       prac_shoulder_mid[0] - prac_hip_mid[0])
        torso_angle_diff = abs(ref_torso_angle - prac_torso_angle)
        differences['torso_angle'] = torso_angle_diff
        
        # Torso position
        torso_pos_diff = np.linalg.norm((ref_shoulder_mid + ref_hip_mid) - (prac_shoulder_mid + prac_hip_mid))
        differences['torso_position'] = torso_pos_diff
    
    # Generate specific tips based on biggest differences
    tips = []
    threshold = 0.05  # Lower threshold to catch more differences
    
    sorted_diffs = sorted(differences.items(), key=lambda x: x[1], reverse=True)
    
    primary_issue = None
    primary_feedback = ""
    
    for part, diff in sorted_diffs[:3]:  # Top 3 issues
        if diff < threshold:
            continue
            
        if part == 'left_arm':
            tips.append("Raise or extend your left arm more")
            if not primary_issue:
                primary_issue = 'left_arm'
                primary_feedback = "Work on extending your left arm fully"
        elif part == 'right_arm':
            tips.append("Raise or extend your right arm more")
            if not primary_issue:
                primary_issue = 'right_arm'
                primary_feedback = "Focus on your right arm positioning"
        elif part == 'left_leg':
            tips.append("Adjust your left footwork or stance")
            if not primary_issue:
                primary_issue = 'left_leg'
                primary_feedback = "Pay attention to your left leg positioning"
        elif part == 'right_leg':
            tips.append("Adjust your right footwork or stance")
            if not primary_issue:
                primary_issue = 'right_leg'
                primary_feedback = "Focus on your right leg stability"
        elif part == 'torso_angle':
            tips.append("Be more loose/fluid in your torso")
            if not primary_issue:
                primary_issue = 'torso_angle'
                primary_feedback = "Try to match the torso movement more closely"
        elif part == 'torso_position':
            tips.append("Stand up straighter or adjust your posture")
            if not primary_issue:
                primary_issue = 'torso_position'
                primary_feedback = "Work on your overall posture"
    
    return {
        'tips': tips,
        'summary': {k: float(v) for k, v in differences.items()},
        'primary_issue': primary_issue,
        'primary_feedback': primary_feedback
    }


def analyze_body_part(ref_frames: list, prac_frames: list, landmark_indices: list) -> float:
    """Calculate difference for specific body part landmarks."""
    if not ref_frames or not prac_frames:
        return 0.0
    
    ref_part = np.mean([np.mean(p['landmarks'][landmark_indices], axis=0) for p in ref_frames], axis=0)
    prac_part = np.mean([np.mean(p['landmarks'][landmark_indices], axis=0) for p in prac_frames], axis=0)
    
    return float(np.linalg.norm(ref_part - prac_part))


def analyze_videos(ref_video_path: str, prac_video_path: str, offset: float = 0) -> dict:
    """
    Main function to analyze reference and practice videos.
    
    Returns dict with:
        - overallScore: int (0-100)
        - moves: list of dicts with id, timestamp, label, match, feedback, tips
    """
    global _model_available
    
    if not _model_available or options is None:
        return {
            'success': False,
            'error': 'Pose landmarker model not loaded. Please download the model from https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker and save as /tmp/pose_landmarker.task',
            'overallScore': 78,
            'moves': [
                {
                    'id': 1,
                    'timestamp': '0:05',
                    'label': 'Move 1',
                    'match': True,
                    'feedback': 'Great job! (Demo mode - model not loaded)',
                    'tips': []
                },
                {
                    'id': 2,
                    'timestamp': '0:12',
                    'label': 'Move 2',
                    'match': True,
                    'feedback': 'Good effort! (Demo mode - model not loaded)',
                    'tips': []
                },
            ]
        }
    
    ref_poses = extract_poses(ref_video_path)
    prac_poses = extract_poses(prac_video_path)
    
    if not ref_poses:
        return {
            'success': False,
            'error': 'Could not detect poses in reference video',
            'overallScore': 0,
            'moves': []
        }
    
    if not prac_poses:
        return {
            'success': False,
            'error': 'Could not detect poses in practice video',
            'overallScore': 0,
            'moves': []
        }
    
    ref_moves = detect_moves(ref_poses)
    
    # Get video durations for gap detection
    ref_duration = ref_poses[-1]['timestamp'] if ref_poses else 0
    prac_duration = prac_poses[-1]['timestamp'] if prac_poses else 0
    
    if not ref_moves:
        ref_moves = [{'timestamp': ref_poses[0]['timestamp'], 'start_idx': 0, 'end_idx': len(ref_poses) - 1}]
    
    for i, move in enumerate(ref_moves):
        if i + 1 < len(ref_moves):
            move['end_timestamp'] = ref_moves[i + 1]['timestamp']
        else:
            move['end_timestamp'] = ref_poses[-1]['timestamp'] + 1.0
    
    moves = []
    total_similarity = 0
    matched_count = 0
    
    # Check if entire video is one move (high overall similarity)
    overall_sim = 0
    if ref_poses and prac_poses:
        sample_ref = ref_poses[min(10, len(ref_poses)-1)]['landmarks']
        sample_prac = prac_poses[min(10, len(prac_poses)-1)]['landmarks']
        overall_sim = pose_similarity(sample_ref, sample_prac)
    
    is_full_match = len(ref_moves) <= 1 and overall_sim > 0.70
    
    for i, move in enumerate(ref_moves):
        quality = analyze_move_quality(ref_poses, prac_poses, move, offset, ref_duration, prac_duration)
        
        # More descriptive labels
        if is_full_match:
            move_label = "Full Routine"
        else:
            duration = move.get('duration', 2.0)
            ts = format_timestamp(move['timestamp'])
            move_label = f"{ts} ({duration:.1f}s)"
        
        moves.append({
            'id': i + 1,
            'timestamp': format_timestamp(move['timestamp']),
            'label': move_label,
            'status': quality.get('status', 'miss'),
            'match': quality['match'],
            'feedback': quality['feedback'],
            'tips': quality['tips']
        })
        
        total_similarity += quality.get('similarity', 0)
        # Count both "match" and "close" as correct for scoring
        if quality.get('status') in ['match', 'close']:
            matched_count += 1
    
    # Only count non-gap moves in the score
    scored_moves = len([m for m in moves if m.get('status') != 'gap'])
    overall_score = int((matched_count / scored_moves) * 100) if scored_moves > 0 else 0
    
    return {
        'success': True,
        'overallScore': int(overall_score),
        'moves': [
            {
                'id': int(m['id']),
                'timestamp': str(m['timestamp']),
                'label': str(m['label']),
                'status': str(m.get('status', 'miss')),
                'match': bool(m['match']),
                'feedback': str(m['feedback']),
                'tips': list(m['tips'])
            }
            for m in moves
        ]
    }


def format_timestamp(seconds: float) -> str:
    """Format seconds as MM:SS."""
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins}:{secs:02d}"
