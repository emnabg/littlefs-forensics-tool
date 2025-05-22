#!/usr/bin/env python3
import struct, sys
from pathlib import Path

BLOCK_SIZE = 512                  # real geometry
# decodes a 32-bit metadata tag into its fields, using bit manipulation based on the tag layout
def decode(tag):
    return {
        "inv": (tag>>31)&1,
        "typ": (tag>>28)&7,
        "chk": (tag>>20)&0xFF,
        "id" : (tag>>10)&0x3FF,
        "len":  tag      &0x3FF
    }
#tag names(type1)
TNAME = {0:"NAME", 2:"STRUCT", 4:"DELETE", 5:"CRC", 6:"TAIL"}

def scan(block, bid):
    off, xor = 4, 0xFFFFFFFF      # skip revision u32 and initial value for decoding tags
    while off+4 <= BLOCK_SIZE:    #Iterates over the block
        stored = struct.unpack_from(">I", block, off)[0] # Reads 4 bytes in big endian
        tag    = stored ^ xor #XORs with xor from previous tag to get real tag (xor-chaining)
        f      = decode(tag)
        if f["inv"]: break
        xor = tag #Update xor with this tag’s value (so the next tag gets decoded correctly)

        if off+4+f["len"] > BLOCK_SIZE: break
        payload = block[off+4: off+4+f["len"]]

        print(f"[blk {bid:3d}] +{off:04X}: {TNAME.get(f['typ'],'?'):<6}"
              f" id={f['id']:3d} len={f['len']:3d} chk=0x{f['chk']:02X}")
        #Decode payload by tag type
        if f["typ"]==0:                               # NAME
            print("           └─",
                  payload.rstrip(b'\0').decode(errors='replace'))
        elif f["typ"]==2 and f["len"]>=8:              # STRUCT
            head,size = struct.unpack_from("<II", payload)
            kind = "inline" if f["chk"]==1 else "ctz"
            print(f"           └─ {kind} head=0x{head:08X} size={size}")
        off += 4 + ((f["len"]+3)&~3) #4 bytes for tag and Add padded len (aligns to next 4-byte boundary)

def main(img):
    buf = Path(img).read_bytes()
    for i in range(len(buf)//BLOCK_SIZE):
        blk = buf[i*BLOCK_SIZE:(i+1)*BLOCK_SIZE]
        if blk[8:16]==b"littlefs":
            print(f"\n=== BLOCK {i} (super-block) ===")
        scan(blk,i)

if __name__=="__main__":
    if len(sys.argv)!=2:
        sys.exit("usage: python3 scan.py FlashMemory.bin")
    main(sys.argv[1])

