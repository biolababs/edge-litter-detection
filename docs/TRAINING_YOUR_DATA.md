# Training with your own data

The application works immediately with the public Grounding DINO or
OmDet-Turbo backends. Training is optional. It is useful when the public model
does not provide sufficient accuracy for a particular camera, facility,
vehicle, waste stream, or operating environment.

Training should run centrally on a workstation or cloud GPU. Deployment devices
only need the final validated checkpoint.

## Before training

First try the lower-cost improvements:

1. review false detections and missed objects from representative footage;
2. improve the open-vocabulary prompts in `config/classes.yaml`;
3. adjust the confidence threshold using validation data; and
4. confirm that camera position, lighting, focus, and object size are suitable.

Fine-tune a closed-set RF-DETR Nano checkpoint when prompt and camera changes
are not sufficient.

## 1. Freeze the class contract

The default product taxonomy is defined in `config/classes.yaml`. A custom
COCO dataset must use exactly the same numeric IDs and names:

```text
0  plastic_bottle
1  glass_bottle
2  metal_can
...
15 other_litter
```

Edit the taxonomy before annotation if the deployment needs different classes.
Changing a class ID or name after closed-set training requires a new dataset
and checkpoint. Sorting destinations can be changed independently in
`config/separation.yaml`.

Do not assign a material class when the image does not provide enough visual
evidence. Use `other_litter`, route the observation for human review, or omit it
according to the annotation policy.

## 2. Collect representative data

Capture images or extract frames from the actual operating domain:

- the intended truck, sorting line, fixed camera, or handheld viewpoint;
- expected object sizes, contamination, crushing, overlap, and occlusion;
- normal and difficult lighting, weather, motion, and background conditions;
- empty scenes and confusing non-litter objects for negative examples; and
- every class that will be enabled in the released checkpoint.

Avoid collecting more adjacent video frames than necessary. Near-identical
frames add little information and can produce misleading test results.

Apply the approved privacy, retention, and de-identification process before
using field media. Keep private data and credentials outside Git.

## 3. Annotate and export COCO detection data

Draw one bounding box around each visible target object and export COCO object
detection annotations. The dataset directory must have this structure:

```text
data/my-litter-v1/
├── train/
│   ├── _annotations.coco.json
│   └── image files...
├── valid/
│   ├── _annotations.coco.json
│   └── image files...
└── test/
    ├── _annotations.coco.json
    └── image files...
```

Every split must contain the same `categories` array. Category IDs and names
must exactly match `config/classes.yaml`. COCO boxes use
`[x, y, width, height]` pixel coordinates.

Example category fragment:

```json
{
  "categories": [
    {"id": 0, "name": "plastic_bottle"},
    {"id": 1, "name": "glass_bottle"},
    {"id": 2, "name": "metal_can"}
  ]
}
```

Keep the complete configured category array in every split, including classes
that happen to have no instances in that split.

## 4. Split by source, not by random frame

Assign an entire source video, route, site, collection session, or camera
sequence to only one split. Adjacent frames from one recording must not appear
in both training and evaluation data.

Use:

- `train` for parameter learning;
- `valid` for checkpoint and threshold decisions; and
- `test` as a frozen held-out set used only for final reporting.

Record the grouping rule, dataset version, source licenses, annotation guide,
class counts, and checksums.

## 5. Optionally prepare the public TACO bootstrap

The repository can create an attributed COCO bootstrap dataset:

```bash
python prepare_training_data.py \
  --output data/taco-operational-v1
```

TACO does not cover every product class or deployment condition. Use it as
licensed bootstrap material, not as proof that a facility or vehicle
deployment is accurate. A site can train on its own COCO export or create one
combined, license-reviewed COCO dataset containing both public and field data.

The repository does not place downloaded images or custom datasets in Git.

## 6. Create the training environment

Use a separate environment on the training machine:

```bash
python3 -m venv .venv-train
source .venv-train/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[runtime,train]"
```

For NVIDIA or AMD acceleration, install the vendor-supported PyTorch build for
the host before installing the project extras. Confirm the device:

```bash
python -c \
  'import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU")'
```

## 7. Run a short training smoke test

Use a small run to verify the data, taxonomy, memory requirement, and output
path before committing to a full job:

```bash
python train.py \
  --data data/my-litter-v1 \
  --model rfdetr-nano \
  --device cuda \
  --epochs 2 \
  --batch 2 \
  --name my-litter-smoke
```

The trainer rejects a training annotation taxonomy that does not exactly match
`config/classes.yaml`. It also writes environment and dataset-manifest evidence
under `runs/litter/<run-name>/`.

## 8. Train the release candidate

After the smoke test succeeds:

```bash
python train.py \
  --data data/my-litter-v1 \
  --model rfdetr-nano \
  --device cuda \
  --epochs 100 \
  --batch 4 \
  --name my-litter-v1
```

The defaults enable early stopping. Adjust batch size to fit GPU memory.
Preserve the configuration, Git commit, package versions, dataset version, and
generated research manifest with the checkpoint.

List the generated checkpoints:

```bash
find runs/litter/my-litter-v1 -type f -name '*.pth' -print
```

## 9. Evaluate before deployment

Evaluate the selected checkpoint once on the frozen test split:

```bash
python evaluate.py \
  --weights runs/litter/my-litter-v1/<checkpoint>.pth \
  --data data/my-litter-v1 \
  --split test \
  --device cuda \
  --output reports/generated/my-litter-v1-accuracy.json
```

Then exercise the full application on representative video:

```bash
LITTER_VENV="$PWD/.venv-train" ./startup.sh \
  --skip-install \
  --backend rfdetr \
  --model runs/litter/my-litter-v1/<checkpoint>.pth \
  --source media/representative-line-video.mp4 \
  --device cuda \
  --no-display
```

Review detection/classification accuracy, per-class failures, count error,
latency, memory, temperature, and human-review volume. A successful training
job alone is not deployment acceptance.

## 10. Improve safely

Use false positives, missed objects, and corrected review-queue items to create
a new versioned dataset. Keep the original held-out test set frozen; create a
new test release if it has been used repeatedly for design decisions.

Do not replace the public release checkpoint until the candidate:

- covers every enabled class;
- passes the declared accuracy and count requirements;
- passes sustained testing on the intended edge device;
- has a model card, dataset statement, and SHA-256 checksum; and
- retains all required dataset, model, and software notices.

After publication, deployment users can download the validated checkpoint
through the normal launcher. They still do not need the training environment or
training dataset.
