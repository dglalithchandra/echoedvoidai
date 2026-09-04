# Day 1 Sprint: Stage 1 + Stage 2 (finalized 6-class taxonomy)

Classes: **1 net/entangled gear · 2 pipe/cable · 3 drum/container · 4 wreck/large structure · 5 small rigid debris (misc) · 6 unknown/anomaly**

## Tool allocation strategy

| Tool | What it's actually good for here | Use it for |
|---|---|---|
| **Cursor Pro** | Works directly inside your codebase with full file/repo context, runs and iterates on real code | Cloning repos, resolving dependency errors, running training/inference scripts, debugging against real files |
| **Claude Pro** | Reads dense docs/papers fast, writes one large coherent script or schema correctly in a single pass, good at reasoning through tricky logic (label mapping, coordinate math) | Designing the harmonization schema, writing the harmonization script itself, architecture decisions |
| **Free Claude / free ChatGPT accounts** | Disposable, parallel, single-purpose — no need to protect context or history | One account per dataset: "read this dataset's README/paper and tell me its exact label format." Run 3–4 of these at once instead of doing it serially in your main tool |

**Two-person split**, running in parallel all day:
- **Person A + Cursor Pro** = the "build" track — environments, code, running things
- **Person B + Claude Pro + free accounts** = the "data" track — downloading, reading docs, harmonizing labels

---

## STAGE 1 (Order 1) — do all of this in parallel, this morning

### 1. KD-YOLOX-ViT — Person A, Cursor Pro
- **Type:** Model (code + pretrained weights)
- **Link:** https://github.com/remaro-network/KD-YOLOX-ViT
- **Download:**
  ```
  git clone https://github.com/remaro-network/KD-YOLOX-ViT.git
  cd KD-YOLOX-ViT
  pip install -r requirements.txt
  ```
  Then open the README's weights table and download **one** checkpoint — pick **Nano-ViT** (smallest, fastest to test today). Save it as `weights/kd_yolox_vit_nano.pth`. Note: these weights were trained on wall-detection data (SWDD), not your 6 classes — they're a sonar-adapted starting point, not a finished model.
- **Ask Cursor:** "Set up this repo's environment, resolve dependency errors, and get the inference script running on one sample SWDD image so we confirm the checkpoint loads correctly."
- **You end up with:** a working local environment that can run a sonar detector, ready to be re-pointed at your own data later.

### 2. Attention U-Net — Person A, Cursor Pro
- **Type:** Model/algorithm (code)
- **Link:** https://github.com/LeeJunHyun/Image_Segmentation
- **Download:**
  ```
  git clone https://github.com/LeeJunHyun/Image_Segmentation.git
  ```
- **Ask Cursor:** "Adapt this Attention U-Net implementation's data loader to accept single-channel grayscale sonar images instead of the 3-channel medical images it was built for."
- **You end up with:** segmentation model code ready, untrained — this is your net-segmentation candidate for later, since nets are irregular blobs better captured by a pixel mask than a box.

### 3. AI4Shipwrecks — Person B, Claude Pro → covers class 4 (wreck)
- **Type:** Dataset
- **Link:** project page https://umfieldrobotics.github.io/ai4shipwrecks/ → actual download at https://deepblue.lib.umich.edu/data/concern/data_sets/8623hz41x
- **Download:** Open the Deep Blue Data page, click the download button — it delivers a zip. Unzip into `data/ai4shipwrecks/`; you'll get `images/`, `labels/` (binary label PNGs), and a `README.txt`.
- **Ask Claude Pro:** "Read this README's label format description and write a Python loader that yields (image, mask) pairs from this folder structure."
- **You end up with:** 286 wreck-labeled sonar images.

### 4. SubPipe — Person B or a free account → covers class 2 (pipe)
- **Type:** Dataset
- **Link:** https://github.com/remaro-network/subpipe-dataset
- **Download:** README has the actual dataset link; it's split into 5 chunks. **Download only Chunk0 today** to move fast — inside it, use `SSS_HF_images/YOLO_Annotation/*.txt` (already in YOLO format, matching what KD-YOLOX-ViT expects).
- **Ask AI:** "Write a script that filters these YOLO annotations to just the pipe objects and remaps the class ID to index 1 (pipe/cable) in our unified schema."
- **You end up with:** pipe-labeled sonar images in YOLO format.

### 5. SWDD — Person B or a free account → NOT a debris class, use as a sanity-check set only
- **Type:** Dataset
- **Link:** https://zenodo.org/records/13692547
- **Download:** direct zip from Zenodo, unzip into `data/swdd/`.
- **Note:** this is wall-detection data. Don't spend time mapping it into your 6 classes — its only job today is letting you confirm the KD-YOLOX-ViT checkpoint actually runs correctly (task 1 above uses it for exactly that).

### 6. Marine Debris FLS/MDT — Person B or a free account → covers class 5 (small rigid debris)
- **Type:** Dataset
- **Link:** https://github.com/mvaldenegro/marine-debris-fls-datasets/releases
- **Download:** on the Releases page, grab the **watertank-v1.0** asset (zip). Contains full sonar PNGs plus a JSON with bounding boxes for bottle/can/chain/drink-carton/hook/propeller/shampoo-bottle/standing-bottle/tire/valve.
- **Ask AI:** "Write a script mapping all 10 of these fine classes into our single class 5 (small_rigid_debris), keeping the original fine label as a metadata field in case we need it later."
- **You end up with:** small-debris data, all 10 fine labels collapsed into one class.

### 7. Seafloor Sediments — Person B or a free account → negative/background class
- **Type:** Dataset
- **Link:** https://zenodo.org/records/10209445
- **Download:** direct from Zenodo. It's large (434,164 images) — don't wait for the whole thing.
- **Ask AI:** "Write a random-sampling script that pulls 2,000–5,000 images from this set for a first training run — we'll use the rest later."
- **You end up with:** a manageable negative-class sample.

### 8. SAM — whoever's free, lowest priority today
- **Type:** Model (foundation model, for labeling)
- **Link:** https://github.com/facebookresearch/segment-anything
- **Download:**
  ```
  pip install git+https://github.com/facebookresearch/segment-anything.git
  wget https://dl.fbaipublicfiles.com/segment_anything/sam_vit_b_01ec64.pth
  ```
  (Using **ViT-B**, 375MB — not ViT-H's 2.4GB — you don't need max accuracy today, just speed.)
- **Only do this today if** you have real net/gear imagery to hand-label (see the gap note below). Otherwise skip and revisit later.

### Skip today: HoloOcean / Stonefish
Both require multi-gigabyte simulator downloads, and HoloOcean's newer install docs indicate their installation method has recently changed (their latest documentation says it's no longer distributed via pypi the way older versions were) — exactly the kind of setup issue that can eat your whole afternoon. Push synthetic data generation to day 2, once the real-data pipeline is proven.

---

## The one real gap in Stage 1: nobody has an open "net" dataset

None of the datasets above contain a labeled fishing-net/ghost-gear class — this matches the gap flagged earlier. For today, pick one:
- **Realistic path:** proceed without net examples today, get the other 5 classes harmonized and sanity-checked, treat net-detection as a day-2 problem (synthetic generation via HoloOcean, or sourcing/hand-labeling real footage).
- **Stretch goal, only if there's spare time:** if either of you has access to any real ghost-net/ROV footage (even stock/YouTube clips of net removal), grab a handful of frames and use SAM (task 8) to mask-label 20–30 examples today. That's enough to bootstrap class 1 for a first pass.

---

## STAGE 2 (Order 2) — this afternoon, needs Stage 1's downloads in place

Both items below are independent of each other — run them in parallel.

### 1. Label-harmonization script — Person B drafts with Claude Pro, Person A runs/debugs with Cursor Pro
- **Ask Claude Pro:** "Write one Python script that reads AI4Shipwrecks binary masks, SubPipe YOLO labels, and the Marine Debris FLS JSON, and outputs one unified COCO-format annotation file with 6 classes: net, pipe, drum, wreck, small_debris, unknown." Feed it the exact label-format details Person B already pulled from each dataset's README in Stage 1.
- **Then hand the script to Cursor Pro** to actually run against your real downloaded files and fix the inevitable real-world snags (path mismatches, encoding, off-by-one class IDs) — this is exactly the "iterate against real code" work Cursor is best at.
- **You end up with:** one merged `annotations_unified.json` covering classes 2, 4, and 5 (pipe, wreck, small debris).

### 2. Visual sanity check — a free Claude or ChatGPT account, in parallel
- **Ask it:** "Write a short script that plots 10 random samples from the merged annotation file with their boxes/masks drawn, so we can visually confirm the harmonization worked before training starts."
- **You end up with:** visual proof the merge is correct, before you waste tomorrow's training run on bad labels.

---

## If there's time left today
- **Lock the class-ID mapping in writing** right now, in one shared doc, so nobody's script disagrees later: `0=net, 1=pipe, 2=drum, 3=wreck, 4=small_debris, 5=unknown`.
- **Count examples per class** after harmonizing. Anything under ~50–100 examples tells you tomorrow's real priority — almost certainly net (class 1), given the gap above.
- **Set up one shared repo** (private GitHub repo or shared drive) now, since you're running two parallel tracks — Person A's code and Person B's data need to land in the same place by end of day.
- **Run one inference pass** with the KD-YOLOX-ViT checkpoint on a SWDD sample image (task 1) — this is your proof that the whole toolchain actually works before you commit to training on the new merged dataset tomorrow.
