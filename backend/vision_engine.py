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

def get_pose_landmarker():
    global pose_landmarker
    if pose_landmarker is None and options:
        try:
            pose_landmarker = PoseLandmarker.create_from_options(options)
        except Exception as e:
            print(f"Error creating pose landmarker: {e}")
    return pose_landmarker


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
                    landmarks = np.array([[lm.x, lm.y, lm.z] for lm in result.pose_landmarks[0]])
                    confidences = [lm.visibility for lm in result.pose_landmarks[0]]
                    confidence = np.mean(confidences) if confidences else 0
                    poses.append({
                        'timestamp': timestamp,
                        'landmarks': landmarks,
                        'confidence': confidence
                    })
            
            frame_idx += 1
    finally:
        cap.release()
    
    return poses


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
    
    norm1 = normalize_pose(pose1)
    norm2 = normalize_pose(pose2)
    
    similarity = 1 - spatial.distance.cosine(norm1.flatten(), norm2.flatten())
    
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


def detect_moves(poses: list, threshold: float = 0.15) -> list:
    """
    Detect distinct moves based on significant pose changes.
    Returns list of move timestamps.
    """
    if len(poses) < 2:
        return []
    
    moves = []
    prev_pose = poses[0]['landmarks']
    move_start = 0
    
    for i in range(1, len(poses)):
        curr_pose = poses[i]['landmarks']
        diff = np.linalg.norm(curr_pose - prev_pose)
        
        if diff > threshold:
            if i - move_start > 3:
                moves.append({
                    'timestamp': poses[move_start]['timestamp'],
                    'start_idx': move_start,
                    'end_idx': i
                })
            move_start = i
        prev_pose = curr_pose
    
    if len(poses) - move_start > 3:
        moves.append({
            'timestamp': poses[move_start]['timestamp'],
            'start_idx': move_start,
            'end_idx': len(poses) - 1
        })
    
    return moves


def analyze_move_quality(ref_poses: list, prac_poses: list, move: dict, offset: float) -> dict:
    """
    Analyze quality of a specific move.
    Returns match status, feedback, and tips.
    """
    start_time = move['timestamp']
    end_time = move.get('end_timestamp', start_time + 2.0)
    
    ref_start = start_time - offset
    ref_end = end_time - offset
    
    ref_frames = [p for p in ref_poses if start_time <= p['timestamp'] <= end_time]
    prac_frames = [p for p in prac_poses if ref_start <= p['timestamp'] <= ref_end]
    
    if not ref_frames or not prac_frames:
        return {
            'match': False,
            'feedback': 'Could not analyze this move.',
            'tips': [],
            'similarity': 0.0
        }
    
    similarities = []
    for ref_frame in ref_frames:
        for prac_frame in prac_frames:
            if abs(ref_frame['timestamp'] - (prac_frame['timestamp'] + offset)) < 0.3:
                sim = pose_similarity(ref_frame['landmarks'], prac_frame['landmarks'])
                similarities.append(sim)
    
    if not similarities:
        return {
            'match': False,
            'feedback': 'Practice footage not aligned with reference for this move.',
            'tips': [],
            'similarity': 0.0
        }
    
    avg_sim = np.mean(similarities)
    match = avg_sim > 0.75
    
    if avg_sim > 0.85:
        feedback = "Great job! Your form closely matches the reference."
        tips = ["Keep up the good work!", "Try to maintain this consistency"]
    elif avg_sim > 0.75:
        feedback = "Good effort! Minor adjustments needed."
        tips = ["Focus on the specific body parts mentioned in feedback"]
    elif avg_sim > 0.6:
        feedback = "Getting there! Significant differences in form."
        tips = ["Study the reference more carefully", "Slow down and practice the move in parts"]
    else:
        feedback = "Needs work. Try breaking down the move into smaller parts."
        tips = ["Practice with a mirror", "Watch the reference video multiple times", "Focus on one body part at a time"]
    
    arm_diff = analyze_body_part(ref_frames, prac_frames, [11, 12, 13, 14, 15, 16, 23, 24])
    leg_diff = analyze_body_part(ref_frames, prac_frames, [23, 24, 25, 26, 27, 28])
    torso_diff = analyze_body_part(ref_frames, prac_frames, [11, 12, 23, 24])
    
    if arm_diff > 0.2:
        tips.append("Pay more attention to arm positioning")
    if leg_diff > 0.2:
        tips.append("Focus on leg stability and footwork")
    if torso_diff > 0.2:
        tips.append("Work on core engagement and torso posture")
    
    return {
        'match': match,
        'feedback': feedback,
        'tips': tips[:3],
        'similarity': float(avg_sim)
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
    
    for i, move in enumerate(ref_moves):
        quality = analyze_move_quality(ref_poses, prac_poses, move, offset)
        
        move_label = f"Move {i + 1}"
        
        moves.append({
            'id': i + 1,
            'timestamp': format_timestamp(move['timestamp']),
            'label': move_label,
            'match': quality['match'],
            'feedback': quality['feedback'],
            'tips': quality['tips']
        })
        
        total_similarity += quality.get('similarity', 0)
        if quality['match']:
            matched_count += 1
    
    overall_score = int((matched_count / len(moves)) * 100) if moves else 0
    
    return {
        'success': True,
        'overallScore': overall_score,
        'moves': moves
    }


def format_timestamp(seconds: float) -> str:
    """Format seconds as MM:SS."""
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins}:{secs:02d}"
