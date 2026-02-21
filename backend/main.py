import os
import shutil
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

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
        "ref_path": ref_path,
        "prac_path": prac_path
    }