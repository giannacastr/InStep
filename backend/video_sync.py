"""
Programmatic video auto-sync via audio cross-correlation.
No AI/LLM APIs; deterministic DSP only (librosa, scipy, numpy, ffmpeg-python).
"""

import os
import sys
import tempfile
import subprocess
import json
import uuid

import numpy as np

SAMPLE_RATE = 22050  # Hz, same for both tracks to save memory


def _get_video_duration_seconds(video_path: str) -> float:
    """Get video duration in seconds using ffprobe."""
    try:
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            video_path,
        ]
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            raise RuntimeError(f"ffprobe stderr: {result.stderr}")
        data = json.loads(result.stdout)
        return float(data["format"]["duration"])
    except Exception as e:
        print(
            f"[SYNC ERROR] Could not get duration for {video_path}: {e!r}",
            file=sys.stderr,
        )
        raise


def _extract_wav_from_video(video_path: str, wav_path: str) -> None:
    """
    Step 1 helper: use ffmpeg-python to extract pure .wav audio from a video file.
    FFmpeg outputs mono, 22050 Hz directly to avoid resampy in librosa.
    """
    import ffmpeg

    print(
        f"[SYNC STATUS] FFmpeg extracting audio: video='{video_path}' -> wav='{wav_path}'",
        flush=True,
    )
    stream = ffmpeg.input(video_path)
    # Extract audio only; FFmpeg resamples to mono 22050 Hz (no resampy needed in librosa)
    stream = ffmpeg.output(
        stream.audio,
        wav_path,
        acodec="pcm_s16le",
        ac=1,
        ar=22050,
    )
    ffmpeg.run(stream, overwrite_output=True, capture_stdout=True, capture_stderr=True)
    print(
        f"[SYNC STATUS] FFmpeg extraction complete for '{video_path}'. Wav at '{wav_path}'",
        flush=True,
    )


def _load_audio_from_wav(wav_path: str):
    """
    Step 2 helper: load .wav into librosa. FFmpeg already output mono 22050 Hz,
    so sr=None bypasses resampy entirely (no resampling = no crash).
    Returns (audio_array, sample_rate).
    """
    import librosa

    print(
        f"[SYNC STATUS] Librosa loading wav file for analysis: '{wav_path}'",
        flush=True,
    )
    try:
        # sr=None: read as-is (FFmpeg already resampled). No res_type = no resampy.
        y, sr = librosa.load(wav_path, sr=None, mono=True)
    except Exception as e:
        print(
            f"[SYNC ERROR] Librosa load failed. Reason: {e!r}",
            file=sys.stderr,
        )
        raise
    y = np.ascontiguousarray(y)
    print(
        f"[SYNC STATUS] Librosa loaded '{wav_path}' - sr={sr}, samples={len(y)}",
        flush=True,
    )
    return y, sr


def compute_time_offset_seconds(
    ref_audio: np.ndarray, prac_audio: np.ndarray, sr: int
) -> float:
    """
    Cross-correlate ref vs practice. Return time offset in seconds.
    Positive offset => ref is ahead (ref started first) => pad practice at start.
    Negative offset => practice is ahead => pad reference at start.
    """
    from scipy.signal import fftconvolve

    print(
        f"[SYNC STATUS] Starting cross-correlation. "
        f"ref_samples={len(ref_audio)}, prac_samples={len(prac_audio)}, sr={sr}",
        flush=True,
    )

    # Cross-correlation: correlate(ref, prac) -> lag where prac aligns with ref
    # Use fftconvolve for speed: corr(a,b) = convolve(a, b[::-1])
    prac_reversed = np.ascontiguousarray(prac_audio[::-1])
    corr = fftconvolve(ref_audio, prac_reversed, mode="full")
    if not np.isfinite(corr).all() or corr.size == 0:
        raise ValueError("Cross-correlation produced invalid or empty result")

    max_idx = int(np.argmax(corr))
    # Zero-lag in 'full' mode is at index len(prac_audio)-1
    zero_lag = len(prac_audio) - 1
    lag_samples = max_idx - zero_lag
    offset_seconds = lag_samples / sr

    print(
        "[SYNC STATUS] Cross-correlation raw metrics: "
        f"max_idx={max_idx}, zero_lag={zero_lag}, "
        f"lag_samples={lag_samples}, offset_seconds={offset_seconds:.6f}",
        flush=True,
    )

    return offset_seconds


def run_sync(
    ref_video_path: str,
    prac_video_path: str,
    output_path: str,
) -> dict:
    """
    Align two videos by audio cross-correlation, pad/trim, and stitch side-by-side.
    Returns dict with offset_seconds, synced_path, and any logs.
    """
    import ffmpeg

    ref_path = os.path.abspath(ref_video_path)
    prac_path = os.path.abspath(prac_video_path)
    out_path = os.path.abspath(output_path)
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

    for p in (ref_path, prac_path):
        if not os.path.isfile(p):
            raise FileNotFoundError(f"Video file not found: {p}")

    backend_dir = os.path.dirname(os.path.abspath(__file__))
    tmp_ref_wav = os.path.join(backend_dir, f"_instep_ref_{uuid.uuid4().hex}.wav")
    tmp_prac_wav = os.path.join(backend_dir, f"_instep_prac_{uuid.uuid4().hex}.wav")
    temp_wavs = [tmp_ref_wav, tmp_prac_wav]

    ref_audio = prac_audio = None
    offset_seconds = None

    try:
        # ----- Step 1: Audio Extraction (FFmpeg -> WAV) -----
        print(
            "[SYNC STATUS] Extracting pure .wav audio from video files using FFmpeg...",
            flush=True,
        )
        try:
            _extract_wav_from_video(ref_path, tmp_ref_wav)
            _extract_wav_from_video(prac_path, tmp_prac_wav)
        except Exception as e:
            print(
                f"[SYNC ERROR] Audio extraction via FFmpeg failed. Reason: {e!r}",
                file=sys.stderr,
            )
            raise

        # ----- Step 2: Audio Loading & Normalization (librosa) -----
        print(
            "[SYNC STATUS] Loading .wav files into librosa for analysis...",
            flush=True,
        )
        try:
            ref_audio, sr_ref = _load_audio_from_wav(tmp_ref_wav)
            prac_audio, sr_prac = _load_audio_from_wav(tmp_prac_wav)
        except Exception as e:
            print(
                f"[SYNC ERROR] Librosa audio loading failed. Reason: {e!r}",
                file=sys.stderr,
            )
            raise

        if sr_ref != SAMPLE_RATE or sr_prac != SAMPLE_RATE:
            print(
                "[SYNC STATUS] Warning: sample rate mismatch after librosa load - "
                f"sr_ref={sr_ref}, sr_prac={sr_prac}, expected={SAMPLE_RATE}",
                file=sys.stderr,
            )

        # ----- Step 3: Cross-Correlation Math (scipy & numpy) -----
        # Use actual sr from loaded wavs (FFmpeg outputs 22050)
        sr_used = sr_ref if sr_ref == sr_prac else min(sr_ref, sr_prac)
        try:
            offset_seconds = compute_time_offset_seconds(
                ref_audio, prac_audio, sr_used
            )
        except Exception as e:
            print(
                f"[SYNC ERROR] Cross-correlation failed. Reason: {e!r}",
                file=sys.stderr,
            )
            raise

        if offset_seconds is None or (
            isinstance(offset_seconds, float) and not np.isfinite(offset_seconds)
        ):
            print(
                "[SYNC ERROR] Computed time offset is null or non-finite.",
                file=sys.stderr,
            )
            raise ValueError("Null or non-finite time offset from cross-correlation")

        # Padding: offset > 0 => ref started first => pad practice. offset < 0 => pad ref.
        pad_ref_seconds = max(0.0, -offset_seconds)
        pad_prac_seconds = max(0.0, offset_seconds)

        print(
            f"[SYNC STATUS] Calculated offset: {offset_seconds:.3f} seconds. "
            f"Padding Reference by {pad_ref_seconds:.3f} seconds and "
            f"Practice by {pad_prac_seconds:.3f} seconds.",
            flush=True,
        )
        ahead = (
            "Video A (reference) is ahead of Video B (practice)."
            if offset_seconds > 0
            else "Video B (practice) is ahead of Video A (reference)."
        )
        print(
            f"[SYNC SUCCESS] Cross-correlation complete. Offset calculated: "
            f"{offset_seconds:.2f} seconds. {ahead}",
            flush=True,
        )

        # ----- Step 4: Video Padding & Stitching (ffmpeg-python) -----
        print(
            "[FFMPEG STATUS] Padding videos with black frames and stitching side-by-side...",
            flush=True,
        )
        try:
            ref_dur = _get_video_duration_seconds(ref_path)
            prac_dur = _get_video_duration_seconds(prac_path)
            print(
                f"[SYNC STATUS] Video durations (seconds): ref={ref_dur:.3f}, prac={prac_dur:.3f}",
                flush=True,
            )
        except Exception as e:
            print(
                f"[FFMPEG ERROR] Could not get video durations. Reason: {e!r}",
                file=sys.stderr,
            )
            raise

        # Which video starts first? (pad_ref_seconds, pad_prac_seconds already set above)

        # After padding, durations are:
        # ref_effective = ref_dur + pad_ref_seconds, prac_effective = prac_dur + pad_prac_seconds
        ref_effective = ref_dur + pad_ref_seconds
        prac_effective = prac_dur + pad_prac_seconds
        target_duration = min(ref_effective, prac_effective)

        print(
            "[SYNC STATUS] Padding/trim plan: "
            f"pad_ref_seconds={pad_ref_seconds:.3f}, pad_prac_seconds={pad_prac_seconds:.3f}, "
            f"ref_effective={ref_effective:.3f}, prac_effective={prac_effective:.3f}, "
            f"target_duration={target_duration:.3f}",
            flush=True,
        )

        with tempfile.TemporaryDirectory(prefix="instep_sync_") as tmp:
            ref_padded = os.path.join(tmp, "ref_padded.mp4")
            prac_padded = os.path.join(tmp, "prac_padded.mp4")

            def pad_and_trim(input_path, output_path, pad_seconds, final_duration):
                """Pad with black at start (tpad + adelay), then trim to final_duration."""
                inp = ffmpeg.input(input_path)
                if pad_seconds > 0:
                    # tpad adds black frames at start; adelay adds silence at start (ms)
                    pad_ms = int(pad_seconds * 1000)
                    print(
                        f"[SYNC STATUS] Applying tpad/adelay: input='{input_path}', "
                        f"pad_seconds={pad_seconds:.3f}, pad_ms={pad_ms}",
                        flush=True,
                    )
                    v = inp.video.filter(
                        "tpad",
                        start_mode="add",
                        start_duration=pad_seconds,
                    )
                    a = inp.audio.filter("adelay", f"{pad_ms}|{pad_ms}")
                    stream = ffmpeg.output(v, a, output_path, t=final_duration)
                else:
                    print(
                        f"[SYNC STATUS] No start padding needed for '{input_path}'. "
                        f"Trimming to {final_duration:.3f} seconds.",
                        flush=True,
                    )
                    stream = ffmpeg.output(
                        inp.video, inp.audio, output_path, t=final_duration
                    )
                ffmpeg.run(
                    stream,
                    overwrite_output=True,
                    capture_stdout=True,
                    capture_stderr=True,
                )
                print(
                    f"[SYNC STATUS] Pad/trim complete for '{input_path}'. "
                    f"Output='{output_path}'",
                    flush=True,
                )

            try:
                pad_and_trim(ref_path, ref_padded, pad_ref_seconds, target_duration)
                pad_and_trim(prac_path, prac_padded, pad_prac_seconds, target_duration)
            except Exception as e:
                print(
                    f"[FFMPEG ERROR] FFmpeg pad/trim failed. Reason: {e!r}",
                    file=sys.stderr,
                )
                raise

            # Stitch side-by-side (use reference audio for output)
            try:
                print(
                    f"[SYNC STATUS] HStack stitching files: ref='{ref_padded}', prac='{prac_padded}'",
                    flush=True,
                )
                v1 = ffmpeg.input(ref_padded)
                v2 = ffmpeg.input(prac_padded)
                joined = ffmpeg.filter([v1.video, v2.video], "hstack", inputs=2)
                out = ffmpeg.output(joined, v1.audio, out_path, shortest=1)
                ffmpeg.run(
                    out,
                    overwrite_output=True,
                    capture_stdout=True,
                    capture_stderr=True,
                )
            except Exception as e:
                print(
                    f"[FFMPEG ERROR] FFmpeg stitch failed. Reason: {e!r}",
                    file=sys.stderr,
                )
                raise

        print(
            "[FFMPEG SUCCESS] Final synced video successfully generated.",
            flush=True,
        )

        return {
            "offset_seconds": offset_seconds,
            "synced_path": out_path,
            "ref_duration": ref_dur,
            "prac_duration": prac_dur,
            "target_duration": target_duration,
        }
    finally:
        # Step 5: Clean up temporary wav files
        print(
            "[SYNC STATUS] Cleaning up temporary .wav audio files...",
            flush=True,
        )
        for wav_path in temp_wavs:
            try:
                if os.path.exists(wav_path):
                    os.remove(wav_path)
                    print(
                        f"[SYNC STATUS] Deleted temp wav file: '{wav_path}'",
                        flush=True,
                    )
            except Exception as e:
                print(
                    f"[SYNC ERROR] Failed to delete temp wav file '{wav_path}': {e!r}",
                    file=sys.stderr,
                )
