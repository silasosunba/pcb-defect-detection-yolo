# PCB Detect — PCB defect detection with YOLO and Neon

A React + TypeScript application backed by FastAPI and Neon PostgreSQL, with user accounts, role-based administration, private inspection history, and a Kaggle notebook for fine-tuning a PCB detection model.

The original `gripregression.ipynb` and `student_scores data.csv` are retained as legacy files, unrelated to the PCB application.

## Features

- Registration and sign-in with Argon2 password hashing, expiring server-side sessions, HttpOnly cookies, request-origin checks and authentication throttling.
- A navy, cyan and purple landing page, split sign-in screen, analysis workspace, personal dashboard and administration.
- Upload JPG, PNG, TIFF or WebP images (20 MB / 20 MP), or load a browser-accessible image URL. Adjust confidence, review labeled bounding boxes and compare original/annotated images. Export images and JSON.
- Transparent class-based review priorities, explanations and repair guidance for each detection. These are not a trained severity classifier or Grad-CAM.
- Private inspection history. Users see their own images; administrators can review workspace inspections.
- Admin dashboard with user counts, inspection totals, predicted defect counts, activity log, user search, role changes and account disabling. Access changes revoke sessions.
- Server-side YOLO inference with checksum and class-order verification against the training export manifest.

**Training has not been run in this repository.** The application starts without a model and displays “Awaiting model”. Inspection becomes available after installing the inference extra and adding your Kaggle artifacts. No invented predictions or accuracy figures are shown.

## Run locally

Install [uv](https://docs.astral.sh/uv/) and Node.js 22.12+ or Node 24 LTS. Run from the repository root:

```bash
uv sync
cd frontend
npm ci
cd ..
```

### Connect Neon

Create a project in the [Neon Console](https://console.neon.tech/), then choose **Connect**, your database and role, and the **pooled** PostgreSQL connection string. Copy `.env.example` to `.env` if it does not already exist, and replace `DATABASE_URL` with the actual connection string. Keep its TLS options (`sslmode=require`, and `channel_binding=require` when provided).

```dotenv
DATABASE_URL=postgresql://USER:PASSWORD@YOUR-ENDPOINT-pooler.REGION.aws.neon.tech/neondb?sslmode=require&channel_binding=require
```

This value is a server secret. Do not put it in a `VITE_` variable, commit it or post it in chat. The application requires PostgreSQL; it has no embedded database fallback.

Verify the connection and apply the tracked migrations:

```bash
uv run python -m backend.manage check-db
uv run python -m backend.manage migrate
```

Create an administrator. The password is entered interactively, never on the command line. Web registration always creates a normal user.

```bash
uv run python -m backend.manage create-admin --email you@example.com --name "Your Name"
```

Start the backend in one terminal:

```bash
uv run uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Start React in another:

```bash
cd frontend
npm run dev
```

Open **http://127.0.0.1:5173**. Public pages include `/`, `/analyze`, `/guide` and `/privacy`; accounts unlock `/dashboard`, `/history` and `/model`. Administrators also receive `/admin`. API documentation: http://127.0.0.1:8000/api/docs. Vite proxies `/api` to FastAPI.

To serve both on one port, run `npm run build` inside `frontend/`, then start FastAPI from the root and open http://127.0.0.1:8000. Build before starting the API.

## Train in Kaggle

Upload **[notebooks/pcb_yolo_kaggle.ipynb](notebooks/pcb_yolo_kaggle.ipynb)** to Kaggle. It is standalone; repository imports are not required.

1. Add [akhatova/pcb-defects](https://www.kaggle.com/datasets/akhatova/pcb-defects) through **Add Input**.
2. Enable a GPU and Internet. Keep Kaggle's CUDA-enabled PyTorch installation.
3. Inspect mounted paths and adjust `DATA_ROOT` if needed. Default: `/kaggle/input/pcb-defects`.
4. Run validation/conversion. Review board groups, class counts and label previews before training.
5. Run fine-tuning, validation, final test evaluation and export. Defaults: pretrained YOLO11s, 1024 px, batch 4, up to 100 epochs, early stopping. Reduce batch size for GPU memory limits.
6. Save a notebook version with outputs and download `/kaggle/working/pcb-export/`.

The notebook and inference extra both pin **Ultralytics 8.3.253**. Exports include measured metrics, split provenance, configuration, curves and environment versions. GPU training was not executed locally.

### Bounding boxes and exported predictions

The notebook trains **object detection**, not image classification. It converts annotations to YOLO boxes, previews ground-truth labels and, after training, draws predicted boxes on held-out images. `/kaggle/working/pcb-export/predictions/` contains annotated images and `predictions.json` with labels, confidence scores and `[x1, y1, x2, y2]` pixel coordinates. The application uses the same coordinates to draw numbered boxes.

### Load your weights

```bash
uv sync --extra inference
```

Copy these files from the same Kaggle run into the repository:

```text
models/
  best.pt
  model-manifest.json
```

Restart FastAPI. The Detection model page reports availability. On first inspection, the API verifies the checksum and exact class order, then loads YOLO. Correct verification failures and restart before retrying. Only load trusted checkpoints: `.pt` files may contain executable Python objects.

Use `PCB_IMAGE_SIZE=1024` to match the notebook. `PCB_DEVICE=cpu` works without a GPU; `mps` can use a supported Mac GPU and `0` selects CUDA on a configured host. Inference runs in Python; React displays results.

### Datasets and split protocol

PKU class order: `missing_hole`, `mouse_bite`, `open_circuit`, `short`, `spur`, `spurious_copper`.

For original [DeepPCB](https://github.com/tangsanli5201/DeepPCB), set `DATASET_KIND="deeppcb"` and point `DATA_ROOT` above extracted `group*` directories. The notebook reads defective `*_test` images and raw labels, excluding templates. Its class order is `open_circuit`, `short`, `mouse_bite`, `spur`, `spurious_copper`, `pin_hole`. **Pin hole and missing hole differ; datasets are not silently merged.**

The notebook splits by parent board before augmentation, approximately 70/15/15 by group count. PKU grouping defaults to the leading number in `01_missing_hole_01`; DeepPCB uses `group*`. Verify these identifiers against source provenance. This protocol differs from DeepPCB's published split, so scores are not directly comparable. Conversion rejects duplicate decoded images, invalid boxes, ambiguous filenames, mismatched dimensions and missing classes in any split. Prefer original data to augmented mirrors.

See **[docs/research.md](docs/research.md)** for sources and experimental decisions. YOLO11 is an established baseline, not a claim to be the newest or best detector. Validate on your camera and healthy boards before production use.

## Verification

Use a dedicated disposable PostgreSQL database. Tests never fall back to the live `DATABASE_URL`. With Docker Desktop running:

```bash
docker compose -f compose.test.yaml up -d --wait
cp .env.test.example .env.test
uv run pytest -q
cd frontend
npm run build
npm run test:e2e
```

Python tests cover authentication, permissions, private images, administrator actions, upload validation, session revocation/expiry, missing-model behavior, manifest verification, dataset conversion, grouped splitting and notebook syntax/schema. Inference contract tests use an explicit fixture detector, not trained weights.

Browser tests start an isolated API and frontend and use locally installed Chrome by default. Tests create separate PostgreSQL schemas and temporary image directories; these are removed afterward. Bounding-box UI tests use an explicit test fixture detector, enabled only in the test server, not trained PCB weights. The production application has no fixture-inference endpoint. For bundled Chromium, install it with `npx playwright install chromium` and set `PLAYWRIGHT_CHANNEL=chromium`.

When finished, stop the disposable database with `docker compose -f compose.test.yaml down`.

Regenerate the notebook after editing `training/prepare.py` or its generator:

```bash
uv run python scripts/build_notebook.py
```

## Layout and deployment

```text
backend/       FastAPI, authentication, PostgreSQL migrations, YOLO adapter, admin CLI
frontend/      React/TypeScript UI and browser tests
notebooks/     Self-contained Kaggle notebook
training/      Dataset adapters and grouped holdout logic
scripts/       Notebook generator
tests/         API, dataset and inference-contract tests
docs/          Research and deployment guidance
models/        Trusted weights and manifest (ignored by Git)
data/          Protected image storage (ignored by Git)
.env           Server-only Neon connection string and configuration (ignored by Git)
```

This supports local use and a small single-instance deployment. **[docs/deployment.md](docs/deployment.md)** covers persistent storage, HTTPS, containers and remaining production work. Email verification, password recovery, MFA, organization isolation, background queues and retention controls are not implemented. OAuth provider buttons and unsupported heatmap claims are intentionally absent; sign-in uses the real email/password flow.

Review dataset terms and the [Ultralytics license](https://www.ultralytics.com/license) before commercial distribution. DeepPCB specifies research-only dataset use. This repository grants no rights to third-party datasets, packages or weights.
