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

## Command Quick Reference (Test)

| Command | Run from folder |
|--------|------------------|
| `pip install -r requirements.txt`, `uvicorn main:app --reload --host 127.0.0.1 --port 8000` | `backend/` |
| `npm install`, `npm run dev` | `frontend/` |

---

## Optional: Vision Analysis (Pose Detection)

For move-by-move pose detection (not required for basic audio sync):

1. Download the **Pose Landmarker (Lite)** model from https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker
2. Save it as `/tmp/pose_landmarker.task` (or the path configured in `vision_engine.py`)

Without this model, the app will show demo analysis data.

---

## Usage

1. Open the app in your browser.
2. Upload a **Reference Video** (the dance you want to match).
3. Upload **Your Practice** video.
4. Click **Analyze Move-by-Move**.
5. Review the results (analysis coming soon).

---

## Project Structure

```
InStep/
├── backend/
│   ├── main.py           # FastAPI app, upload endpoints
│   ├── requirements.txt
│   └── uploads/          # Saved videos (gitignored)
│       ├── reference/
│       └── practice/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── screens/
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

---

## Tech Stack

- **Backend:** Python, FastAPI, Uvicorn
- **Frontend:** React 19, Vite, React Router
