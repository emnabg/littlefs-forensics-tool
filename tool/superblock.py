import struct
import sys

def extract_superblock_summary(buf, default_block_size=512):
    for block_id in (0, 1):  # Try block 0 and 1
        start = block_id * default_block_size
        magic = buf[start + 8 : start + 16]
        MAGIC_OFF     = 8
        TAG201_OFF    = MAGIC_OFF + 8  # start+16 … start+19 → 0x201xxxxx
        FIELDS_OFF    = TAG201_OFF + 4 # start+20 …          → real fields
        if magic == b'littlefs':
            version, block_size, block_count, name_max, file_max, attr_max = struct.unpack_from("<IIIIII", buf, start + FIELDS_OFF)
            print(f"[SUPERBLOCK @ block {block_id}]")
            print(f"  Magic         : {magic.decode()}")
            print(f"  Version       : {version >> 16}.{version & 0xFFFF} (0x{version:08x})")
            print(f"  Block Size    : {block_size}")
            print(f"  Block Count   : {block_count}")
            print(f"  Name Max      : {name_max}")
            print(f"  File Max      : {file_max}")
            print(f"  Attr Max      : {attr_max}")
            return block_size
    raise ValueError("No valid LittleFS superblock found in block 0 or 1.")

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 superblock_summary.py <image_file> [block_size]")
        sys.exit(1)

    image_path = sys.argv[1]
    default_block_size = int(sys.argv[2]) if len(sys.argv) > 2 else 512

    with open(image_path, "rb") as f:
        buf = f.read()

    extract_superblock_summary(buf, default_block_size)

if __name__ == "__main__":
    main()

