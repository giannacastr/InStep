# InStep

Welcome to InStep! This project combines a Python-based computer vision backend with a React frontend. This guide will help you set up your local development environment correctly.

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js & npm (Recommended version: Latest LTS)

---

## Backend Setup (Python)

The backend handles the vision engine using MediaPipe and other data processing tools.

1. Navigate to the backend folder:
```bash
cd backend
```

2. Create a virtual environment:
```bash
python3 -m venv venv
```

3. Activate the virtual environment:
   - Mac/Linux: `source venv/bin/activate`
   - Windows: `.\venv\Scripts\activate`

4. Install dependencies:
```bash
pip install -r requirements.txt
```

5. **Environment Variables:** Create a `.env` file in the `backend/` directory. Do not commit this file. Add any necessary API keys or local configurations here.

---

## Frontend Setup (React + Vite)

The frontend is built with React and Vite for a fast development experience.

1. Navigate to the frontend folder:
```bash
cd frontend
```

2. Install packages:
```bash
npm install
```

3. Run the development server:
```bash
npm run dev
```

---

## Development Guidelines

### Git Workflow & Safety

To avoid the issues we've seen in previous projects like Hope for Haiti, please follow these rules:

- **Never push `venv/` or `node_modules/`:** These are ignored by the root `.gitignore`. If you install a new Python package, update the requirements file using `pip freeze > backend/requirements.txt`.
- **Large Files:** Be mindful of large binaries (over 50MB). If you need to include large models, let the team know so we can use Git LFS.
- **Secrets:** Never commit `.env` files. Ensure they are listed in the `.gitignore`.

---

## Project Structure
```
InStep/
├── backend/            # Python logic & vision_engine.py
│   ├── requirements.txt
│   └── .env            # (Local only)
├── frontend/           # React + Vite source code
│   ├── src/
│   └── package.json
└── .gitignore          # Root-level protection
```