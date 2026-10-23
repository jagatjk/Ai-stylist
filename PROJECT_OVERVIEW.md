# StylistAI: Project Overview

**Faculty presentation report**

**Status reviewed:** 23 October 2026

## 1. Executive summary

StylistAI is a web application for browsing a fashion catalogue, receiving rule-based outfit suggestions, and previewing a selected garment with a virtual try-on model. The interface is a React single-page application. A Python/FastAPI backend serves catalogue data and images, applies recommendation rules, validates try-on uploads, and proxies try-on requests to CatVTON running on a Google Colab GPU.

The project combines two different kinds of logic:

1. **Catalogue recommendations:** a deterministic scoring and outfit-assembly algorithm over product metadata. It is not currently powered by an LLM or by CLIP similarity search.
2. **Virtual try-on:** CatVTON, a pretrained, diffusion-based virtual try-on pipeline. It uses the uploaded person image, catalogue garment image, garment type, and an automatically prepared clothing mask to generate an output image.

The local app-to-Colab path was verified with a real model inference returning a PNG. The test used a catalogue garment image as the uploaded person-image input, so it confirms that the API, model, and image-response path work, but does **not** establish visual quality on a real person's photo. The Colab service and ngrok tunnel are temporary and must remain active during a demo.

## 2. Project goals and user workflow

The application is intended to let a user:

- Browse, search, and filter fashion catalogue items.
- Describe a desired style and optionally select a gender preference.
- Receive outfit suggestions selected from the local catalogue.
- Select a supported garment and upload a JPEG, PNG, or WebP photo.
- Preview the uploaded photo before submitting it for try-on.
- See the generated result or a visible error if a service is unavailable.

The supported virtual try-on garment classes are tops (`upper`), bottoms (`lower`), and full-body garments (`overall`). Shoes and accessories can appear in catalogue recommendations, but they are not supported by the CatVTON try-on endpoint.

## 3. System architecture

```text
Browser (React + Vite, localhost:5173)
  ├── GET /api/products ───────────────┐
  ├── POST /api/recommendations ───────┤
  └── POST /api/try-on/{product_id} ───┤
                                       v
                         StylistAI FastAPI backend
                         (localhost:8001)
                           ├── CSV catalogue and local images
                           ├── rule-based recommender
                           └── authenticated multipart request
                                       |
                                       v
                         ngrok HTTPS tunnel (temporary)
                                       |
                                       v
                         CatVTON API on Colab GPU
                           ├── image checks and resizing
                           ├── automatic garment mask
                           ├── CatVTON diffusion inference
                           └── PNG response
```

The browser does not receive the CatVTON API key. The backend reads the URL and key from its local configuration and forwards them in a bearer authorization header. The browser receives only the generated PNG response.

## 4. Data

### 4.1 Catalogue dataset

The application catalogue is `data/fashion-1000-new/products.csv`, paired with images under `data/fashion-1000-new/images/`.

The verified working catalogue contains **1,000 product rows and 1,000 matching images**. Its CSV fields include:

| Field | Purpose |
|---|---|
| `id` | Product identifier and image filename key |
| `gender` | Product's labelled gender group |
| `masterCategory`, `subCategory` | Broad and specific catalogue grouping |
| `articleType` | Garment or footwear class used for filtering, recommendations, and try-on mapping |
| `baseColour` | Colour metadata used to match a text request |
| `season`, `year`, `usage` | Product context, including use such as Casual or Formal |
| `productDisplayName` | Display/search text |
| `image` | Local `/images/...` path for the product image |

The data-preparation script, `backend/prepare_dataset.py`, reads `data/fashion-dataset/styles.csv`, retains selected apparel and footwear classes only when the corresponding JPG exists, then chooses a reproducible 1,000-item sample using random seed `42`. It copies the selected images and writes the reduced CSV. The script includes apparel, shoes, and selected article types such as shirts, jeans, dresses, and jackets.

The current sample contains **665 Apparel** and **335 Footwear** records. These are pre-labelled catalogue records; the project does not train a classifier to assign those labels.

### 4.2 Additional data artifacts

The data folder also contains `fashion_embeddings.npy` with shape **(1000, 512)** and dtype `float32`, plus `fashion_products_matched.csv` and the original `styles.csv`. The embedding file is an artifact of an earlier semantic-search workflow. It is **not loaded by the current FastAPI recommendation route or current frontend request flow**. Its exact encoder, preprocessing, and evaluation provenance are not recorded in the current app code, so the report does not claim a particular model generated it.

### 4.3 Personal images

The user photo is uploaded for a request and held transiently by the backend and Colab API while that request is processed. The current project code does not save the uploaded person photo as part of the catalogue. Users should still avoid uploading sensitive images to an experimental service unless they are comfortable with that data passing through their own browser, local backend, Colab runtime, and temporary tunnel.

## 5. Recommendation logic: no LLM in the current application

The current recommendation endpoint is `POST /api/recommendations` in `backend/main.py`. It accepts a prompt, an optional gender value, and a result limit.

The implementation is a **transparent metadata-based heuristic**, not a generative AI system:

1. It detects an occasion from a small keyword list: Formal, Casual, Sports, or Ethnic.
2. It detects a requested colour from a fixed list of common colours.
3. It uses the explicit gender selection, or attempts to infer Men/Women from prompt words when none was selected.
4. It scores each product against the request:
   - A matching gender adds 2 points; a non-matching gender excludes that record.
   - A matching requested colour adds 3 points.
   - A matching occasion/use adds 4 points.
   - Prompt words longer than three characters found in product name or article type add 1 point each.
5. It groups products into tops, bottoms, shoes, one-piece garments, and outerwear, ranks each group, and assembles simple outfits according to the detected occasion.
6. It returns product recommendations and outfit groupings as JSON.

**LLM status:** no LLM provider, model, prompt endpoint, or API key is used for recommendations in the current app. The prompt is parsed locally using keyword matching. Therefore, the system does not provide open-ended language understanding, explanation generation, or learned stylist reasoning. Outfit explanations are short templates from code.

## 6. Image classification and computer-vision components

### 6.1 What the app does not do

- It does not currently train or run a standalone image-classification model (for example, a custom CNN, ResNet, or ViT classifier).
- It does not infer product labels from raw catalogue pixels at request time. It relies on existing CSV metadata such as `articleType`, `baseColour`, and `masterCategory`.
- It does not use the 512-dimensional embedding artifact in the active recommendation endpoint.
- It does not currently use CLIP `/search` for the recommendation flow; that earlier Colab route is not the active app integration.

### 6.2 Computer vision used for try-on

CatVTON is the image-generation component, not a product classifier. The Colab API:

- Accepts `person_image`, `cloth_image`, and `cloth_type` multipart fields.
- Uses Pillow to decode images, convert them to RGB, and reject invalid or oversized inputs.
- Uses CatVTON's `AutoMasker` and mask-processing utilities to prepare the garment region mask.
- Resizes/crops the person image and resizes/pads the garment image to the model input size.
- Applies a blurred mask and calls the CatVTON pipeline to synthesize the try-on image.
- Returns the generated result as `image/png`.

The StylistAI backend maps catalogue `articleType` strings to CatVTON's `upper`, `lower`, and `overall` classes. Unknown or unsupported items are rejected rather than silently treated as a supported garment.

## 7. Libraries, frameworks, and tools

### 7.1 Frontend

| Tool | Role |
|---|---|
| React 19 | Component-based user interface and state management |
| Vite 8 | Frontend development server and production bundler |
| `@vitejs/plugin-react` | React integration and development transforms for Vite |
| Oxlint | JavaScript/JSX linting |
| Browser Fetch API | HTTP calls to the backend; `FormData`/blob handling for images |

The project is JavaScript/JSX rather than TypeScript.

### 7.2 Local backend

| Tool | Role |
|---|---|
| Python | Backend runtime |
| FastAPI | HTTP routes, request validation, and API responses |
| Pydantic | Recommendation request model and field validation |
| Starlette | ASGI support and thread-pool helper for blocking upstream calls |
| Python standard library | CSV loading, file paths, MIME detection, multipart encoding, HTTP forwarding, and secrets |

The catalogue is stored in CSV and local image files; the active backend does not require a database for this workflow.

### 7.3 Colab inference service

The prepared Colab environment uses Python 3.11, PyTorch **2.4.0 + CUDA 12.1** and torchvision **0.19.0**, along with the CatVTON repository and pinned/selected supporting libraries including Diffusers **0.30.3**, Accelerate, Transformers, Pillow, FastAPI, Uvicorn, `python-multipart`, and `pyngrok`. The service runs on a Colab GPU runtime and is exposed to the local backend through an ngrok HTTPS tunnel.

`pyngrok` creates the tunnel. The API key protects the inference endpoint with bearer authentication. The setup is a development/demo deployment, not a permanent production hosting arrangement.

### 7.4 Development and verification tools

- VS Code and PowerShell for local development and process configuration.
- npm scripts for frontend linting, development serving, and production builds.
- Python `py_compile` for a backend syntax check.
- `curl`/HTTP checks for backend and Colab health, API responses, and generated-image content type.
- Google Colab for the GPU runtime and model execution.

## 8. API and request/response design

| Route | Method | Purpose |
|---|---|---|
| `/api/health` | GET | Confirms the local FastAPI backend is serving |
| `/api/products` | GET | Loads and filters catalogue products |
| `/api/recommendations` | POST | Returns metadata-ranked products and outfit groupings |
| `/api/try-on/{product_id}` | POST | Accepts a raw JPEG/PNG/WebP person image, resolves the catalogue garment, and proxies inference |
| `/health` on Colab | GET | Confirms the CatVTON service is alive |
| `/try-on` on Colab | POST | Authenticated multipart inference endpoint; returns PNG |

The backend validates supported image content types, caps the uploaded person image at 10 MB, verifies the selected product/image, chooses a garment type, sends the product garment and user photo to Colab, and expects an `image/png` response. Upstream errors are surfaced as HTTP errors instead of being presented as successful image responses.

## 9. Validation performed and current evidence

The following checks were observed during project setup:

- Frontend Oxlint completed successfully.
- Vite production build completed successfully.
- Backend `main.py` compiled successfully with `py_compile`.
- Local recommendation request returned product and outfit data.
- Local API health returned HTTP 200.
- Colab `/health` returned HTTP 200.
- A request through the local try-on route reached CatVTON and returned HTTP 200 with `Content-Type: image/png`; the response had a valid PNG file signature.

**Important scope of the try-on test:** the smoke test supplied a catalogue JPG as the person-image request body because a real test portrait was not available in the project files. It proves end-to-end transport and image generation, but it is not a quality evaluation on a person wearing a garment. Before a faculty demo, run a consented test with a suitable full-body photo and record the actual output and elapsed time.

## 10. Known limitations and responsible-use notes

1. **Temporary compute and tunnel:** Colab runtimes disconnect or reset, and free ngrok URLs are temporary. Restart setup and API cells after a runtime reset. The local backend cannot generate while the Colab service is offline.
2. **Inference latency:** CatVTON performs diffusion inference (configured here for 50 steps) plus image/mask preparation. This is substantially slower than catalogue filtering; latency varies with GPU allocation, cold start, and tunnel conditions.
3. **Limited recommendation understanding:** keyword detection and hand-authored scoring do not understand nuanced or multi-part natural-language constraints. The current system is not an LLM stylist.
4. **No classifier evaluation:** product taxonomy comes from catalogue metadata; there are no reported classification metrics, confusion matrix, or custom trained classifier.
5. **Try-on scope:** footwear/accessories are not supported, and output realism depends on image framing, pose, lighting, mask quality, and garment type.
6. **Demo security:** the CatVTON key belongs only in the backend's local ignored configuration, never frontend source or a public repository. Keep the notebook restricted because the executed cell output includes service configuration. Rotate the API key if notebook outputs or credentials are exposed beyond trusted collaborators.
7. **Not production deployment:** Colab plus ngrok is appropriate for a prototype demonstration, not a reliable production service. Production use needs persistent GPU hosting, HTTPS/domain management, access control, request quotas, monitoring, data-retention rules, and operational cost planning.

## 11. Suggested faculty demonstration

1. Start the local backend and frontend, and confirm `/api/health` responds.
2. Confirm the Colab GPU runtime is connected and Cell 35's API cell is running.
3. Browse a supported garment such as a shirt, trousers, or dress.
4. Upload a consented, appropriately framed person photo and show the preview before generation.
5. Submit one try-on request and display the resulting image.
6. Briefly show an outfit recommendation prompt and explain that it uses deterministic catalogue metadata ranking, not an LLM.
7. Explain the temporary Colab/ngrok dependency and the difference between the current functional smoke test and a formal visual-quality evaluation.

## 12. Short presentation summary

> StylistAI is a React and FastAPI fashion prototype. It uses a 1,000-item image catalogue with structured product metadata. Recommendations are generated by a local, explainable keyword-and-score algorithm; there is no LLM or active image classifier in that feature. Virtual try-on is provided by CatVTON, a pretrained diffusion model running on a Colab GPU. The backend securely proxies person and garment images to the temporary Colab API, which returns a PNG. The integration and PNG response have been smoke-tested, while final visual-quality testing with a real consented person photo remains part of the demo evaluation.
