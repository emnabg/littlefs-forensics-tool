#!/usr/bin/env python3
"""
recover_to_be_deleted.py
Extract the inline data for any file from a LittleFS-v2 image,
even if the commit lacks a CRC.

Usage:
    python3 recover_to_be_deleted.py <image.bin> <filename>
"""
import struct
import sys
import pathlib

# Size of each erase block in bytes (must match the image's geometry)
BLOCK_SIZE = 512

# Helper to read a big-endian 32-bit integer from `buf` at offset `o`
be32 = lambda b, o: struct.unpack_from(">I", b, o)[0]
# Helper to align a length up to the next multiple of 4
align4 = lambda n: (n + 3) & ~3

# Decode a 32-bit tag word into its LittleFS fields
def decode(w):
    return {
        "inv": (w >> 31) & 1,        # invalid flag (stop if set)
        "typ": (w >> 28) & 0x7,      # abstract type: 0=NAME,2=STRUCT,4=DELETE,5=CRC,6=TAIL
        "chk": (w >> 20) & 0xFF,     # chunk: sub-type (e.g. file/dir inline/ctz)
        "id":  (w >> 10) & 0x3FF,    # object ID (inode-like)
        "ln":   w         & 0x3FF,    # payload length in bytes
    }


def main():
    # Expect exactly two arguments: image file path and target filename
    if len(sys.argv) != 3:
        sys.exit("usage: python3 recover_to_be_deleted.py <image.bin> <filename>")

    img_path = sys.argv[1]
    # Convert the target filename to bytes for exact comparison
    target   = sys.argv[2].encode("utf-8")

    # Read the entire image into memory
    buf = pathlib.Path(img_path).read_bytes()

    # Iterate over each block in the image
    for blk_idx in range(len(buf) // BLOCK_SIZE):
        blk = buf[blk_idx * BLOCK_SIZE : (blk_idx + 1) * BLOCK_SIZE]
        # 'pos' is the offset within the block where the next tag starts
        # Start at 4 to skip the 4-byte revision counter at the block's beginning
        pos, xor = 4, 0xFFFFFFFF

        # Walk through tags until we reach the end of the block
        while pos + 4 <= BLOCK_SIZE:
            # Read the raw stored tag word
            stored = be32(blk, pos)
            # Decode it by XORing with the previous decoded tag
            tag    = stored ^ xor
            f      = decode(tag)
            # Update xor for the next iteration
            xor    = tag

            # If the invalid flag is set, no more tags here
            if f["inv"]:
                break

            # Check if this is a NAME tag
            if f["typ"] == 0:
                # Extract the filename bytes from the payload
                name_bytes = blk[pos + 4 : pos + 4 + f["ln"]]
                # Compare to the target (ignoring trailing NULs)
                if name_bytes.rstrip(b"\0") == target:
                    name_str = name_bytes.rstrip(b"\0").decode("utf-8")
                    print(f"Found NAME tag in block {blk_idx}, offset 0x{pos:04X}")
                    print(" file name =", name_str)

                    # Compute the absolute offset where inline data begins
                    data_start = (
                        blk_idx * BLOCK_SIZE
                        + pos     # tag start
                        + 4       # skip the 4-byte tag header
                        + align4(f["ln"])  # skip the filename + padding
                    )

                    # Carve bytes until the next 0xFF (erased) marker
                    end = data_start
                    while end < len(buf) and buf[end] != 0xFF:
                        end += 1
                    data = buf[data_start:end]

                    # Write the recovered data to a local file
                    out_path = pathlib.Path(f"recovered_{name_str}")
                    out_path.write_bytes(data)
                    print(f"Recovered {len(data)} bytes → {out_path}")
                    return

            # Move to the next tag: 4-byte header + payload padded to 4
            pos += 4 + align4(f["ln"])

    # If we finish the loops with no match, report not found
    print(f"Filename '{sys.argv[2]}' not found in image")

if __name__ == "__main__":
    main()

