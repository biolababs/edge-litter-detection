# License notice

The original software source code, configuration, schemas, deployment examples,
and software documentation in this repository are licensed under the Apache
License 2.0, as recorded in `LICENSE`.

The academic thesis manuscript, datasets, annotations, model weights, private
images, and generated research results are not relicensed by the software
license unless a separate release explicitly says otherwise.

Grounding DINO, RF-DETR, exported runtimes, datasets, and pretrained assets may
carry separate licenses and redistribution conditions. Before publishing
third-party or research artifacts:

1. retain all required third-party notices;
2. confirm each source dataset's license and attribution terms;
3. review the selected model's code, weights, runtime, and commercial-use terms;
4. do not describe an academic/open-source release as suitable for proprietary
   commercial deployment without a separate licensing review.

The OmDet-Turbo Tiny Hugging Face checkpoint and upstream OmDet repository
declare Apache-2.0. The project downloads that checkpoint from its upstream
source and does not include it in Git.

The demo and training-data downloaders retrieve material from the TACO dataset.
TACO annotations are distributed under CC BY 4.0, while individual images can
use different licenses recorded in the generated manifests under
`media/taco-demo/` or `data/taco-operational-v1/`. The repository does not
redistribute those images.

The optional sorting-floor demo downloader retrieves "Recycling Video" by the
Wikimedia Commons contributor Ireland4me. The video is licensed separately
under CC BY-SA 3.0 and has Wikimedia VRTS permission confirmation. It is stored
outside Git with its attribution, source URL, permission status, and checksums
in `media/demo-video/manifest.json`; the Apache-2.0 software license does not
relicense that video.
