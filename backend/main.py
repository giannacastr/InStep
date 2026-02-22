import os
import shutil
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from audio_sync import compute_sync_offset
from vision_engine import analyze_videos
from mocap_reference import analyze_with_mocap_reference

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup folders for the two different video types
UPLOAD_DIR = "uploads"
REF_DIR = os.path.join(UPLOAD_DIR, "reference")
PRAC_DIR = os.path.join(UPLOAD_DIR, "practice")

for folder in [REF_DIR, PRAC_DIR]:
    if not os.path.exists(folder):
        os.makedirs(folder)

# Serve uploaded videos so the frontend can play them
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

@app.get("/")
def read_root():
    return {"InStep": "System Online"}

@app.post("/upload-comparison")
async def upload_comparison(ref_file: UploadFile = File(...), prac_file: UploadFile = File(...)):
    # Save Reference
    ref_path = os.path.join(REF_DIR, ref_file.filename)
    with open(ref_path, "wb") as buffer:
        shutil.copyfileobj(ref_file.file, buffer)
        
    # Save Practice
    prac_path = os.path.join(PRAC_DIR, prac_file.filename)
    with open(prac_path, "wb") as buffer:
        shutil.copyfileobj(prac_file.file, buffer)
    
    return {
        "status": "Success",
        "message": "Both videos received for InStep analysis!",
        "ref_path": ref_path.replace("\\", "/"),
        "prac_path": prac_path.replace("\\", "/"),
    }


class ComputeSyncRequest(BaseModel):
    ref_path: str
    prac_path: str


@app.post("/compute-sync")
async def compute_sync(body: ComputeSyncRequest):
    """
    Compute audio-based sync offset between reference and practice videos.
    Requires ffmpeg to be installed on the system.
    """
    base = os.path.abspath(UPLOAD_DIR)
    ref_abs = os.path.abspath(body.ref_path)
    prac_abs = os.path.abspath(body.prac_path)
    if not ref_abs.startswith(base) or not prac_abs.startswith(base):
        return {"success": False, "error": "Invalid paths"}
    result = compute_sync_offset(ref_abs, prac_abs)
    return result


class ClearUploadsRequest(BaseModel):
    ref_path: str | None = None
    prac_path: str | None = None


@app.post("/clear-uploads")
async def clear_uploads(body: ClearUploadsRequest):
    """Delete the uploaded videos from reference and practice folders."""
    base = os.path.abspath(UPLOAD_DIR)
    deleted = []
    for path in [body.ref_path, body.prac_path]:
        if path:
            abs_path = os.path.abspath(path)
            if abs_path.startswith(base) and os.path.isfile(abs_path):
                os.remove(abs_path)
                deleted.append(path)
    return {"status": "Success", "message": "Videos cleared.", "deleted": deleted}


class AnalyzeRequest(BaseModel):
    ref_path: str
    prac_path: str
    offset: float = 0.0


@app.post("/analyze")
async def analyze(body: AnalyzeRequest):
    """
    Analyze reference and practice videos to detect moves and provide feedback.
    Uses MediaPipe Pose to extract keypoints and compare movements.
    """
    base = os.path.abspath(UPLOAD_DIR)
    ref_abs = os.path.abspath(body.ref_path)
    prac_abs = os.path.abspath(body.prac_path)
    
    if not ref_abs.startswith(base) or not prac_abs.startswith(base):
        return {"success": False, "error": "Invalid paths"}
    
    result = analyze_videos(ref_abs, prac_abs, body.offset)
    return result


class AnalyzeMocapRequest(BaseModel):
    mocap_ref_path: str  # Path to motion capture reference file
    prac_path: str
    offset: float = 0.0
    mocap_format: str | None = None  # Optional: 'cmu', 'aist', 'mixamo', etc.
    mocap_fps: float = 30.0


@app.post("/analyze-mocap")
async def analyze_mocap(body: AnalyzeMocapRequest):
    """
    Analyze practice video against motion capture reference data.
    
    This uses pre-recorded motion capture data (from Mixamo, CMU, AIST++, etc.)
    as the reference instead of extracting poses from a video. This provides
    pristine, high-quality reference data for more accurate grading.
    
    Supported formats:
    - CMU Graphics Lab Motion Capture Database (JSON)
    - AIST++ Dance Motion Dataset (JSON)
    - Cloud API outputs (DeepMotion, Move AI, RADiCAL JSON)
    """
    base = os.path.abspath(UPLOAD_DIR)
    prac_abs = os.path.abspath(body.prac_path)
    
    # Mocap files can be outside uploads directory
    mocap_abs = os.path.abspath(body.mocap_ref_path)
    
    if not prac_abs.startswith(base):
        return {"success": False, "error": "Invalid practice video path"}
    
    if not os.path.exists(mocap_abs):
        return {"success": False, "error": f"Motion capture file not found: {body.mocap_ref_path}"}
    
    try:
        result = analyze_with_mocap_reference(
            mocap_abs,
            prac_abs,
            offset=body.offset,
            mocap_format=body.mocap_format,
            mocap_fps=body.mocap_fps
        )
        return result
    except Exception as e:
        return {"success": False, "error": f"Failed to analyze with mocap reference: {str(e)}"}