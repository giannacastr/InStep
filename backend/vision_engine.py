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

# Black/dark frame detection: mean brightness below this = padding (excluded from grading)
BLACK_FRAME_BRIGHTNESS_THRESHOLD = 18


def extract_black_ranges(video_path: str) -> list[tuple[float, float]]:
    """
    Detect black/dark padding frames in video. Returns list of (start_sec, end_sec) ranges
    where the frame is considered black (mean brightness < threshold).
    These seconds should NOT count toward grading.
    Uses same frame sampling as pose extraction to ensure timestamp alignment.
    """
    if not os.path.isfile(video_path):
        return []
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return []
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    black_ranges = []
    in_black = False
    black_start = 0.0
    frame_idx = 0
    last_black_frame = -1
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Use same sampling rate as pose extraction for timestamp alignment
            if frame_idx % FRAME_SAMPLE_RATE == 0:
                timestamp = frame_idx / fps
                # Check if frame is black/dark (padding)
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                mean_brightness = np.mean(gray)
                is_black = mean_brightness < BLACK_FRAME_BRIGHTNESS_THRESHOLD
                
                if is_black:
                    if not in_black:
                        in_black = True
                        black_start = timestamp
                    last_black_frame = frame_idx
                else:
                    if in_black:
                        in_black = False
                        # Use timestamp of last black frame for end time
                        black_end = last_black_frame / fps if last_black_frame >= 0 else timestamp
                        black_ranges.append((black_start, black_end))
                        last_black_frame = -1
            
            frame_idx += 1
        
        # Handle case where video ends in black
        if in_black:
            black_end = frame_idx / fps
            black_ranges.append((black_start, black_end))
    finally:
        cap.release()
    
    # Merge adjacent/overlapping black ranges (within 0.2s gap for better alignment)
    merged = []
    for start, end in sorted(black_ranges):
        if merged and start - merged[-1][1] <= 0.2:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    
    return merged


def _time_in_black_ranges(t: float, ranges: list[tuple[float, float]]) -> bool:
    """Check if timestamp t falls within any black range."""
    for start, end in ranges:
        if start <= t < end:
            return True
    return False


def _range_overlaps_black(start: float, end: float, ranges: list[tuple[float, float]]) -> bool:
    """Check if time range [start, end] overlaps any black range."""
    for b_start, b_end in ranges:
        if not (end <= b_start or start >= b_end):
            return True
    return False


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
    Detect distinct key dance moves based on significant pose changes.
    Splits on pose transitions - key moves are typically 0.5-2.5 seconds.
    Only includes segments where person is clearly visible (not cut off).
    """
    if len(poses) < 3:
        return []
    
    # Filter to high-confidence poses (body clearly visible, not cut off)
    MIN_CONFIDENCE = 0.4  # Higher = ensure person is fully in frame
    valid_poses = [p for p in poses if p.get('confidence', 0) >= MIN_CONFIDENCE]
    if len(valid_poses) < 3:
        return []
    
    # Compute pose change magnitude between consecutive frames
    # Key dance moves = significant pose transitions
    POSE_CHANGE_THRESHOLD = 0.08  # Lower threshold = more sensitive to changes (was 0.12)
    MIN_MOVE_DURATION = 0.3       # Seconds - minimum key move length (was 0.4)
    MAX_MOVE_DURATION = 2.0       # Seconds - max before forcing split (was 2.5, stricter)
    TARGET_MOVES_PER_30S = 18     # Target ~18 moves per 30s (was 15, more granular)
    
    video_duration = valid_poses[-1]['timestamp'] - valid_poses[0]['timestamp']
    if video_duration <= 0:
        return []
    
    # Build change scores between consecutive poses
    # Use normalized landmarks for more accurate change detection
    changes = []
    for i in range(1, len(valid_poses)):
        lm1 = normalize_pose(valid_poses[i - 1]['landmarks'])
        lm2 = normalize_pose(valid_poses[i]['landmarks'])
        # Use both position difference and angle difference for better detection
        pos_diff = np.linalg.norm(lm2 - lm1)
        angles1 = calculate_joint_angles(valid_poses[i - 1]['landmarks'])
        angles2 = calculate_joint_angles(valid_poses[i]['landmarks'])
        angle_diff = np.mean(np.abs(angles2 - angles1)) if len(angles1) > 0 and len(angles2) > 0 else 0
        # Combined change score
        diff = pos_diff + angle_diff * 0.5
        changes.append((valid_poses[i]['timestamp'], diff))
    
    if not changes:
        return [{
            'timestamp': valid_poses[0]['timestamp'],
            'start_idx': 0,
            'end_idx': len(valid_poses) - 1,
            'duration': valid_poses[-1]['timestamp'] - valid_poses[0]['timestamp']
        }]
    
    # Split at significant pose changes; also enforce max duration
    moves = []
    move_start_idx = 0
    move_start_time = valid_poses[0]['timestamp']
    
    for i in range(1, len(valid_poses)):
        t = valid_poses[i]['timestamp']
        duration_so_far = t - move_start_time
        change_at_i = changes[i - 1][1] if i - 1 < len(changes) else 0
        
        # New move if: big pose change, or max duration exceeded
        force_split = (
            change_at_i >= POSE_CHANGE_THRESHOLD and duration_so_far >= MIN_MOVE_DURATION
        ) or duration_so_far >= MAX_MOVE_DURATION
        
        if force_split and i - move_start_idx >= 2:
            moves.append({
                'timestamp': move_start_time,
                'start_idx': move_start_idx,
                'end_idx': i - 1,
                'duration': valid_poses[i - 1]['timestamp'] - move_start_time
            })
            move_start_idx = i
            move_start_time = t
    
    # Final move
    if move_start_idx < len(valid_poses):
        moves.append({
            'timestamp': move_start_time,
            'start_idx': move_start_idx,
            'end_idx': len(valid_poses) - 1,
            'duration': valid_poses[-1]['timestamp'] - move_start_time
        })
    
    # If we got too few moves, aggressively subdivide the longest ones
    target_count = max(10, int(video_duration / 30 * TARGET_MOVES_PER_30S))
    iterations = 0
    while len(moves) < target_count and len(moves) > 0 and iterations < 30:
        longest = max(moves, key=lambda m: m['duration'])
        if longest['duration'] < MIN_MOVE_DURATION * 1.5:  # More aggressive splitting
            break
        idx = moves.index(longest)
        # Find midpoint pose index
        mid = (longest['start_idx'] + longest['end_idx']) // 2
        if mid <= longest['start_idx'] or mid >= longest['end_idx']:
            break
        t_mid = valid_poses[mid]['timestamp']
        moves[idx] = {
            'timestamp': longest['timestamp'],
            'start_idx': longest['start_idx'],
            'end_idx': mid,
            'duration': t_mid - longest['timestamp']
        }
        moves.insert(idx + 1, {
            'timestamp': t_mid,
            'start_idx': mid,
            'end_idx': longest['end_idx'],
            'duration': valid_poses[longest['end_idx']]['timestamp'] - t_mid
        })
        iterations += 1
    
    return moves


def analyze_move_quality(ref_poses: list, prac_poses: list, move: dict, offset: float, ref_duration: float = 0, prac_duration: float = 0, ref_black_ranges: list = None, prac_black_ranges: list = None) -> dict:
    """
    Analyze quality of a specific move.
    Returns match status, feedback, and tips.
    
    Status values:
    - "match": Style really matches (green) - high similarity
    - "close": Close enough (gray) - counts as CORRECT for score, minor adjustments
    - "miss": Poor match (red) - needs work, show suggestions
    - "gap": No practice data (black padding / video gap)
    """
    # Thresholds: green = great match, gray = acceptable (counts correct), red = needs work
    # Made stricter to prevent false 100% scores
    MATCH_THRESHOLD = 0.72   # Green - style really matches (was 0.65, stricter)
    CLOSE_THRESHOLD = 0.52   # Gray - close enough, counts as correct (was 0.45, stricter)
    
    start_time = move['timestamp']
    end_time = move.get('end_timestamp', start_time + 2.0)
    
    ref_start = start_time - offset
    ref_end = end_time - offset
    
    # Exclude moves in black padding (either video) - do NOT count toward grading
    if ref_black_ranges and _range_overlaps_black(start_time, end_time, ref_black_ranges):
        return {'status': 'gap', 'match': False, 'feedback': 'Reference video is black/padding here.', 'tips': [], 'similarity': 0.0}
    if prac_black_ranges and _range_overlaps_black(ref_start, ref_end, prac_black_ranges):
        return {'status': 'gap', 'match': False, 'feedback': 'Practice video is black/padding here.', 'tips': [], 'similarity': 0.0}
    
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
    
    # CRITICAL: Filter out frames that are in black ranges BEFORE comparing
    # Check each frame individually to ensure we don't compare when one video is black
    ref_frames_filtered = []
    for rf in ref_frames:
        if ref_black_ranges and _time_in_black_ranges(rf['timestamp'], ref_black_ranges):
            continue  # Skip this frame - reference is black
        ref_frames_filtered.append(rf)
    ref_frames = ref_frames_filtered
    
    prac_frames_filtered = []
    for pf in prac_frames:
        # Practice video time is in practice timeline, check against practice black ranges
        if prac_black_ranges and _time_in_black_ranges(pf['timestamp'], prac_black_ranges):
            continue  # Skip this frame - practice is black
        prac_frames_filtered.append(pf)
    prac_frames = prac_frames_filtered
    
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
            # Align timestamps: ref_time = prac_time + offset, so prac_time = ref_time - offset
            ref_time = ref_frame['timestamp']
            prac_time = prac_frame['timestamp']
            expected_prac_time = ref_time - offset
            
            if abs(prac_time - expected_prac_time) < 0.3:
                # Double-check: ensure neither frame is in black range at comparison time
                if ref_black_ranges and _time_in_black_ranges(ref_time, ref_black_ranges):
                    continue  # Reference is black at this time
                if prac_black_ranges and _time_in_black_ranges(prac_time, prac_black_ranges):
                    continue  # Practice is black at this time
                
                # Calculate confidence-weighted similarity
                ref_conf = ref_frame.get('confidence', 0.5)
                prac_conf = prac_frame.get('confidence', 0.5)
                avg_confidence = (ref_conf + prac_conf) / 2
                
                # Require minimum confidence to compare (avoid comparing low-quality poses)
                if avg_confidence < 0.35:
                    continue
                
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
        match = True   # Counts as CORRECT for overall score (gray on scrubber)
        feedback = "Good effort! You're on the right track—minor polish would make it perfect."
        tips = ["Small refinements could elevate this move"]
    else:
        status = 'miss'
        match = False
        if avg_sim > 0.40:
            feedback = "Getting there! Keep practicing this section."
            tips = ["Focus on timing and body positioning"]
        else:
            feedback = "Needs work. Try breaking down the move into smaller parts."
            tips = ["Practice with a mirror", "Watch the reference video multiple times", "Focus on one body part at a time"]
    
    # Only add detailed body tips for miss (red) - genuinely helpful suggestions
    body_analysis = {'summary': {}, 'tips': []}
    if status == 'miss':
        body_analysis = get_detailed_body_feedback(ref_frames, prac_frames)
        tips = body_analysis['tips']  # Replace generic tips with specific ones
        if body_analysis['primary_issue'] and body_analysis['primary_feedback']:
            feedback = body_analysis['primary_feedback']
    
    return {
        'status': status,
        'match': match,
        'feedback': feedback,
        'tips': tips[:4],  # Allow up to 4 tips now
        'similarity': float(avg_sim),
        'body_parts': body_analysis.get('summary', {})  # Include for debugging/display
    }


def _angle_between(p1: np.ndarray, p2: np.ndarray, p3: np.ndarray) -> float:
    """Angle at p2 formed by p1-p2-p3, in radians."""
    v1 = p1 - p2
    v2 = p3 - p2
    n1, n2 = np.linalg.norm(v1) + 1e-8, np.linalg.norm(v2) + 1e-8
    cos_a = np.clip(np.dot(v1, v2) / (n1 * n2), -1, 1)
    return np.arccos(cos_a)


def get_detailed_body_feedback(ref_frames: list, prac_frames: list) -> dict:
    """
    Analyze specific body parts and provide genuinely helpful, actionable tips.
    Uses joint angles and positions to infer: "loosen your shoulders", "straighten your right arm", etc.
    """
    if not ref_frames or not prac_frames:
        return {'tips': [], 'summary': {}, 'primary_issue': None, 'primary_feedback': ''}
    
    def avg_landmarks(frames, idx):
        return np.mean([f['landmarks'][idx] for f in frames], axis=0)
    
    issues = []  # (priority_score, tip, primary_feedback)
    
    # --- Shoulders: compare height and tension (shoulder-to-shoulder vs ref)
    ref_l = avg_landmarks(ref_frames, 11)
    ref_r = avg_landmarks(ref_frames, 12)
    prac_l = avg_landmarks(prac_frames, 11)
    prac_r = avg_landmarks(prac_frames, 12)
    ref_shoulder_height = (ref_l[1] + ref_r[1]) / 2
    prac_shoulder_height = (prac_l[1] + prac_r[1]) / 2
    shoulder_height_diff = prac_shoulder_height - ref_shoulder_height
    if shoulder_height_diff > 0.03:  # Practice shoulders higher = tense
        issues.append((0.9, "Loosen your shoulders—let them drop naturally", "Your shoulders look tense; try to relax them"))
    elif shoulder_height_diff < -0.03:
        issues.append((0.7, "Engage your shoulders slightly—avoid slouching", "Your shoulders could be more engaged"))
    
    # --- Arm angles: elbow bend (straight vs bent)
    # Left: shoulder 11, elbow 13, wrist 15
    ref_left_elbow = _angle_between(avg_landmarks(ref_frames, 11), avg_landmarks(ref_frames, 13), avg_landmarks(ref_frames, 15))
    prac_left_elbow = _angle_between(avg_landmarks(prac_frames, 11), avg_landmarks(prac_frames, 13), avg_landmarks(prac_frames, 15))
    left_elbow_diff = prac_left_elbow - ref_left_elbow
    if left_elbow_diff > 0.25:  # Practice arm more bent
        issues.append((0.85, "Straighten your left arm more", "Your left arm is more bent than the reference"))
    elif left_elbow_diff < -0.25:
        issues.append((0.75, "Bend your left arm slightly to match the reference", "Your left arm is straighter than the reference"))
    
    # Right arm
    ref_right_elbow = _angle_between(avg_landmarks(ref_frames, 12), avg_landmarks(ref_frames, 14), avg_landmarks(ref_frames, 16))
    prac_right_elbow = _angle_between(avg_landmarks(prac_frames, 12), avg_landmarks(prac_frames, 14), avg_landmarks(prac_frames, 16))
    right_elbow_diff = prac_right_elbow - ref_right_elbow
    if right_elbow_diff > 0.25:
        issues.append((0.85, "Straighten your right arm more", "Your right arm is more bent than the reference"))
    elif right_elbow_diff < -0.25:
        issues.append((0.75, "Bend your right arm slightly to match the reference", "Your right arm is straighter than the reference"))
    
    # --- Arm height: wrist relative to shoulder
    ref_left_wrist_y = np.mean([f['landmarks'][15][1] for f in ref_frames])
    prac_left_wrist_y = np.mean([f['landmarks'][15][1] for f in prac_frames])
    if prac_left_wrist_y - ref_left_wrist_y > 0.04:
        issues.append((0.7, "Raise your left arm higher", "Your left arm could be lifted more"))
    elif prac_left_wrist_y - ref_left_wrist_y < -0.04:
        issues.append((0.65, "Lower your left arm slightly", "Your left arm is higher than the reference"))
    
    ref_right_wrist_y = np.mean([f['landmarks'][16][1] for f in ref_frames])
    prac_right_wrist_y = np.mean([f['landmarks'][16][1] for f in prac_frames])
    if prac_right_wrist_y - ref_right_wrist_y > 0.04:
        issues.append((0.7, "Raise your right arm higher", "Your right arm could be lifted more"))
    elif prac_right_wrist_y - ref_right_wrist_y < -0.04:
        issues.append((0.65, "Lower your right arm slightly", "Your right arm is higher than the reference"))
    
    # --- Torso lean
    ref_shoulder_mid = (ref_l + ref_r) / 2
    ref_hip_mid = (avg_landmarks(ref_frames, 23) + avg_landmarks(ref_frames, 24)) / 2
    prac_shoulder_mid = (prac_l + prac_r) / 2
    prac_hip_mid = (avg_landmarks(prac_frames, 23) + avg_landmarks(prac_frames, 24)) / 2
    ref_torso_angle = np.arctan2(ref_shoulder_mid[1] - ref_hip_mid[1], ref_shoulder_mid[0] - ref_hip_mid[0] + 1e-8)
    prac_torso_angle = np.arctan2(prac_shoulder_mid[1] - prac_hip_mid[1], prac_shoulder_mid[0] - prac_hip_mid[0] + 1e-8)
    torso_diff = abs(ref_torso_angle - prac_torso_angle)
    if torso_diff > 0.3:
        issues.append((0.8, "Match the torso lean—shift your weight in the same direction", "Your torso angle doesn't match the reference"))
    
    # --- Hip/knee (leg stance)
    ref_left_knee = avg_landmarks(ref_frames, 25)
    prac_left_knee = avg_landmarks(prac_frames, 25)
    ref_right_knee = avg_landmarks(ref_frames, 26)
    prac_right_knee = avg_landmarks(prac_frames, 26)
    knee_spread_ref = np.linalg.norm(ref_left_knee[:2] - ref_right_knee[:2])
    knee_spread_prac = np.linalg.norm(prac_left_knee[:2] - prac_right_knee[:2])
    if abs(knee_spread_prac - knee_spread_ref) > 0.08:
        if knee_spread_prac < knee_spread_ref:
            issues.append((0.6, "Widen your stance slightly", "Your feet are closer together than the reference"))
        else:
            issues.append((0.6, "Bring your feet slightly closer together", "Your stance is wider than the reference"))
    
    # Sort by priority, take top 3, deduplicate by body part
    issues.sort(key=lambda x: -x[0])
    tips = []
    seen = set()
    for _, tip, _ in issues[:5]:
        key = tip.split()[1] if len(tip.split()) > 1 else tip[:20]
        if key not in seen:
            seen.add(key)
            tips.append(tip)
            if len(tips) >= 3:
                break
    
    primary_feedback = issues[0][2] if issues else ""
    primary_issue = "body" if issues else None
    
    return {
        'tips': tips[:4],
        'summary': {},
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
    ref_black_ranges = extract_black_ranges(ref_video_path)
    prac_black_ranges = extract_black_ranges(prac_video_path)
    
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
        quality = analyze_move_quality(ref_poses, prac_poses, move, offset, ref_duration, prac_duration, ref_black_ranges, prac_black_ranges)
        
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
    
    # Prevent false 100% scores: require minimum number of moves or use weighted average
    if scored_moves > 0:
        if scored_moves < 5:
            # With very few moves, be more conservative - use similarity-weighted score
            total_weighted = sum(m.get('similarity', 0) * (1 if m.get('status') in ['match', 'close'] else 0) 
                                for m in moves if m.get('status') != 'gap')
            overall_score = int((total_weighted / scored_moves) * 100)
        else:
            overall_score = int((matched_count / scored_moves) * 100)
    else:
        overall_score = 0
    
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
