from littlefs import lfs

# Filesystem config
cfg = lfs.LFSConfig(block_size=512, block_count=256)
fs = lfs.LFSFilesystem()

# Format and mount the filesystem
lfs.format(fs, cfg)
lfs.mount(fs, cfg)

# -- Root file --
fh = lfs.file_open(fs, "first-file.txt", "w")
lfs.file_write(fs, fh, b"This is the root file\n")
lfs.file_close(fs, fh)

# -- Create config/ directory and files --
lfs.mkdir(fs, "config")

fh = lfs.file_open(fs, "config/system.conf", "w")
lfs.file_write(fs, fh, b"system=true\nversion=2.0\n")
lfs.file_close(fs, fh)

fh = lfs.file_open(fs, "config/network.conf", "w")
lfs.file_write(fs, fh, b"ip=192.168.1.1\nmask=255.255.255.0\n")
lfs.file_close(fs, fh)

# -- Create logs/ directory and file --
lfs.mkdir(fs, "logs")

fh = lfs.file_open(fs, "logs/boot.log", "w")
lfs.file_write(fs, fh, b"Boot successful at 12:34PM\n")
lfs.file_close(fs, fh)

# -- Create temp/ directory and delete a file --
lfs.mkdir(fs, "temp")

fh = lfs.file_open(fs, "temp/to-be-deleted.txt", "w")
lfs.file_write(fs, fh, b"This file will be deleted\n")
lfs.file_close(fs, fh)


lfs.remove(fs, "temp/to-be-deleted.txt")
# Unmount filesystem
lfs.unmount(fs)

# Dump binary image
with open("Flashmemory.bin", "wb") as out:
    out.write(cfg.user_context.buffer)

