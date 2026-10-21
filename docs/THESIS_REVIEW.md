# Review of the 2023 thesis and code

## Located manuscript

The principal manuscript is retained in the author's private MSc archive under
the original YOLOv7 litter-detection title.

It is approximately 11,750 extracted words. Several earlier/larger Word
variants also exist in that private archive.

## Material technical corrections

1. YOLOv7 is attributed incorrectly in multiple places. The 2022 YOLOv7 paper
   is by Chien-Yao Wang, Alexey Bochkovskiy, and Hong-Yuan Mark Liao.
2. The architecture discussion includes unsupported claims that YOLOv7 was
   built on YOLOv6, developed by Ultralytics, introduced a dual-stream attention
   head, replaced the loss with Dice loss, or is defined by a fixed 608-pixel
   input.
3. The reported detection metrics are internally inconsistent: values that
   decrease are described as improvements.
4. The statement that 640 is the number of parameters confuses image resolution
   with model size.
5. A claim of 30 FPS on Raspberry Pi conflicts with retained logs. The binary
   detector samples averaged about 7.98 seconds per frame (0.125 FPS), while
   the longer multiclass log averaged about 6.54 seconds per frame (0.153 FPS).
6. Accuracy, robustness, scalability, and cost-effectiveness are overstated
   relative to the retained evidence.
7. The original root `train.py` and `detect.py` are partial YOLOv7 repository
   files and cannot run without missing `models`, `utils`, and `test` modules.
8. Both notebooks contain a hard-coded Roboflow credential and machine-specific
   SageMaker paths.

## Revision strategy

The new manuscript does not silently rewrite the historical results. It frames
one RF-DETR Nano litter-detection, classification, tracking, and counting use
case prospectively, retains the research motivation, replaces unsupported
architecture claims, defines reproducible methods, and leaves measured results
pending until representative data and hardware tests exist. Maintainers train
and publish the checkpoint; deployment users are not required to train.

