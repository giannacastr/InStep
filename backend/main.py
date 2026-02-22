import os
import shutil
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

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