"""Dataset conversion embedded verbatim in the standalone Kaggle notebook."""

import hashlib
import json
import math
import random
import re
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

import yaml
from PIL import Image

PKU_NAMES = [
    "missing_hole",
    "mouse_bite",
    "open_circuit",
    "short",
    "spur",
    "spurious_copper",
]
DEEP_NAMES = [
    "open_circuit",
    "short",
    "mouse_bite",
    "spur",
    "spurious_copper",
    "pin_hole",
]
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


@dataclass
class Sample:

    image: Path
    group: str
    boxes: list  # (class_id, x1, y1, x2, y2), absolute pixels



def normalized_box(class_id, coords, width, height):

    x1, y1, x2, y2 = map(float, coords)

    if not all(math.isfinite(v) for v in [x1, y1, x2, y2]):

        raise ValueError("Non-finite box coordinate")

    if not (0 <= x1 < x2 <= width and 0 <= y1 < y2 <= height):

        raise ValueError(f"Invalid bounding box {coords} for {width}x{height}")

    return f"{class_id} {(x1 + x2) / (2 * width):.8f} {(y1 + y2) / (2 * height):.8f} {(x2 - x1) / width:.8f} {(y2 - y1) / height:.8f}"



def read_pku(root, group_pattern=r"^(\d+)_"):

    root = Path(root)
    images = defaultdict(list)

    for path in sorted(root.rglob("*")):

        if path.suffix.lower() in IMAGE_SUFFIXES:

            images[path.stem.lower()].append(path)

    xmls = sorted(root.rglob("*.xml"))

    if not xmls:

        raise ValueError(
            f"No VOC XML annotations found under {root}. Add the original akhatova/pcb-defects dataset."
        )

    samples = []

    for annotation in xmls:

        tree = ET.parse(annotation).getroot()
        stem = Path(
            (tree.findtext("filename") or annotation.stem).replace("\\", "/")
        ).stem.lower()
        candidates = images.get(stem, [])

        if len(candidates) != 1:

            raise ValueError(
                f"Expected one image for {annotation}, found {len(candidates)}. Select the dataset root without duplicate copies."
            )

        match = re.search(group_pattern, stem)

        if not match:

            raise ValueError(
                f"Cannot derive board identity from {stem}; set GROUP_PATTERN for your original board IDs."
            )

        with Image.open(candidates[0]) as image:

            width, height = image.size
            image.verify()

        if (
            int(tree.findtext("size/width", "0")),
            int(tree.findtext("size/height", "0")),
        ) != (width, height):

            raise ValueError(f"Annotation dimensions disagree with image: {annotation}")

        boxes = []

        for obj in tree.findall("object"):

            name = (
                (obj.findtext("name") or "")
                .strip()
                .lower()
                .replace(" ", "_")
                .replace("-", "_")
            )

            if name not in PKU_NAMES:

                raise ValueError(
                    f"Unknown class {name!r} in {annotation}; review the taxonomy before mapping it."
                )

            # Pascal VOC minima are one-based inclusive; convert to zero-based edges.
            coords = [
                float(obj.findtext(f"bndbox/{key}", "nan"))
                for key in ("xmin", "ymin", "xmax", "ymax")
            ]
            coords[0] -= 1
            coords[1] -= 1
            class_id = PKU_NAMES.index(name)
            normalized_box(class_id, coords, width, height)
            boxes.append((class_id, *coords))

        samples.append(Sample(candidates[0], match.group(1), boxes))

    if len({s.image for s in samples}) != len(samples):

        raise ValueError("Multiple annotations refer to the same image.")

    return samples, PKU_NAMES.copy()



def read_deeppcb(root):

    root = Path(root)
    labels = defaultdict(list)

    for path in root.rglob("*.txt"):

        labels[path.stem].append(path)

    samples = []

    for image_path in sorted(root.rglob("*_test.*")):

        if image_path.suffix.lower() not in IMAGE_SUFFIXES:

            continue

        stem = image_path.stem.removesuffix("_test")
        candidates = labels.get(stem, [])

        if len(candidates) != 1:

            raise ValueError(
                f"Expected one DeepPCB label for {image_path}, found {len(candidates)}"
            )

        groups = [
            p
            for p in image_path.relative_to(root).parts
            if re.fullmatch(r"group\d+", p)
        ]

        if len(groups) != 1:

            raise ValueError(
                f"Cannot derive parent board group for {image_path}; select a root above group* directories."
            )

        with Image.open(image_path) as image:

            width, height = image.size
            image.verify()

        boxes = []

        for line in candidates[0].read_text().splitlines():

            if not line.strip():

                continue

            values = re.split(r"[,\s]+", line.strip())

            if len(values) != 5:

                raise ValueError(f"Invalid DeepPCB annotation: {line}")

            x1, y1, x2, y2 = map(float, values[:4])
            source_id = int(values[4])

            if source_id not in range(1, 7):

                raise ValueError(f"Invalid DeepPCB class ID {source_id}")

            normalized_box(source_id - 1, (x1, y1, x2, y2), width, height)
            boxes.append((source_id - 1, x1, y1, x2, y2))

        samples.append(Sample(image_path, groups[0], boxes))

    if not samples:

        raise ValueError(
            "No DeepPCB *_test images found. Extract the original repository dataset first."
        )

    return samples, DEEP_NAMES.copy()



def write_dataset(samples, names, destination, seed=42):

    destination = Path(destination)
    # Never silently mix a new conversion with artifacts from an older run.

    if destination.exists() and any(destination.iterdir()):

        raise ValueError(
            f"Output directory must be empty: {destination}. Choose a new OUTPUT path to rerun."
        )

    groups = sorted({s.group for s in samples})

    if len(groups) < 3:

        raise ValueError(
            "At least three independent board groups are required for train/val/test."
        )

    random.Random(seed).shuffle(groups)
    n_test = max(1, round(len(groups) * 0.15))
    n_val = max(1, round(len(groups) * 0.15))
    allocation = {
        g: "test" if i < n_test else "val" if i < n_test + n_val else "train"
        for i, g in enumerate(groups)
    }

    if "train" not in allocation.values():

        raise ValueError("Not enough board groups for a training set")

    # Decode for a pixel-level digest: identical pixels in differently encoded files also collide.
    seen, records, counts = (
        {},
        [],
        {split: Counter() for split in ("train", "val", "test")},
    )
    staged = []

    for sample in samples:

        with Image.open(sample.image) as image:

            image = image.convert("RGB")
            width, height = image.size
            pixel_sha = hashlib.sha256(
                f"{width}x{height}".encode() + image.tobytes()
            ).hexdigest()

        split = allocation[sample.group]

        if pixel_sha in seen:

            raise ValueError(
                f"Duplicate image pixels found: {sample.image} and {seen[pixel_sha]}. Review duplicates and annotations before training."
            )

        seen[pixel_sha] = str(sample.image)
        lines = []

        for class_id, *coords in sample.boxes:

            if class_id not in range(len(names)):

                raise ValueError("Out-of-range class ID")

            lines.append(normalized_box(class_id, coords, width, height))
            counts[split][class_id] += 1

        staged.append((sample, split, pixel_sha, lines))

    for split, counter in counts.items():

        absent = [names[i] for i in range(len(names)) if not counter[i]]

        if absent:

            raise ValueError(
                f"{split} has no examples for {absent}. Review board grouping or choose a different seed before training; do not select a seed using test performance."
            )

    for split in counts:

        (destination / "images" / split).mkdir(parents=True)
        (destination / "labels" / split).mkdir(parents=True)

    for sample, split, pixel_sha, lines in staged:

        name = hashlib.sha256(str(sample.image).encode()).hexdigest()[:20]
        target = destination / "images" / split / f"{name}.png"

        with Image.open(sample.image) as image:

            image.convert("RGB").save(target)

        (destination / "labels" / split / f"{name}.txt").write_text(
            "\n".join(lines) + ("\n" if lines else "")
        )
        records.append(
            {
                "source": str(sample.image),
                "image": str(target.relative_to(destination)),
                "group": sample.group,
                "split": split,
                "pixel_sha256": pixel_sha,
                "boxes": len(lines),
            }
        )

    config = {
        "path": str(destination.resolve()),
        "train": "images/train",
        "val": "images/val",
        "test": "images/test",
        "names": dict(enumerate(names)),
    }
    (destination / "data.yaml").write_text(yaml.safe_dump(config, sort_keys=False))
    manifest = {
        "seed": seed,
        "protocol": "board_group_holdout_70_15_15_approximate",
        "groups": allocation,
        "names": names,
        "samples": records,
        "class_counts": {
            s: {names[i]: c[i] for i in range(len(names))} for s, c in counts.items()
        },
    }
    (destination / "split-manifest.json").write_text(json.dumps(manifest, indent=2))

    return destination / "data.yaml", manifest
