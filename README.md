# StylistAI

StylistAI is a fashion catalogue and virtual try-on prototype. The React frontend uses a FastAPI backend for product search, rule-based outfit recommendations, and requests to CatVTON running on a Google Colab GPU.

For the faculty-facing architecture, data details, algorithms, dependencies, validation scope, and limitations, see [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md).

The Colab setup and authenticated CatVTON API cells are documented in [notebooks/catvton_colab.ipynb](notebooks/catvton_colab.ipynb). This is a clean, output-free project notebook; the live GPU runtime and ngrok URL/key are temporary and must not be committed.

## Requirements

- Git and Git LFS
- Python 3.11 or newer
- Node.js 20.19 or newer and npm
- A connected Google Colab GPU runtime with the CatVTON API notebook running for virtual try-on

The prepared product catalogue contains 1,000 images stored with Git LFS. Install Git LFS and fetch the images after cloning:

```powershell
git lfs install
git lfs pull
```

## Start the backend

From the project root in PowerShell:

```powershell
py -3.11 -m venv backend\.venv
backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

Create `backend\.env` locally with the current Colab service details. Do not commit this file:

```text
CATVTON_API_URL=https://your-current-colab-tunnel.ngrok-free.dev
CATVTON_API_KEY=your-generated-api-key
```

The URL and key are printed by the API cell in the restricted CatVTON Colab notebook. Both change when the Colab runtime or API session is restarted.

Start the backend from the project root:

```powershell
backend\.venv\Scripts\python.exe -m uvicorn main:app --app-dir backend --host 127.0.0.1 --port 8001
```

Check that it is responding:

```powershell
curl.exe http://127.0.0.1:8001/api/health
```

## Start the frontend

In a second PowerShell terminal:

```powershell
Set-Location frontend
npm ci
npm run dev -- --host 127.0.0.1 --port 5173
```

Open <http://localhost:5173>.

## Try-on requirements

Keep the Colab GPU runtime connected and the authenticated API cell running while using try-on. Upload a consented JPEG, PNG, or WebP person photo (10 MB maximum) and select a supported top, bottom, or full-body garment. Footwear and accessories can be browsed but cannot be sent to CatVTON.

Colab and its ngrok tunnel are temporary demo infrastructure. A runtime reset requires rerunning the notebook setup and API cells, then updating `backend\.env` with the newly printed values and restarting the backend.

## Data and Git LFS

The app catalogue metadata is in `data/fashion-1000-new/products.csv`; its matching JPEGs are under `data/fashion-1000-new/images/` and are tracked with Git LFS. The original dataset, compressed archives, and unused embedding artifacts are excluded from this repository. The prepared image set is distributed under the repository owner's confirmed redistribution permission.

## Current AI scope

- Product suggestions use deterministic keyword matching and metadata scoring; no LLM is currently connected.
- Product categories are read from the supplied catalogue metadata; the app does not train a separate image classifier.
- CatVTON provides virtual try-on image generation through the Colab GPU service.
