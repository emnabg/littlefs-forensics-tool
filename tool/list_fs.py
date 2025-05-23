
"""
list_fs.py  –  LittleFS image inspector
========================================================

A minimal forensic helper that **mounts an existing LittleFS disk image held in
ordinary storage**, prints the directory tree, and (optionally) dumps file
contents to stdout.

Why a dedicated script?
-----------------------
* The high‑level *littlefs‑python* wrapper (≥0.13) hides all the low‑level
  callbacks—you just drop the binary into an internal buffer and call
  `fs.mount()`.
* Older examples you’ll find on blogs often call `fs_configure()` or pass an
  extra buffer to `lfs.mount()`. Those APIs were **removed**; this script uses
  the supported approach and will stay forward‑compatible.

Usage
-----
```bash
pip install littlefs-python         # once
python forensic_analysis_littlefs.py image.lfs            # tree only
python forensic_analysis_littlefs.py image.lfs -c         # tree + contents
python forensic_analysis_littlefs.py image.lfs -b 1024    # custom block size
```

Options
~~~~~~~
*image – path to the *.lfs* binary image.
*-c/--contents  – print each file’s raw bytes (UTF‑8 decoded if possible).
*-b/ --block-size – override the default *512 B* erase‑block size if your
  image was built with something else.( if the block_size of your image is 1024 for example you can just pass the argument -b 1024 and it will work)

Limitations
~~~~~~~~~~~
* The script assumes the **entire filesystem resides in RAM** (forensics on a
  copy, never the live evidence!).  For a terabyte‑scale dump you’d want to
  stream blocks through a custom device callback instead.
* It prints to stdout; pipe to `less -R` or redirect to a report file in real
  investigations.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import List

try:
    from littlefs import LittleFS
except ModuleNotFoundError as exc:
    sys.exit("littlefs-python not found. Install with:  pip install littlefs-python")

# ──────────────────────────────────────────────────────────────────────────────
# Helper functions
# ──────────────────────────────────────────────────────────────────────────────

def _print_tree(fs: "LittleFS", path: str = "/", indent: str = "") -> None:
    """Recursively pretty‑print the directory structure."""
    """
    fs:the mounted LittleFS object.
    path:the directory we’re currently listing (defaults to root /
    indent – the running prefix ('') that keeps the tree aligned as we go deeper)(to have the nice structure)
    """
    #fs.listdir(path) returns a list of entry names (files + sub-dirs).
    #sorted() makes the output deterministic across runs.
    entries: List[str] = sorted(fs.listdir(path))
    #enumerate() gives us both index and name so we can tell whether we’re on the last entry.
    for idx, name in enumerate(entries):
        #full is the absolute LittleFS path (e.g. /config/system.conf).
        full = os.path.join(path, name).replace("//", "/")
        """
        lfs.stat() ret a tuple like record (type, size, name) ( equivalent to struct lfs_info in the C side ) 
        In LittleFS, type values are:
             0 – file
             2 – directory
        (Matches the enum lfs_type in the C headers.)
        """
        stat = fs.stat(full)
        is_dir = stat.type == 2  # 2 == LFS_TYPE_DIR in public headers

        branch = "└── " if idx == len(entries) - 1 else "├── "
        child_indent = "    " if idx == len(entries) - 1 else "│   "
        print(f"{indent}{branch}{name}{'/' if is_dir else ''}")

        if is_dir:
            _print_tree(fs, full, indent + child_indent)


def _dump_files(fs: "LittleFS") -> None:
    """Iterate every file and dump its contents (best‑effort UTF‑8)."""
    """i
    fs.walk() is LittleFS’ iterator that mimics Python’s os.walk. : 1) the current directory path (root), 2) a list    of sub-directory names 3) a list of plain-file names.
    """
    for root, _dirs, files in fs.walk("/"):
        for fname in files:
            full_path = os.path.join(root, fname).replace("//", "/")
            with fs.open(full_path, "rb") as fh:
                #Fine for small embedded images; for multi-MB logs you might prefer chunked reads.
                data = fh.read()
            try:
                #Any valid UTF-8 file (config, logs, JSON, source code) prints human-readable.
                text = data.decode("utf-8")
            except UnicodeDecodeError:
                #f decoding fails, we avoid spewing binary to the console and note its presence.
                text = "[binary data omitted]"
                """
                Output looks like:
                --- /logs/boot.log (34 bytes) ---<newline>Boot successful…
                """
            print(f"\n--- {full_path}  ({len(data)} bytes) ---\n{text}")


# ──────────────────────────────────────────────────────────────────────────────
# Main driver
# ──────────────────────────────────────────────────────────────────────────────

def main(argv: List[str] | None = None) -> None:
    """ Creates an argument parser. The description text appears when the user runs script.py -h, giving a one sentence overview."""
    parser = argparse.ArgumentParser(
        description="Mount and inspect a LittleFS image file")
    #Adds the required positional argument image
    parser.add_argument("image", type=Path, help="Path to .lfs binary image")
    """
    Adds an optional flag that becomes a boolean.
    - If -c or --contents is present → args.contents is True; otherwise False.
    - Meant for cases where you want to print each file’s contents in addition to the tree.
    """
    parser.add_argument("-c", "--contents", action="store_true",
                        help="Dump file contents as well as directory tree")
    """
    Another optional flag.
    Accepts an integer (type=int).
    Defaults to 512 if the user doesn’t override it (-b 1024)
    """
    parser.add_argument("-b", "--block-size", type=int, default=512,
                        help="Erase block size in bytes (default: 512)")
    args = parser.parse_args(argv)

    # 1) Read entire image into RAM (immutable forensic copy!)
    #Loads a forensic duplicate of the evidence into a mutable bytearray
    try:
        buf = bytearray(args.image.read_bytes())
    except FileNotFoundError:
        sys.exit(f"Error: image '{args.image}' not found")

    # 2) Derive geometry & sanity‑check
    #Verifies the image length is an exact multiple of the erase-block size the user supplied with -b
    if len(buf) % args.block_size != 0:
        sys.exit("Image size is not a multiple of block size – check -b value")
    block_count = len(buf) // args.block_size

    # 3) Build FS but don’t auto‑mount (mount=False)
    #Creates a LittleFS instance without mounting yet.
    fs = LittleFS(block_size=args.block_size,
                  block_count=block_count,
                  mount=False)

    # 4) Inject the image into the internal flash buffer
    fs.context.buffer[:] = buf

    # 5) Mount & bail if it fails (non‑zero return)
    if fs.mount() != 0:
        sys.exit("Failed to mount image – invalid super‑block or wrong geometry")
    print(f"Mounted '{args.image}' ({len(buf)//1024} KiB, {block_count} blocks)\n/")
    _print_tree(fs)

    if args.contents:
        _dump_files(fs)

    fs.unmount()


if __name__ == "__main__":
    main()

