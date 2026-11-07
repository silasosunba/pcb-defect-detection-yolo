import ast
import json
from pathlib import Path

import nbformat
import pytest
from PIL import Image

from training.prepare import (
    DEEP_NAMES,
    PKU_NAMES,
    Sample,
    normalized_box,
    read_deeppcb,
    read_pku,
    write_dataset,
)


def test_notebook_is_standalone_and_syntactically_valid():

    notebook = nbformat.read(
        Path(__file__).parents[1] / "notebooks/pcb_yolo_kaggle.ipynb", as_version=4
    )
    nbformat.validate(notebook)
    code = "\n".join(c.source for c in notebook.cells if c.cell_type == "code")
    ast.parse(code)
    assert "from training" not in code
    assert 'GROUP_PATTERN = r"^(\\d+)_"' in code
    assert '"sha256"' in code and 'split="test"' in code
    assert 'task="detect"' in code and "result.plot()" in code
    assert "box.xyxy" in code and "predictions.json" in code



def test_box_geometry():

    values = normalized_box(0, [0, 0, 10, 20], 100, 100).split()
    assert list(map(float, values[1:])) == [0.05, 0.1, 0.1, 0.2]

    for coords in [
        [1, 1, 0, 2],
        [-1, 0, 5, 5],
        [0, 0, 101, 2],
        [float("nan"), 0, 5, 5],
    ]:

        with pytest.raises(ValueError):

            normalized_box(0, coords, 100, 100)



def test_pku_xml_conversion_and_grouping(tmp_path):

    (tmp_path / "images").mkdir()
    Image.new("RGB", (100, 80), "green").save(
        tmp_path / "images/01_missing_hole_01.jpg"
    )
    (tmp_path / "sample.xml").write_text(
        """<annotation><filename>01_missing_hole_01.jpg</filename><size><width>100</width><height>80</height></size><object><name>missing_hole</name><bndbox><xmin>1</xmin><ymin>1</ymin><xmax>10</xmax><ymax>20</ymax></bndbox></object></annotation>"""
    )
    samples, names = read_pku(tmp_path)
    assert names == PKU_NAMES and samples[0].group == "01"
    assert samples[0].boxes[0] == (0, 0, 0, 10, 20)



def test_deeppcb_class_mapping_and_template_exclusion(tmp_path):

    board = tmp_path / "group00041/00041"
    labels = tmp_path / "group00041/00041_not"
    board.mkdir(parents=True)
    labels.mkdir()

    for suffix in ("test", "temp"):

        Image.new("RGB", (30, 30), "white").save(board / f"00041000_{suffix}.jpg")

    (labels / "00041000.txt").write_text("1 2 10 12 5\n4,5,15,18,6\n")
    samples, names = read_deeppcb(tmp_path)
    assert len(samples) == 1 and names == DEEP_NAMES
    assert samples[0].boxes[0][0] == 4 and names[4] == "spurious_copper"
    assert samples[0].boxes[1][0] == 5 and names[5] == "pin_hole"



def make_samples(root):

    root.mkdir()
    samples = []

    for group in range(10):

        for variant in range(2):

            path = root / f"{group}_{variant}.png"
            Image.new("RGB", (40, 40), (group * 20, variant * 80, 30)).save(path)
            samples.append(
                Sample(path, str(group), [(i, 1, 1, 10 + i, 20) for i in range(6)])
            )

    return samples



def test_group_split_reproducibility_and_manifests(tmp_path):

    samples = make_samples(tmp_path / "input")
    data, manifest = write_dataset(samples, PKU_NAMES, tmp_path / "out")
    _, second = write_dataset(samples, PKU_NAMES, tmp_path / "second")
    assert manifest["groups"] == second["groups"]
    assert data.is_file()
    assert set(manifest["groups"].values()) == {"train", "val", "test"}

    for group in range(10):

        assert (
            len({r["split"] for r in manifest["samples"] if r["group"] == str(group)})
            == 1
        )

    assert (
        json.loads((data.parent / "split-manifest.json").read_text())["names"]
        == PKU_NAMES
    )

    with pytest.raises(ValueError, match="empty"):

        write_dataset(samples, PKU_NAMES, tmp_path / "out")



def test_duplicate_pixels_and_absent_classes_fail(tmp_path):

    samples = make_samples(tmp_path / "input")
    samples.append(samples[0])

    with pytest.raises(ValueError, match="Duplicate"):

        write_dataset(samples, PKU_NAMES, tmp_path / "duplicate-out")

    for sample in samples[:-1]:

        sample.boxes = []

    with pytest.raises(ValueError, match="no examples"):

        write_dataset(samples[:-1], PKU_NAMES, tmp_path / "absent-out")
