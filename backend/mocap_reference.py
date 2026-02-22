"""
Motion Capture Reference System

Allows using pre-recorded motion capture data as reference instead of video.
This provides pristine, high-quality reference data for grading.
"""
import os
from typing import Optional, List, Dict
from mocap_loader import load_mocap_data, mocap_to_dataframe
# Imports handled locally to avoid circular dependencies


class MocapReference:
    """
    Wrapper for motion capture reference data.
    Can be used as a drop-in replacement for video-based reference.
    """
    
    def __init__(self, mocap_path: str, format_type: Optional[str] = None, fps: float = 30.0):
        """
        Load motion capture reference data.
        
        Args:
            mocap_path: Path to mocap file (JSON, etc.)
            format_type: Optional format hint ('cmu', 'aist', 'mixamo', etc.)
            fps: Frames per second
        """
        self.mocap_path = mocap_path
        self.poses = load_mocap_data(mocap_path, format_type=format_type, fps=fps)
        self.duration = self.poses[-1]['timestamp'] if self.poses else 0.0
        self.fps = fps
    
    def get_poses(self) -> List[Dict]:
        """Get poses in MediaPipe-compatible format."""
        return self.poses
    
    def get_duration(self) -> float:
        """Get duration in seconds."""
        return self.duration
    
    def sample_at_time(self, timestamp: float, tolerance: float = 0.1) -> Optional[Dict]:
        """
        Get pose closest to given timestamp.
        
        Args:
            timestamp: Target timestamp in seconds
            tolerance: Maximum time difference to accept
        
        Returns:
            Pose dict or None if no pose found within tolerance
        """
        best_pose = None
        best_diff = float('inf')
        
        for pose in self.poses:
            diff = abs(pose['timestamp'] - timestamp)
            if diff < best_diff:
                best_diff = diff
                best_pose = pose
        
        if best_diff <= tolerance:
            return best_pose
        return None


def analyze_with_mocap_reference(
    mocap_ref_path: str,
    prac_video_path: str,
    offset: float = 0.0,
    mocap_format: Optional[str] = None,
    mocap_fps: float = 30.0
) -> Dict:
    """
    Analyze practice video against motion capture reference.
    
    This is a drop-in replacement for analyze_videos() but uses mocap data
    instead of extracting poses from a reference video.
    
    Args:
        mocap_ref_path: Path to motion capture reference file
        prac_video_path: Path to practice video
        offset: Time offset for synchronization (from audio sync)
        mocap_format: Optional format hint
        mocap_fps: FPS of mocap data
    
    Returns:
        Analysis result dict (same format as analyze_videos)
    """
    # Load mocap reference
    mocap_ref = MocapReference(mocap_ref_path, format_type=mocap_format, fps=mocap_fps)
    ref_poses = mocap_ref.get_poses()
    
    if not ref_poses:
        return {
            'success': False,
            'error': 'Could not load motion capture reference data',
            'overallScore': 0,
            'moves': []
        }
    
    # Extract poses from practice video
    import vision_engine as ve
    
    prac_poses = ve.extract_poses(prac_video_path)
    prac_black_ranges = ve.extract_black_ranges(prac_video_path)
    
    if not prac_poses:
        return {
            'success': False,
            'error': 'Could not detect poses in practice video',
            'overallScore': 0,
            'moves': []
        }
    
    # Mocap data has no black ranges (it's clean data)
    ref_black_ranges = []
    
    # Detect moves in reference (mocap)
    ref_moves = ve.detect_moves(ref_poses)
    
    # Get durations
    ref_duration = mocap_ref.get_duration()
    prac_duration = prac_poses[-1]['timestamp'] if prac_poses else 0
    
    if not ref_moves:
        ref_moves = [{
            'timestamp': ref_poses[0]['timestamp'],
            'start_idx': 0,
            'end_idx': len(ref_poses) - 1
        }]
    
    # Set end timestamps for moves
    for i, move in enumerate(ref_moves):
        if i + 1 < len(ref_moves):
            move['end_timestamp'] = ref_moves[i + 1]['timestamp']
        else:
            move['end_timestamp'] = ref_duration
    
    # Analyze each move
    moves = []
    matched_count = 0
    
    for i, move in enumerate(ref_moves):
        quality = ve.analyze_move_quality(
            ref_poses, prac_poses, move, offset,
            ref_duration, prac_duration,
            ref_black_ranges, prac_black_ranges
        )
        
        duration = move.get('duration', move.get('end_timestamp', ref_duration) - move['timestamp'])
        ts = ve.format_timestamp(move['timestamp'])
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
        
        if quality.get('status') in ['match', 'close']:
            matched_count += 1
    
    # Calculate score
    scored_moves = len([m for m in moves if m.get('status') != 'gap'])
    
    if scored_moves > 0:
        if scored_moves < 5:
            total_weighted = sum(
                m.get('similarity', 0) * (1 if m.get('status') in ['match', 'close'] else 0)
                for m in moves if m.get('status') != 'gap'
            )
            overall_score = int((total_weighted / scored_moves) * 100)
        else:
            overall_score = int((matched_count / scored_moves) * 100)
    else:
        overall_score = 0
    
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
                'feedback': str(m['feedback']),
                'tips': list(m['tips'])
            }
            for m in moves
        ],
        'reference_type': 'mocap',
        'mocap_path': mocap_ref_path
    }
