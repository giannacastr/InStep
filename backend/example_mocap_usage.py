"""
Example usage of the Motion Capture Reference System

This demonstrates how to:
1. Load mocap data from various formats
2. Convert to DataFrame for analysis
3. Use mocap reference for video analysis
"""
import os
import json
import numpy as np
from mocap_loader import load_mocap_data, mocap_to_dataframe, dataframe_to_poses
from mocap_reference import analyze_with_mocap_reference, MocapReference


def create_sample_cmu_json(output_path: str, duration_seconds: float = 5.0, fps: float = 30.0):
    """
    Create a sample CMU-format JSON file for testing.
    Simulates a simple dance move (arm raise).
    """
    frames = []
    num_frames = int(duration_seconds * fps)
    
    for i in range(num_frames):
        t = i / fps
        # Simple animation: arms raise up over time
        arm_height = 0.3 + 0.4 * (i / num_frames)  # Raise from 0.3 to 0.7
        
        frame = {
            "time": t,
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
                "LeftArm": [-0.3, arm_height, 0.0],
                "LeftForeArm": [-0.4, arm_height + 0.2, 0.0],
                "RightShoulder": [0.2, 1.5, 0.0],
                "RightArm": [0.3, arm_height, 0.0],
                "RightForeArm": [0.4, arm_height + 0.2, 0.0]
            }
        }
        frames.append(frame)
    
    data = {"frames": frames}
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"Created sample CMU JSON file: {output_path}")
    print(f"  Duration: {duration_seconds}s")
    print(f"  Frames: {num_frames}")
    print(f"  FPS: {fps}")


def example_load_and_analyze():
    """Example: Load mocap data and analyze with practice video."""
    
    # Step 1: Create sample mocap file (or use existing)
    sample_mocap = "sample_dance_move.json"
    if not os.path.exists(sample_mocap):
        create_sample_cmu_json(sample_mocap, duration_seconds=5.0, fps=30.0)
    
    # Step 2: Load mocap data
    print("\n=== Loading Mocap Data ===")
    poses = load_mocap_data(sample_mocap, format_type="cmu", fps=30.0)
    print(f"Loaded {len(poses)} poses")
    print(f"Duration: {poses[-1]['timestamp']:.2f} seconds")
    print(f"First pose landmarks shape: {poses[0]['landmarks'].shape}")
    
    # Step 3: Convert to DataFrame for analysis
    print("\n=== Converting to DataFrame ===")
    df = mocap_to_dataframe(poses)
    print(f"DataFrame shape: {df.shape}")
    print(f"Columns: {list(df.columns[:5])}...")
    print(f"\nStatistics:")
    print(df[['timestamp', 'confidence']].describe())
    
    # Step 4: Use mocap as reference (if practice video exists)
    prac_video = "uploads/practice/user_video.mp4"
    if os.path.exists(prac_video):
        print("\n=== Analyzing with Mocap Reference ===")
        result = analyze_with_mocap_reference(
            mocap_ref_path=sample_mocap,
            prac_video_path=prac_video,
            offset=0.0,
            mocap_format="cmu",
            mocap_fps=30.0
        )
        
        print(f"Overall Score: {result['overallScore']}%")
        print(f"Number of moves: {len(result['moves'])}")
        for move in result['moves'][:3]:  # Show first 3 moves
            print(f"  {move['timestamp']}: {move['status']} - {move['feedback']}")
    else:
        print(f"\nPractice video not found: {prac_video}")
        print("Skipping analysis step")


def example_mocap_reference_class():
    """Example: Using MocapReference class directly."""
    
    sample_mocap = "sample_dance_move.json"
    if not os.path.exists(sample_mocap):
        create_sample_cmu_json(sample_mocap)
    
    print("\n=== Using MocapReference Class ===")
    mocap_ref = MocapReference(sample_mocap, format_type="cmu", fps=30.0)
    
    print(f"Duration: {mocap_ref.get_duration():.2f}s")
    print(f"Number of poses: {len(mocap_ref.get_poses())}")
    
    # Sample at specific time
    pose_at_2s = mocap_ref.sample_at_time(2.0, tolerance=0.1)
    if pose_at_2s:
        print(f"\nPose at 2.0s:")
        print(f"  Timestamp: {pose_at_2s['timestamp']:.3f}")
        print(f"  Confidence: {pose_at_2s['confidence']}")
        print(f"  Left shoulder position: {pose_at_2s['landmarks'][11]}")


if __name__ == "__main__":
    print("Motion Capture Reference System - Examples")
    print("=" * 50)
    
    # Run examples
    example_load_and_analyze()
    example_mocap_reference_class()
    
    print("\n" + "=" * 50)
    print("Examples complete!")
    print("\nNext steps:")
    print("1. Download real mocap data from CMU or AIST++")
    print("2. Convert to JSON format if needed")
    print("3. Use /analyze-mocap API endpoint with your practice videos")
