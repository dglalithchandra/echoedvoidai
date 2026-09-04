# Marine Debris Sonar Detector — Master Build Reference

## How to read this
- **Order** = the sequence to work in. **Same number = you can work on them at the same time** (they don't depend on each other), whether that's you switching between them or splitting across teammates.
- **Type** tells you what kind of thing it is: dataset, model, algorithm, simulator, tool/framework, or hardware.
- **Ask AI to...** is a starting prompt you can hand an AI coding assistant for that specific piece.

---

## Stage 1 (Order 1) — Pull down every raw material
Nothing here depends on anything else. Grab all of these in parallel.

| Name | Type | Link | What it actually is | Ask AI to... |
|---|---|---|---|---|
| KD-YOLOX-ViT | Model (code + trained weights) | [github.com/remaro-network/KD-YOLOX-ViT](https://github.com/remaro-network/KD-YOLOX-ViT) | An object detector built specifically for side-scan sonar. It's a smaller "student" network trained to copy a bigger "teacher" network (that's the "knowledge distillation" part), plus a transformer layer bolted on for better feature understanding — the whole point is high accuracy in a small, fast package you can run on weak hardware. | Set up the repo environment, explain the teacher/student training loop, write a config file for a new dataset. |
| Attention U-Net | Model / Algorithm (architecture, no single official repo) | Paper: [arxiv.org/abs/1804.03999](https://arxiv.org/abs/1804.03999) · base U-Net: [arxiv.org/abs/1505.04597](https://arxiv.org/abs/1505.04597) | A segmentation network — instead of drawing a box around an object, it colors in the exact pixels that belong to it. "Attention" means it learns to focus on the relevant part of the image and ignore background clutter. Good for messy, blob-shaped debris like nets. | Implement Attention U-Net in PyTorch from the paper, or point you to a clean existing implementation and adapt it to your data format. |
| AI4Shipwrecks | Dataset + benchmark code | [umfieldrobotics.github.io/ai4shipwrecks](https://umfieldrobotics.github.io/ai4shipwrecks/) | 286 real side-scan sonar images from actual AUV surveys of shipwrecks, with pixel-level labels. The best-documented open segmentation benchmark for this exact problem. | Write a loader script and convert its label format into your unified schema. |
| SubPipe | Dataset (detection + segmentation) | Paper/data pointer: [arxiv.org/abs/2401.17907](https://arxiv.org/abs/2401.17907) | The largest open sonar object-detection dataset, originally built for pipeline inspection — same sensor, same detection task, different object shape (long pipes instead of nets/wrecks). | Convert its bounding-box annotations into COCO format matching your other datasets. |
| SWDD (+Validation +Adversarial) | Dataset (COCO-format object detection) | [zenodo.org/records/13692547](https://zenodo.org/records/13692547) | ~7,900 labeled sonar images of underwater walls, built alongside KD-YOLOX-ViT specifically to train/test it. Comes with an adversarial-robustness variant. | Write the data loader that feeds this straight into KD-YOLOX-ViT's training pipeline. |
| Marine Debris FLS / MDT | Dataset (classification, detection, segmentation) | [github.com/mvaldenegro/marine-debris-fls-datasets](https://github.com/mvaldenegro/marine-debris-fls-datasets) | The only datasets in the whole landscape actually labeled "marine debris" — bottles, pipes, platforms, propellers, tires, etc., imaged with forward-looking sonar in tanks/quarries. Your best source of real debris-class examples. | Map its 12 debris classes onto your net/pipe/cylinder/wreck taxonomy. |
| Seafloor Sediments dataset | Dataset (unlabeled/self-supervised) | [zenodo.org/records/10209445](https://zenodo.org/records/10209445) | 434,164 images of plain seafloor — rock, sand, ripples, no debris. This is your "natural clutter" negative class, critical for teaching the model what's *not* an anomaly. | Write a script to sample a balanced negative set from this for training. |
| HoloOcean | Simulator | [holoocean.readthedocs.io](https://holoocean.readthedocs.io/en/stable/) | A physics + graphics simulator (built on Unreal Engine) that can generate synthetic sonar imagery of a scene you design, including realistic sonar noise. Used when you don't have enough real data. | Write a scenario script that scatters debris-like objects on a simulated seafloor and exports sonar frames + labels automatically. |
| Stonefish | Simulator | [github.com/patrykcieslak/stonefish](https://github.com/patrykcieslak/stonefish) | Similar purpose to HoloOcean — a marine-robotics physics simulator with sonar modeling, ROS-integrated. Either this or HoloOcean is enough; you don't need both. | Same as HoloOcean — generate synthetic training frames with ground-truth labels. |
| SAM (Segment Anything) | Model (foundation model) | [github.com/facebookresearch/segment-anything](https://github.com/facebookresearch/segment-anything) | Meta's general-purpose "click or box an object, get a perfect mask" model. Not trained on sonar, but very good at turning a rough click into a clean segmentation mask on *any* image — a huge shortcut if you ever hand-label your own sonar images. | Write a labeling script: you click/box a candidate object, SAM returns the mask, you just confirm the class. |

---

## Stage 2 (Order 2) — Data engineering
Needs Stage 1's downloads in place. The two rows below don't depend on each other, so they're parallel.

| Name | Type | Link | What it actually is | Ask AI to... |
|---|---|---|---|---|
| Label-harmonization script | Custom (you build this) | — no existing tool does this | A script that reads each dataset's own labeling format (they're all different) and rewrites every label into one shared schema: `{class: net\|pipe\|cylinder\|wreck\|unknown, bbox or mask, source_dataset}`. | Write this script end-to-end once you tell it each dataset's raw label format. |
| Synthetic augmentation (HoloOcean/Stonefish + SAM + GAN/diffusion) | Model/Algorithm pipeline | CycleGAN/Pix2Pix reference: [github.com/junyanz/pytorch-CycleGAN-and-pix2pix](https://github.com/junyanz/pytorch-CycleGAN-and-pix2pix) | Using your simulator output (or SAM-labeled real images) as input to a GAN or diffusion model that makes the synthetic frames look statistically closer to real sonar noise, so the model doesn't just learn "simulator artifacts." Mainly useful for your thinnest class (usually nets). | Set up a CycleGAN training run that translates your simulated sonar frames toward the real-sonar "style" from your combined dataset. |

---

## Stage 3 (Order 3) — Model training
Needs Stage 2's harmonized/augmented dataset. The detector and the segmenter are separate models, so train them in parallel.

| Name | Type | What you're doing | Ask AI to... |
|---|---|---|---|
| KD-YOLOX-ViT fine-tuning | Model training | Fine-tune the pretrained KD-YOLOX-ViT checkpoint on your merged, harmonized dataset instead of training from zero. | Write the training config, debug loss curves, tune the knowledge-distillation temperature. |
| Attention U-Net fine-tuning | Model training | Same idea, for pixel-level segmentation instead of boxes. | Set up the training loop, pick a loss function suited to small/thin objects (e.g. Dice + focal loss for nets). |

---

## Stage 4 (Order 4) — The pieces nobody has open-sourced
The confidence layer depends on Stage 3's trained model. The report engine and dashboard don't — build them against fake/sample data while training runs, so all three happen in parallel.

| Name | Type | Link | What it actually is | Ask AI to... |
|---|---|---|---|---|
| CFAR pre-filter | Algorithm (classical, ~50 lines of code, no single canonical library) | Reference: [NSWC PCD threshold report](https://apps.dtic.mil/sti/pdfs/AD1040463.pdf) | A sliding-window statistical test: it looks at the "background" pixels around a candidate detection and checks whether the detection is a genuine statistical outlier, or just noise the network overreacted to. Runs *before* your neural net's confidence score, as a sanity filter. | Implement a standard CA-CFAR (cell-averaging CFAR) filter in Python/NumPy for your sonar image format. |
| Temperature-scaling calibration | Algorithm (small, well-documented technique) | Reference paper: [arxiv.org/abs/1706.04599](https://arxiv.org/abs/1706.04599) | Neural network confidence scores are usually overconfident. Temperature scaling is a one-parameter fix, fit on a held-out validation set, that rescales the raw score into something that's actually a trustworthy probability. | Implement temperature scaling on top of your trained detector's logits and validate the calibration curve. |
| Geotag & report engine | Custom (you build this — the identified gap) | No existing open tool | Takes a detection's pixel coordinates + the sonar log's navigation metadata (lat/long, heading, altitude at time of ping) and converts it into real-world coordinates, then writes everything to a structured JSON/CSV: location, bounding geometry, class, confidence. | Write the coordinate-fusion math and the JSON/CSV export schema, in a format that isn't locked to one sonar vendor. |
| Dashboard UI | Custom (you build this — the identified gap) | Framework: [streamlit.io](https://streamlit.io/) · Map library: [python-visualization.github.io/folium](https://python-visualization.github.io/folium/) | The upload → view → export interface. Streamlit is a fast way to build a working Python web app without frontend expertise; Folium/Leaflet draws the interactive map with your detections pinned on it. | Scaffold a Streamlit app: file upload, a Folium map with confidence-colored markers, a threshold filter slider, and a report download button. |

---

## Stage 5 (Order 5) — Integration and edge validation
Needs everything above. The two rows are independent efforts, so run them in parallel.

| Name | Type | Link | What it actually is | Ask AI to... |
|---|---|---|---|---|
| Full pipeline integration | Engineering task | — | Wiring preprocessing → detector → confidence layer → report engine → dashboard into one script/service that runs end to end on a raw sonar log. | Write the orchestration script and the error handling for a log that fails partway through. |
| ONNX Runtime + NVIDIA TensorRT export | Tool/framework | [onnxruntime.ai](https://onnxruntime.ai/) · [developer.nvidia.com/tensorrt](https://developer.nvidia.com/tensorrt) | Converts your trained PyTorch model into a format optimized to run fast on constrained hardware — this is how you actually get the "edge-ready" claim to be true rather than asserted. | Export your fine-tuned model to ONNX, then to a TensorRT engine, and benchmark latency/FPS. |
| NVIDIA Jetson | Hardware (device family) | [developer.nvidia.com/embedded/jetson-modules](https://developer.nvidia.com/embedded/jetson-modules) | The class of small, low-power GPU boards this whole field targets for onboard AUV/drone deployment. You don't need to own one to make a credible efficiency claim — profiled ONNX/TensorRT numbers plus published comparisons (e.g. RT-Seg hit 25.67 FPS on a Jetson AGX Xavier) are enough for a prototype. | Estimate expected FPS on Jetson-class hardware from your model's FLOPs/parameter count if you don't have physical access to test. |

---

## Optional / good-context reading (not build steps)
- **CIDCO ghost-gear meta-algorithm** — [arxiv.org/abs/1909.07763](https://arxiv.org/abs/1909.07763) — a classical (pre-deep-learning) approach aimed at exactly your ghost-net use case. Worth reading for design ideas, not for code.
- **S3Simulator** — [arxiv.org/abs/2408.12833](https://arxiv.org/abs/2408.12833) — shows exactly how to combine SAM + a simulator, if you want a reference implementation pattern for Stage 2.
- **RT-Seg** — [ncbi.nlm.nih.gov/pmc/articles/PMC6540040](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6540040/) — the real-time-on-Jetson proof point cited above.
