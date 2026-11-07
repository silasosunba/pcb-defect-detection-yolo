import hashlib
import json
import sys
from types import SimpleNamespace

import pytest

from backend.config import Settings
from backend.inference import Detector, ModelUnavailable


@pytest.fixture
def detector(tmp_path, monkeypatch):

    settings = Settings(
        model_path=tmp_path / "best.pt", manifest_path=tmp_path / "model-manifest.json"
    )
    settings.model_path.write_bytes(b"controlled-fixture-not-a-checkpoint")
    settings.manifest_path.write_text(
        json.dumps(
            {
                "task": "detect",
                "names": ["short"],
                "sha256": hashlib.sha256(settings.model_path.read_bytes()).hexdigest(),
            }
        )
    )
    # Test verification ordering without installing the GPU inference stack.
    monkeypatch.setattr(
        "backend.inference.importlib.util.find_spec", lambda name: object()
    )

    return Detector(settings)



def test_checksum_mismatch_rejected_before_deserialization(detector):

    detector.settings.model_path.write_bytes(b"different")

    with pytest.raises(ModelUnavailable):

        detector._load()

    assert detector.status()["state"] == "error"



def test_foreign_classes_are_rejected(detector):

    manifest = json.loads(detector.settings.manifest_path.read_text())
    manifest["names"] = ["person"]
    detector.settings.manifest_path.write_text(json.dumps(manifest))

    with pytest.raises(ModelUnavailable):

        detector._load()



def test_model_class_order_must_match_manifest(detector, monkeypatch):

    monkeypatch.setitem(
        sys.modules,
        "ultralytics",
        SimpleNamespace(
            YOLO=lambda _: SimpleNamespace(task="detect", names={0: "spur"})
        ),
    )

    with pytest.raises(ModelUnavailable):

        detector._load()



def test_verified_model_becomes_ready(detector, monkeypatch):

    monkeypatch.setitem(
        sys.modules,
        "ultralytics",
        SimpleNamespace(
            YOLO=lambda _: SimpleNamespace(task="detect", names={0: "short"})
        ),
    )
    detector._load()
    assert detector.status()["state"] == "ready"
    assert detector.status()["manifest"]["names"] == ["short"]



def test_inference_draws_boxes_and_returns_pixel_coordinates(detector):

    from PIL import Image

    box = SimpleNamespace(
        xyxy=[SimpleNamespace(tolist=lambda: [2, 16, 24, 29])],
        cls=SimpleNamespace(item=lambda: 0),
        conf=SimpleNamespace(item=lambda: 0.9),
    )
    detector.model = SimpleNamespace(
        names={0: "short"}, predict=lambda **kwargs: [SimpleNamespace(boxes=[box])]
    )
    detector.manifest = {"sha256": "a" * 64}
    image = Image.new("RGB", (40, 40), "black")
    detections, annotated, _, sha = detector.predict(image, 0.25)
    assert detections[0]["box"] == [2, 16, 24, 29]
    assert annotated.getpixel((2, 28)) == (0, 229, 229)
    assert image.getpixel((2, 28)) == (0, 0, 0)
    assert sha == "a" * 64
