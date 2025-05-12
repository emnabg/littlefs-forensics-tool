from littlefs import lfs

cfg = lfs.LFSConfig(block_size=512, block_count=256)
fs = lfs.LFSFilesystem()

# Format and mount the filesystem
lfs.format(fs, cfg)
lfs.mount(fs, cfg)

# Open a file and write some content
fh = lfs.file_open(fs, 'first-file.txt', 'w')
lfs.file_write(fs, fh, b'Some text to begin with\n')
lfs.file_close(fs, fh)

# Dump the filesystem content to a file
with open('FlashMemory.bin', 'wb') as fh:
    fh.write(cfg.user_context.buffer)
