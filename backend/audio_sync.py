"""
Audio-based video synchronization.
Extracts audio from both videos, finds the time offset that aligns them by cross-correlation,
and returns timing info for black-padding when one video starts/ends before the other.
"""
import os
import subprocess
import tempfile
import numpy as np
import librosa
from scipy import signal

SAMPLE_RATE = 22050
HOP_LENGTH = 512


def extract_audio_wav(video_path: str) -> str | None:
    """
    Extract audio from video to a temp WAV file using ffmpeg.
    Returns path to temp file, or None if ffmpeg fails.
    """
    abs_path = os.path.abspath(video_path)
    if not os.path.isfile(abs_path):
        return None
    fd, wav_path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    try:
        subprocess.run(
            [
                "ffmpeg", "-y", "-i", abs_path,
                "-vn", "-acodec", "pcm_s16le",
                "-ar", str(SAMPLE_RATE), "-ac", "1",
                wav_path,
            ],
            capture_output=True,
            check=True,
            timeout=60,
        )
        return wav_path
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        if os.path.exists(wav_path):
            os.unlink(wav_path)
        return None


def compute_sync_offset(ref_video_path: str, prac_video_path: str) -> dict:
    """
    Compute the time offset that aligns practice video with reference video.
    Uses chroma features and cross-correlation.

    Returns:
        dict with:
            - offset: seconds to ADD to practice time to get reference time.
                      prac_display_time = ref_time - offset
                      If offset > 0: practice "starts" offset seconds into ref timeline (black for prac at start)
            - ref_duration: duration of reference video in seconds
            - prac_duration: duration of practice video in seconds
            - success: bool - whether sync was computed (False if ffmpeg/libs fail)
            - error: optional error message
    """
    ref_wav = None
    prac_wav = None
    result = {
        "offset": 0.0,
        "ref_duration": 0.0,
        "prac_duration": 0.0,
        "success": False,
        "error": None,
    }

    try:
        ref_wav = extract_audio_wav(ref_video_path)
        prac_wav = extract_audio_wav(prac_video_path)
        if not ref_wav or not prac_wav:
            result["error"] = "Could not extract audio (ffmpeg required)"
            return result

        y_ref, sr = librosa.load(ref_wav, sr=SAMPLE_RATE, mono=True)
        y_prac, _ = librosa.load(prac_wav, sr=sr, mono=True)

        result["ref_duration"] = len(y_ref) / sr
        result["prac_duration"] = len(y_prac) / sr

        # Use chroma - robust to volume, good for music
        chroma_ref = librosa.feature.chroma_stft(y=y_ref, sr=sr, hop_length=HOP_LENGTH)
        chroma_prac = librosa.feature.chroma_stft(y=y_prac, sr=sr, hop_length=HOP_LENGTH)

        # Collapse to 1D per frame (mean across pitch classes)
        ref_frames = np.mean(chroma_ref, axis=0)
        prac_frames = np.mean(chroma_prac, axis=0)

        if len(ref_frames) < 10 or len(prac_frames) < 10:
            result["error"] = "Audio too short for sync"
            return result

        # Cross-correlate: find lag where practice aligns with reference
        corr = signal.correlate(ref_frames, prac_frames, mode="full")
        lags = signal.correlation_lags(len(ref_frames), len(prac_frames), mode="full")
        lag_frames = lags[np.argmax(corr)]

        # Convert frames to seconds (each frame = HOP_LENGTH/sr seconds)
        frame_duration = HOP_LENGTH / sr
        offset_sec = lag_frames * frame_duration

        result["offset"] = float(offset_sec)
        result["success"] = True

    except Exception as e:
        result["error"] = str(e)
    finally:
        if ref_wav and os.path.exists(ref_wav):
            os.unlink(ref_wav)
        if prac_wav and os.path.exists(prac_wav):
            os.unlink(prac_wav)

    return result
