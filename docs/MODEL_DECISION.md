# RF-DETR implementation decision

## Decision

Use RF-DETR Nano to implement the litter use case. This project does not rank
or compare detector families.

RF-DETR Nano was chosen as a compact, fine-tunable detector with a documented
Python API and export paths including ONNX, TensorRT, and TFLite. A validated
ONNX artifact can also be integrated with a compatible runtime such as
OpenVINO. The implementation remains behind a small adapter so the
tracking/counting core is not coupled to PyTorch or one accelerator.

## Use-case acceptance

The implementation is evaluated against the requirements of the litter
application:

1. Detect visible litter with a bounding box.
2. Classify it as glass, metal, paper/cardboard, plastic, or other litter.
3. Maintain a stable track when an object remains visible across frames.
4. Report current visible counts by class.
5. Count each confirmed track once per inspection session.
6. Produce structured evidence and optional annotated media.
7. Operate within the declared resource limits of the deployment device.

## Accuracy evaluation

The held-out target-domain test set will report:

- precision, recall, F1, mAP50, and mAP50-95;
- per-class AP and confusion matrix;
- errors by object size and scene condition;
- per-frame count mean absolute error;
- unique-session count error;
- duplicate-track and missed-track rates.

There is no model leaderboard. Results answer whether this RF-DETR
implementation is accurate enough for the defined use case.

## Deployment formats

The same trained checkpoint may be exported to different runtimes to make the
application usable across edge hardware. Testing two export formats verifies
portability; it is not a comparison of detector models. Each target retains its
own environment and accuracy manifest because conversion or quantization can
change model output.

## LLM/VLM role

An LLM or VLM is not part of the real-time detection, classification, tracking,
or counting path. The target Jetson already hosts LLM services, and adding
another continuous model would create unnecessary resource contention.

## Sources

- RF-DETR documentation: https://rfdetr.roboflow.com/
- RF-DETR export documentation: https://rfdetr.roboflow.com/latest/learn/export/
- RF-DETR repository: https://github.com/roboflow/rf-detr
