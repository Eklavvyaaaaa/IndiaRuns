# RedRob Candidate Intelligence Engine - Frontend

This is the React + Vite frontend for the RedRob Candidate Intelligence Engine. It provides a Dashboard for pasting a Job Description and a Rankings page to view the evaluated candidates with their organic reasoning bullets.

## Setup Instructions

1. **Install dependencies**
   Ensure you have Node.js installed, then run:
   ```bash
   npm install
   ```

2. **Configure Environment Variables**
   By default, the frontend connects to the backend at `http://localhost:8000/api/v1`. If your backend is hosted elsewhere, create a `.env` file in this `frontend/` directory and set the base URL:
   ```env
   VITE_API_URL=http://your-backend-url:8000/api/v1
   ```

3. **Start the Development Server**
   ```bash
   npm run dev
   ```
   The UI will be available at `http://localhost:5173`.

## Connecting to the Backend

The frontend requires the FastAPI backend to be running.
To start the backend from the project root:
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --app-dir backend
```

Ensure you have run `python backend/precompute.py` at least once so the backend has the necessary FAISS and Parquet artifacts to serve requests.
