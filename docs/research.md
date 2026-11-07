# PCB dataset and model research

Research checked on 6 November 2026. Reported results in external sources are not results achieved by this repository.

| Source | Useful finding | Implementation decision |
| --- | --- | --- |
| [Huang & Wei: A PCB Dataset for Defects Detection and Classification](https://arxiv.org/abs/1901.08204) | Describes a synthetic PCB defect dataset and a reference-based detection/classification approach. | Start with PKU-style bounding boxes as a single-image YOLO baseline; validate on real manufacturing defects separately. |
| [Kaggle: akhatova/pcb-defects](https://www.kaggle.com/datasets/akhatova/pcb-defects) | Input source for the notebook. | Read original images and VOC XML; measure actual file counts and dimensions rather than relying on mirror descriptions. |
| [DeepPCB authors' repository](https://github.com/tangsanli5201/DeepPCB) and [paper](https://arxiv.org/abs/1902.06197) | Paired template/test images and raw box labels. Source IDs: 1=open, 2=short, 3=mousebite, 4=spur, 5=copper, 6=pin-hole. Authors specify research use. | Use a separate adapter/taxonomy, excluding template images. Keep parent groups together; this differs from the published benchmark split. |
| [Existing YOLO PCB implementation](https://github.com/Gabriel-Almeida-ECAT/YOLO_PCB_DEFECTS) | Community conversion and training example using the Kaggle data. | Workflow reference; this project implements its own conversion validation, group holdout and export contract. No performance claims are copied. |
| [Ultralytics YOLO11](https://docs.ultralytics.com/models/yolo11/) and [Python usage](https://docs.ultralytics.com/usage/python/) | Established pretrained models with train/validate/predict/export APIs. | Use YOLO11s and the same pinned release in training and inference. Start with a baseline before architecture changes. |
| [Official training documentation](https://docs.ultralytics.com/modes/train/) | Device, resolution, augmentation, early stopping and checkpoint resume controls. | Start with 1024 px, mild augmentation, one Kaggle GPU and validation early stopping. Preserve configuration and environment versions. |

## Evaluation protocol

1. Check data provenance and usage terms; prefer original images to pre-augmented mirrors.
2. Validate annotation/image alignment and inspect label previews.
3. Derive parent-board IDs, split by those IDs, and check decoded-pixel duplicates. Filename grouping is a convention, not proof of physical independence.
4. Apply augmentation only during training. Record seed, allocation, class counts and input resolution.
5. Select settings and confidence thresholds using validation. Review per-class precision/recall and confusion matrices.
6. Evaluate the held-out test after fixing those settings. Report mAP50 and mAP50-95 as detection metrics, rather than calling them accuracy.
7. Test actual production camera images, including confirmed healthy boards. Measure false alarms, missed defects and latency.

PKU and DeepPCB include synthetic defects and do not fully describe production variability. The application reports “No defects detected”; it does not certify that a board passes inspection.

## Further experiments

Compare YOLO11n and YOLO11s on fixed splits and hardware. If resizing removes tiny defects, investigate tiling after board splitting with matching tiled inference and duplicate suppression. For research reporting, use multiple board holdouts and report variability. Add real camera examples and healthy boards before increasing model complexity.
