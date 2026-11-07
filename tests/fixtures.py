from PIL import ImageDraw


class FixtureDetector:

    """Exercise persistence and HTTP contracts without pretending to run YOLO."""

    def status(self):

        return {
            "available": True,
            "state": "ready",
            "message": "Test fixture",
            "manifest": None,
            "image_size": 1024,
        }


    def predict(self, image, confidence):

        annotated = image.copy()
        ImageDraw.Draw(annotated).rectangle((1, 1, 12, 12), outline="#00e5e5", width=2)

        return (
            [{"label": "short", "confidence": 0.88, "box": [1, 1, 12, 12]}],
            annotated,
            12.5,
            "a" * 64,
        )
