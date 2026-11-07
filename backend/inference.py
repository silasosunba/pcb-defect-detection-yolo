import hashlib
import importlib.util
import json
import threading
import time

from PIL import ImageDraw

ALLOWED_CLASSES = {
    "missing_hole",
    "mouse_bite",
    "open_circuit",
    "short",
    "spur",
    "spurious_copper",
    "pin_hole",
}


class ModelUnavailable(Exception):

    pass



class Detector:

    def __init__(self, settings):

        self.settings = settings
        self.lock = threading.Lock()
        self.model = None
        self.manifest = None
        self.error = None


    def status(self):

        installed = (
            self.settings.model_path.is_file() and self.settings.manifest_path.is_file()
        )
        runtime = importlib.util.find_spec("ultralytics") is not None

        return {
            "available": installed and runtime and not self.error,
            "state": "error"
            if self.error
            else "ready"
            if self.model
            else "installed"
            if installed and runtime
            else "not_configured",
            "message": self.error
            or (
                "Model loaded and verified."
                if self.model
                else "Model will be verified on first inspection."
                if installed and runtime
                else "Install the inference dependencies and copy best.pt and model-manifest.json from Kaggle into models/."
            ),
            "manifest": self.manifest,
            "image_size": self.settings.image_size,
        }


    def _load(self):

        if self.model is not None:

            return

        if not self.status()["available"]:

            raise ModelUnavailable(self.status()["message"])

        try:

            manifest = json.loads(self.settings.manifest_path.read_text())
            names = manifest["names"]

            if (
                manifest.get("task") != "detect"
                or not isinstance(names, list)
                or not names
                or len(set(names)) != len(names)
                or not set(names) <= ALLOWED_CLASSES
            ):

                raise ValueError("Invalid PCB class manifest")

            with self.settings.model_path.open("rb") as handle:

                sha = hashlib.sha256()

                for chunk in iter(lambda: handle.read(1024 * 1024), b""):

                    sha.update(chunk)

            if sha.hexdigest() != manifest["sha256"]:

                raise ValueError("Weight checksum differs from manifest")

            from ultralytics import YOLO

            model = YOLO(str(self.settings.model_path))

            if (
                model.task != "detect"
                or [model.names[i] for i in range(len(model.names))] != names
            ):

                raise ValueError("Model classes differ from manifest")

            self.manifest, self.model = manifest, model

        except Exception as exc:

            self.error = "Model verification failed. Check the exported weights, manifest and inference runtime; restart after replacing them."

            raise ModelUnavailable(self.error) from exc


    def predict(self, image, confidence):

        with self.lock:

            self._load()
            started = time.perf_counter()
            result = self.model.predict(
                source=image,
                conf=confidence,
                imgsz=self.settings.image_size,
                device=self.settings.device,
                verbose=False,
            )[0]
            detections = []
            annotated = image.copy()
            draw = ImageDraw.Draw(annotated)

            for index, box in enumerate(result.boxes, 1):

                coords = [round(float(v), 2) for v in box.xyxy[0].tolist()]
                label = self.model.names[int(box.cls.item())]
                score = round(float(box.conf.item()), 4)
                detections.append({"label": label, "confidence": score, "box": coords})
                draw.rectangle(
                    coords, outline="#00e5e5", width=max(2, image.width // 400)
                )
                draw.text(
                    (coords[0], max(0, coords[1] - 12)),
                    f"{index}. {label} {score:.0%}",
                    fill="#ffffff",
                    stroke_width=1,
                    stroke_fill="#0f172a",
                )

            return (
                detections,
                annotated,
                round((time.perf_counter() - started) * 1000, 1),
                self.manifest["sha256"],
            )
