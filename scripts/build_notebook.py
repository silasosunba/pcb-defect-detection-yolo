"""Regenerate a standalone notebook; no repository imports are needed on Kaggle."""

from pathlib import Path
import textwrap
import sys

import nbformat as nbf
from format_code import format_python

ROOT = Path(__file__).resolve().parents[1]
cells = []


def md(text):

    cells.append(nbf.v4.new_markdown_cell(textwrap.dedent(text).strip()))



def code(text):

    source = format_python(textwrap.dedent(text).strip())
    cells.append(nbf.v4.new_code_cell(source))



md("""
# PCB defect detection · Kaggle training & application export

This notebook fine-tunes **YOLO11s** on PCB bounding boxes and produces the two files consumed by PCB Detect: **best.pt** and **model-manifest.json**. It is self-contained; upload this notebook alone to Kaggle.

1. Create a Kaggle notebook and upload this `.ipynb`.
2. Add [akhatova/pcb-defects](https://www.kaggle.com/datasets/akhatova/pcb-defects) through **Add Input**.
3. Enable **GPU** and **Internet** in notebook settings (package install and pretrained weight download need Internet). Do not replace Kaggle's CUDA-enabled PyTorch.
4. Inspect the mounted paths printed below and set `DATA_ROOT`. Run all cells.
5. Save a notebook version with outputs and download `/kaggle/working/pcb-export/`.

No accuracy is claimed before executing this notebook. Group holdouts are stricter than random image splits and can produce lower, more useful scores. The dataset contains synthetic defects; also evaluate on your own camera and real manufacturing defects.
""")
code("""
import subprocess, sys

subprocess.check_call(
    [
        sys.executable,
        "-m",
        "pip",
        "install",
        "-q",
        "ultralytics==8.3.253",
        "pyyaml>=6,<7",
    ]
)
""")
code("""
from pathlib import Path
import os, random, json, hashlib, shutil, platform
import numpy as np
import torch
import ultralytics
from ultralytics import YOLO
from IPython.display import display, Image as DisplayImage

print("Python:", platform.python_version(), "Ultralytics:", ultralytics.__version__)
print("Torch:", torch.__version__, "CUDA:", torch.cuda.is_available())
print("Mounted inputs:")

for path in sorted(Path("/kaggle/input").iterdir()):

    print(path)

if not torch.cuda.is_available():

    raise RuntimeError("Select a GPU accelerator in Kaggle settings before training.")

print("GPU:", torch.cuda.get_device_name(0))
""")
md("""
## Configure this run

Default: original PKU-style Pascal VOC XML annotations. `DATA_ROOT` must contain the actual images and XML files, not an unextracted ZIP. The default path matches the dataset slug; Kaggle may mount a different path, so inspect the listing above.

Alternative: attach an extracted [DeepPCB](https://github.com/tangsanli5201/DeepPCB) dataset and set `DATASET_KIND="deeppcb"`. It uses only `*_test` images and raw `x1 y1 x2 y2 type` labels, excluding template images. It performs a **new parent-board holdout**, not DeepPCB's published 1,000/500 split, so scores are not directly comparable to that benchmark.

**Do not merge these taxonomies**: PKU has `missing_hole`; DeepPCB has `pin_hole`. For YOLO-converted or augmented mirrors, use the original source dataset here instead; untracked augmentation can leak board identity across splits.
""")
code("""
DATASET_KIND = "pku_voc"  # or "deeppcb"
DATA_ROOT = Path("/kaggle/input/pcb-defects")
OUTPUT = Path(
    "/kaggle/working/pcb-yolo-data"
)  # choose an empty path when rerunning conversion
GROUP_PATTERN = r"^(\\d+)_"  # e.g. 01_missing_hole_01 -> original board 01
SEED = 42
MODEL = (
    "yolo11s.pt"  # yolo11n.pt for a faster baseline; do not use a classification model
)
IMAGE_SIZE = 1024
BATCH = 4  # reduce to 2 on GPU OOM; use IMAGE_SIZE=640 only if necessary
EPOCHS = 100
RUN_NAME = "pcb-yolo11s"
RUNS = Path("/kaggle/working/runs")
RESUME_FROM = (
    None  # optional absolute path to a matching previous run's weights/last.pt
)

assert DATASET_KIND in {"pku_voc", "deeppcb"}
assert DATA_ROOT.is_dir(), f"Dataset directory missing: {DATA_ROOT}"
os.environ["WANDB_MODE"] = "disabled"
random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)
""")
md("""
## Validate annotations and split by parent board

Conversion checks image dimensions, class names, box geometry and duplicate decoded pixels. It fails on ambiguous filenames or duplicate images rather than silently treating missing labels as negative examples. Review and resolve each reported issue in the source.

All variations of a parent board stay together. The split is approximately 70/15/15 by **group count**, so image counts may differ. Check the printed group allocation and class counts before training. With few board layouts, results have high variance; use repeated group folds for a final research report. Filename grouping cannot prove physical board independence: verify `GROUP_PATTERN` and source provenance.
""")
code((ROOT / "training/prepare.py").read_text())
code("""
samples, names = (
    read_pku(DATA_ROOT, GROUP_PATTERN)
    if DATASET_KIND == "pku_voc"
    else read_deeppcb(DATA_ROOT)
)
data_yaml, split_manifest = write_dataset(samples, names, OUTPUT, SEED)
print("Dataset:", data_yaml)
print("Parent board allocation:", split_manifest["groups"])

for split in ("train", "val", "test"):

    rows = [r for r in split_manifest["samples"] if r["split"] == split]
    print(split, "images:", len(rows), "boxes:", sum(r["boxes"] for r in rows))
    print(split_manifest["class_counts"][split])

print("Class order:", names)
""")
md("""
## Inspect labels visually

Check these images before spending GPU time. Boxes must cover the actual defects and labels must match them. Small defects can disappear when full-resolution boards are resized; 1024 px is a baseline. A future tiling experiment should split by parent board **before** generating crops and use a matching inference strategy.
""")
code("""
from PIL import ImageDraw
from PIL import Image as PILImage

for image_path in list((OUTPUT / "images/train").glob("*.png"))[:4]:

    image = PILImage.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(image)
    label_path = OUTPUT / "labels/train" / f"{image_path.stem}.txt"

    for line in label_path.read_text().splitlines():

        cls, xc, yc, bw, bh = map(float, line.split())
        x1, y1 = (xc - bw / 2) * image.width, (yc - bh / 2) * image.height
        x2, y2 = (xc + bw / 2) * image.width, (yc + bh / 2) * image.height
        draw.rectangle((x1, y1, x2, y2), outline="lime", width=3)
        draw.text((x1, max(0, y1 - 12)), names[int(cls)], fill="red")

    image.thumbnail((1000, 700))
    display(image)
""")
md("""
## Fine-tune pretrained weights

Use validation for model selection and confidence threshold tuning. The test split is not used here. Mild augmentation avoids hiding tiny defects; early stopping uses validation. `last.pt` supports recovery if Kaggle interrupts the session; save it as a private dataset and set `RESUME_FROM` when resuming with the same converted dataset and paths. Check the saved `args.yaml` when changing configuration.
""")
code("""
if RESUME_FROM:

    model = YOLO(str(RESUME_FROM))
    model.train(resume=True, device=0)

else:

    model = YOLO(MODEL, task="detect")
    model.train(
        data=str(data_yaml),
        epochs=EPOCHS,
        imgsz=IMAGE_SIZE,
        batch=BATCH,
        device=0,
        workers=2,
        seed=SEED,
        deterministic=True,
        project=str(RUNS),
        name=RUN_NAME,
        exist_ok=False,
        patience=25,
        optimizer="AdamW",
        lr0=0.001,
        weight_decay=0.0005,
        cos_lr=True,
        close_mosaic=15,
        mosaic=0.5,
        mixup=0.0,
        degrees=5.0,
        translate=0.05,
        scale=0.25,
        fliplr=0.5,
        flipud=0.5,
        hsv_h=0.01,
        hsv_s=0.2,
        hsv_v=0.2,
        plots=True,
        save=True,
    )

RUN_DIR = Path(model.trainer.save_dir)
BEST = RUN_DIR / "weights/best.pt"
assert BEST.is_file(), "Training did not produce best.pt. Review the training logs."
print("Best checkpoint:", BEST)

if (RUN_DIR / "results.png").is_file():

    display(DisplayImage(filename=str(RUN_DIR / "results.png")))
""")
md("""
## Validation and one final held-out evaluation

Review per-class precision, recall, mAP@0.5, mAP@0.5:0.95 and confusion matrices. Tune thresholds or settings using validation only. Run the test evaluation once after fixing those choices; do not repeatedly tune against it. mAP is not classification accuracy, and no detections does not establish that a board is defect-free.
""")
code("""
best_model = YOLO(str(BEST))
assert best_model.task == "detect", (
    "This application requires bounding-box object detection weights."
)
assert [best_model.names[i] for i in range(len(best_model.names))] == names
validation = best_model.val(
    data=str(data_yaml),
    split="val",
    imgsz=IMAGE_SIZE,
    batch=BATCH,
    device=0,
    project=str(RUNS),
    name="validation",
    plots=True,
)
test = best_model.val(
    data=str(data_yaml),
    split="test",
    imgsz=IMAGE_SIZE,
    batch=BATCH,
    device=0,
    project=str(RUNS),
    name="held-out-test",
    plots=True,
)
print("Validation:", validation.results_dict)
print("Held-out test:", test.results_dict)
print("Test per-class mAP50-95:", dict(zip(names, map(float, test.box.maps))))
""")
md("""
## Preview predicted bounding boxes

This is **object detection**, not image classification. Each prediction contains a defect class, confidence and an `xyxy` bounding box in the original image's pixel coordinates. The next cell draws those predictions on held-out images and saves both annotated images and JSON coordinates in the application export directory. These predictions differ from the ground-truth label preview above. The model does not train severity labels or Grad-CAM explanations.
""")
code("""
PREVIEW_DIR = Path("/kaggle/working/pcb-export/predictions")
PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
prediction_records = []

for image_path in sorted((OUTPUT / "images/test").glob("*.png"))[:6]:

    result = best_model.predict(
        source=str(image_path), imgsz=IMAGE_SIZE, conf=0.25, device=0, verbose=False
    )[0]
    annotated = PILImage.fromarray(
        result.plot()[..., ::-1]
    )  # Ultralytics plots BGR; Pillow displays RGB.
    annotated.save(PREVIEW_DIR / image_path.name)
    preview = annotated.copy()
    preview.thumbnail((1100, 750))
    display(preview)
    boxes = [
        {
            "label": result.names[int(box.cls.item())],
            "confidence": float(box.conf.item()),
            "box": [float(x) for x in box.xyxy[0].tolist()],
        }
        for box in result.boxes
    ]
    prediction_records.append({"image": image_path.name, "detections": boxes})
    print(image_path.name, json.dumps(boxes, indent=2))

(PREVIEW_DIR / "predictions.json").write_text(json.dumps(prediction_records, indent=2))
print("Annotated prediction examples:", PREVIEW_DIR)
""")
md("""
## Export the application artifacts

The manifest records class order, dataset protocol, versions, measured test metrics and a SHA-256 checksum of the exact weights. The API verifies the checksum and classes before use. Keep the training environment report for reproducibility. Optional ONNX export is provided for future deployment; the current API loads `best.pt`.
""")
code("""
from datetime import datetime, timezone

EXPORT = Path("/kaggle/working/pcb-export")
EXPORT.mkdir(exist_ok=True)
shutil.copy2(BEST, EXPORT / "best.pt")
manifest = {
    "schema_version": 1,
    "task": "detect",
    "architecture": Path(MODEL).stem,
    "names": names,
    "dataset": DATASET_KIND,
    "dataset_root": str(DATA_ROOT),
    "split_protocol": split_manifest["protocol"],
    "seed": SEED,
    "image_size": IMAGE_SIZE,
    "created_at": datetime.now(timezone.utc).isoformat(),
    "sha256": hashlib.sha256((EXPORT / "best.pt").read_bytes()).hexdigest(),
    "ultralytics_version": ultralytics.__version__,
    "torch_version": torch.__version__,
    "metrics": {k: float(v) for k, v in test.results_dict.items()},
    "validation_metrics": {k: float(v) for k, v in validation.results_dict.items()},
    "per_class_map50_95": dict(zip(names, map(float, test.box.maps))),
}
(EXPORT / "model-manifest.json").write_text(json.dumps(manifest, indent=2))
shutil.copy2(OUTPUT / "split-manifest.json", EXPORT / "split-manifest.json")

for filename in ("results.csv", "results.png", "args.yaml"):

    if (RUN_DIR / filename).is_file():

        shutil.copy2(RUN_DIR / filename, EXPORT / filename)

(EXPORT / "training-requirements.txt").write_text(
    subprocess.check_output([sys.executable, "-m", "pip", "freeze"], text=True)
)
print(json.dumps(manifest, indent=2))
print("Download artifacts from:", EXPORT)

# Optional: the React application does not require ONNX.
# best_model.export(format="onnx", imgsz=IMAGE_SIZE, dynamic=False, simplify=False)
""")
md("""
## Bring the model into PCB Detect

On your local machine, run `uv sync --extra inference`. Copy `best.pt` and `model-manifest.json` into `models/` in the project, and restart the API. Use `PCB_IMAGE_SIZE` matching this run (default 1024). Set `PCB_DEVICE=cpu`, `mps` on a supported Mac, or `0` on a CUDA host.

The model is loaded by Python on the server; the React client uploads images and displays results. Never load a `.pt` file from an untrusted source: checkpoints can contain executable Python objects.

## Sources and research context

- [PKU dataset paper: Huang & Wei, 2019](https://arxiv.org/abs/1901.08204): synthetic defects and a reference-based detection/classification approach.
- [Kaggle PCB Defects](https://www.kaggle.com/datasets/akhatova/pcb-defects): default data source. Check the current dataset card, license and actual file contents; counts can differ across mirrors.
- [DeepPCB authors' repository](https://github.com/tangsanli5201/DeepPCB): paired reference/test images, six classes, raw annotation specification and research-use notice.
- [DeepPCB paper](https://arxiv.org/abs/1902.06197): a reference-based benchmark, with a different evaluation protocol from this notebook.
- [Existing community YOLO training implementation](https://github.com/Gabriel-Almeida-ECAT/YOLO_PCB_DEFECTS): a useful example of Kaggle-to-YOLO conversion; this notebook implements its own validation and grouped split.
- [Ultralytics YOLO11](https://docs.ultralytics.com/models/yolo11/) and [training documentation](https://docs.ultralytics.com/modes/train/): baseline model and official training/inference API. YOLO11 is an established baseline, not a claim of being the newest YOLO release.

Review dataset usage terms and Ultralytics AGPL-3.0/enterprise licensing before commercial distribution. Keep healthy-board images in a future deployment evaluation: these defect-focused benchmarks alone do not establish the false-alarm rate on normal production boards.
""")

for index, cell in enumerate(cells):

    cell.id = f"pcb-{index:02d}"


notebook = nbf.v4.new_notebook(
    cells=cells,
    metadata={
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3",
        },
        "language_info": {"name": "python", "version": "3.10"},
    },
)
nbf.validate(notebook)
target = ROOT / "notebooks/pcb_yolo_kaggle.ipynb"
target.parent.mkdir(exist_ok=True)

if "--check" in sys.argv:

    if not target.exists() or nbf.read(target, as_version=4) != notebook:

        raise SystemExit(
            "The training notebook needs regeneration. Run python scripts/format_code.py."
        )

    print("Training notebook is formatted and up to date.")

else:

    nbf.write(notebook, target)
    print(target)
