#!/usr/bin/env python3
"""
step2_show_filename.py
After locating the super-block, decode the first NAME tag and show
its filename payload (14 bytes in your image).
"""

import struct, sys
from pathlib import Path

be32 = lambda b, o: struct.unpack_from(">I", b, o)[0]

def decode(tag):
    return {
        "invalid": (tag >> 31) & 1,
        "type1":   (tag >> 28) & 0x7,
        "chunk":   (tag >> 20) & 0xFF,
        "id":      (tag >> 10) & 0x3FF,
        "length":   tag        & 0x3FF,
    }

if len(sys.argv) != 2:
    sys.exit("usage: python3 step2_show_filename.py <image-file>")

buf = Path(sys.argv[1]).read_bytes()

# ── confirm magic ────────────────────────────────────────────────────────
if buf[8:16] != b"littlefs":
    sys.exit("no LittleFS magic at block 0")

# inline-struct payload starts at 0x14+4 = 0x18 and is 24 bytes long
FIRST_TAG_OFF = 0x2c                 # 0x14 + 4 + 24
raw      = be32(buf, FIRST_TAG_OFF)
prev_dec = 0x20100018                # decoded inline-struct tag
tag_word = raw ^ prev_dec
info     = decode(tag_word)

if info["type1"] != 0:
    sys.exit(f"unexpected: first post-super tag is not NAME (type1={info['type1']})")

print("First NAME tag after the super-block")
for k in ("invalid", "type1", "chunk", "id", "length"):
    print(f"  {k:7s}: {info[k]}")

name_off = FIRST_TAG_OFF + 4
name_raw = buf[name_off : name_off + info["length"]]
print(f"\nRaw filename bytes (hex): {name_raw.hex()}")
print(f"ASCII filename           : {name_raw.decode(errors='replace')}")

