# InStep

Compare your dance moves to a reference video. Upload a reference video and your practice video to get a move-by-move analysis of where your style differs and how to improve.

---

## Prerequisites

Before you begin, make sure you have these installed:

| Requirement | Version | Check with |
|-------------|---------|------------|
| **Python** | 3.9+ | `python --version` or `python3 --version` |
| **Node.js** | 18+ | `node --version` |
| **npm** | (included with Node.js) | `npm --version` |
| **ffmpeg** | (for audio sync) | `ffmpeg -version` |

### Installing ffmpeg

- **Mac:** `brew install ffmpeg`
- **Windows:** Download from https://ffmpeg.org/download.html or use `winget install ffmpeg`
- **Linux:** `sudo apt install ffmpeg` (Ubuntu/Debian) or `sudo yum install ffmpeg` (Fedora)

---

## Quick Start

### 1. Backend (FastAPI)

```bash
cd backend
python -m venv venv
```

Activate the virtual environment:
- **Mac/Linux:** `source venv/bin/activate`
- **Windows:** `.\venv\Scripts\activate`

```bash
pip install -r requirements.txt
```

Download the MediaPipe pose detection model (required — do this once):

**Mac/Linux:**
```bash
curl -L "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_heavy/float16/latest/pose_landmarker_heavy.task" -o /tmp/pose_landmarker.task
```

**Windows (PowerShell):**
```powershell
Invoke-WebRequest -Uri "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_heavy/float16/latest/pose_landmarker_heavy.task" -OutFile "$env:TEMP\pose_landmarker.task"
```

> **Windows note:** `vision_engine.py` uses `/tmp/pose_landmarker.task` by default. On Windows, update `MODEL_PATH` in `vision_engine.py` to:
> ```python
> MODEL_PATH = os.path.join(os.environ.get('TEMP', '/tmp'), 'pose_landmarker.task')
> ```

Then start the backend:

```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

The backend runs at `http://127.0.0.1:8000`.

---

### 2. Frontend (React + Vite)

Open a **new terminal** and run:

```bash
cd frontend
npm install
npm run dev
```

The frontend runs at `http://localhost:5173` (or the port Vite shows).

---

## Command Quick Reference

| Step | Command | Run from |
|------|---------|----------|
| Install backend deps | `pip install -r requirements.txt` | `backend/` |
| Download model (Mac/Linux) | `curl -L "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_heavy/float16/latest/pose_landmarker_heavy.task" -o /tmp/pose_landmarker.task` | anywhere |
| Start backend | `uvicorn main:app --reload --host 127.0.0.1 --port 8000` | `backend/` |
| Install frontend deps | `npm install` | `frontend/` |
| Start frontend | `npm run dev` | `frontend/` |

---

## Usage

1. Open the app in your browser.
2. Upload a **Reference Video** (the dance you want to match).
3. Upload **Your Practice** video.
4. Click **Analyze Move-by-Move**.
5. Review the move-by-move breakdown, color-coded feedback, and score.

---

## Project Structure

```
InStep/
├── backend/
│   ├── main.py           # FastAPI app, upload & analysis endpoints
│   ├── vision_engine.py  # MediaPipe pose detection & grading logic
│   ├── audio_sync.py     # Audio-based video sync
│   ├── requirements.txt
│   └── uploads/          # Saved videos (gitignored)
│       ├── reference/
│       └── practice/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── screens/
│   │   ├── data/
│   │   ├── App.jsx
│   │   └── main.jsx
│   └── package.json
└── README.md
```

---

## Contributing

1. Clone the repo and follow the setup steps above.
2. Backend changes: add new packages to `requirements.txt` with pinned versions, e.g. `packagename==1.2.3`.
3. Use `pip install -r requirements.txt` for a clean install.
4. Don't commit `venv/`, `node_modules/`, or `.env` files.
5. Large video files in `backend/uploads/` are gitignored.
6. The MediaPipe model at `/tmp/pose_landmarker.task` is not committed — each machine must download it manually using the steps above.

---

## Tech Stack

- **Backend:** Python, FastAPI, Uvicorn, MediaPipe, OpenCV
- **Frontend:** React 19, Vite, React Router