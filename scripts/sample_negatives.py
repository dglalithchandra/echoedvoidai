"""
Randomly sample 3,000 images directly out of the seafloor_sediments zip
archive into seafloor_sediments_sample/, without extracting the other
~400k images to disk.

This archive's Zip64 / central-directory metadata is corrupted in a way
that defeats both Python's zipfile (BadZipFile errors) and .NET's
ZipArchive ("Split or spanned archives are not supported", even though
this is a single physical file) -- every entry's recorded "disk number"
looks wrong. Local file headers, however, carry no disk-number field at
all, so this script ignores the central directory completely and scans
the raw byte stream for local file header signatures (PK\\x03\\x04),
reading each image's compressed data directly by offset.

After a successful sample, the original zip is deleted to free disk
space (confirmed by the user) -- only the 3,000-image sample folder is
kept.

Usage:
    python sample_negatives.py
"""

import os
import random
import struct
import zlib
from pathlib import Path

# --- config ---------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
RAW_DIR = REPO_ROOT / "data" / "raw" / "seafloor_sediments"
ZIP_PATH = RAW_DIR / "sss_ssl_dataset_N713_384.zip"
OUT_DIR = RAW_DIR / "seafloor_sediments_sample"
N_SAMPLE = 3000
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}
SEED = 42
DELETE_ZIP_AFTER = True  # user confirmed: remove the 9.3GB zip once the sample is verified
CHUNK_SIZE = 64 * 1024 * 1024  # 64MB scan chunks
# ---------------------------------------------------------------------------

LOCAL_SIG = b"PK\x03\x04"
# fields AFTER the 4-byte signature, little-endian:
# version_needed(H) flags(H) method(H) mod_time(H) mod_date(H)
# crc32(L) comp_size(L) uncomp_size(L) fname_len(H) extra_len(H)
LOCAL_FMT = "<HHHHHLLLHH"
LOCAL_FIXED_SIZE = struct.calcsize(LOCAL_FMT)  # 26 bytes
LOCAL_HEADER_TOTAL = 4 + LOCAL_FIXED_SIZE      # 30 bytes


def _looks_like_name(raw):
    try:
        name = raw.decode("utf-8")
    except UnicodeDecodeError:
        try:
            name = raw.decode("cp437")
        except UnicodeDecodeError:
            return None
    if not name or "\x00" in name:
        return None
    if any(ord(c) < 0x20 for c in name):
        return None
    return name


def scan_entries(path, progress=True):
    """
    Sequentially scan the file for local file header signatures and return
    a list of dicts describing each *image* entry found:
    {name, offset, comp_size, uncomp_size, method}.
    Entries whose size can't be determined up front (streamed / data-
    descriptor style headers) are skipped, with a count reported.
    """
    entries = []
    skipped_unknown_size = 0
    file_size = path.stat().st_size
    overlap = len(LOCAL_SIG) - 1
    next_report = 512 * 1024 * 1024

    with open(path, "rb") as f:
        pos = 0
        tail = b""
        while True:
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break
            buf = tail + chunk
            buf_base = pos - len(tail)
            search_from = 0
            while True:
                idx = buf.find(LOCAL_SIG, search_from)
                if idx == -1:
                    break
                abs_pos = buf_base + idx

                if idx + LOCAL_HEADER_TOTAL <= len(buf):
                    fixed = buf[idx + 4: idx + LOCAL_HEADER_TOTAL]
                else:
                    f.seek(abs_pos + 4)
                    fixed = f.read(LOCAL_FIXED_SIZE)
                    f.seek(pos + len(chunk))

                if len(fixed) != LOCAL_FIXED_SIZE:
                    search_from = idx + 1
                    continue

                (version, flags, method, mtime, mdate, crc32,
                 comp_size, uncomp_size, fname_len, extra_len) = struct.unpack(LOCAL_FMT, fixed)

                name = None
                if 0 < fname_len <= 260:
                    name_start = idx + LOCAL_HEADER_TOTAL
                    name_end = name_start + fname_len
                    if name_end <= len(buf):
                        name_raw = buf[name_start:name_end]
                    else:
                        f.seek(abs_pos + LOCAL_HEADER_TOTAL)
                        name_raw = f.read(fname_len)
                        f.seek(pos + len(chunk))
                    name = _looks_like_name(name_raw)

                if name and not name.endswith("/"):
                    ext = os.path.splitext(name)[1].lower()
                    if ext in IMAGE_EXTS:
                        data_offset = abs_pos + LOCAL_HEADER_TOTAL + fname_len + extra_len
                        has_data_descriptor = bool(flags & 0x08)
                        if comp_size == 0 and has_data_descriptor:
                            skipped_unknown_size += 1
                        elif data_offset + comp_size <= file_size:
                            entries.append({
                                "name": name,
                                "offset": data_offset,
                                "comp_size": comp_size,
                                "uncomp_size": uncomp_size,
                                "method": method,
                            })

                search_from = idx + 1

            tail = buf[-overlap:] if overlap and len(buf) >= overlap else buf
            pos += len(chunk)
            if progress and pos >= next_report:
                print(f"  scanned {pos / 1e9:.1f} / {file_size / 1e9:.1f} GB, "
                      f"{len(entries)} images found so far")
                next_report += 512 * 1024 * 1024

    if skipped_unknown_size:
        print(f"  ({skipped_unknown_size} entries had streamed/unknown sizes and were skipped)")
    return entries


def extract_entry(f, entry, dest_path):
    f.seek(entry["offset"])
    data = f.read(entry["comp_size"])
    if entry["method"] == 0:
        payload = data
    elif entry["method"] == 8:
        payload = zlib.decompressobj(-15).decompress(data)
    else:
        raise ValueError(f"Unsupported compression method {entry['method']} for {entry['name']}")
    dest_path.write_bytes(payload)


def main():
    if not ZIP_PATH.exists():
        raise SystemExit(f"Zip not found: {ZIP_PATH}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Scanning {ZIP_PATH.name} for image entries (raw scan, ignoring the broken central directory)...")
    entries = scan_entries(ZIP_PATH)
    print(f"Found {len(entries)} image entries")

    if not entries:
        raise SystemExit("No image entries found -- the scan didn't turn up anything, stopping without touching the zip.")

    if len(entries) < N_SAMPLE:
        print(f"WARNING: only {len(entries)} images available, sampling all of them")

    random.seed(SEED)
    sample = random.sample(entries, min(N_SAMPLE, len(entries)))
    target = len(sample)

    with open(ZIP_PATH, "rb") as f:
        for i, entry in enumerate(sample, 1):
            filename = os.path.basename(entry["name"])
            dest = OUT_DIR / filename
            if dest.exists():
                stem, ext = os.path.splitext(filename)
                dest = OUT_DIR / f"{stem}_{i}{ext}"
            try:
                extract_entry(f, entry, dest)
            except Exception as e:
                print(f"  skipping {entry['name']}: {e}")
                continue
            if i % 250 == 0 or i == target:
                print(f"  copied {i}/{target}")

    copied = len(list(OUT_DIR.iterdir()))
    print(f"Done. {copied} images written to {OUT_DIR}")

    if copied < target * 0.95:
        print("Sample looks incomplete -- leaving the zip in place, please check manually.")
        return

    if DELETE_ZIP_AFTER:
        size_gb = ZIP_PATH.stat().st_size / 1e9
        print(f"Removing source zip ({size_gb:.1f} GB): {ZIP_PATH}")
        ZIP_PATH.unlink()
        print("Zip deleted. Only seafloor_sediments_sample/ remains in this folder.")


if __name__ == "__main__":
    main()
