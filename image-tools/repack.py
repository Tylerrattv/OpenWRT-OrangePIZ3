import gzip
from pathlib import Path
import struct
import subprocess
import zipfile

with zipfile.ZipFile('original.zip') as archive:
    name = next(n for n in archive.namelist() if 'orangepi-zero3' in n and 'ext4' in n and n.endswith('sdcard.img.gz'))
    original = gzip.decompress(archive.read(name))
assert original[510:512] == b'\x55\xaa'
start, sectors = struct.unpack_from('<II', original, 446 + 16 + 8)
offset, size = start * 512, sectors * 512
root = Path('rootfs.img')
root.write_bytes(original[offset:offset + size])
assert root.read_bytes()[1080:1082] == b'\x53\xef'
script = Path('image-tools/99-repeater').resolve()
subprocess.run(['sh', '-n', str(script)], check=True)
commands = Path('debugfs.commands')
commands.write_text(f'write {script} /etc/uci-defaults/99-repeater\nset_inode_field /etc/uci-defaults/99-repeater mode 0100700\n')
result = subprocess.run(['debugfs', '-w', '-f', str(commands), str(root)], capture_output=True, text=True, check=True)
print(result.stdout, result.stderr)
verify = Path('verified-firstboot')
subprocess.run(['debugfs', '-R', f'dump /etc/uci-defaults/99-repeater {verify}', str(root)], check=True)
assert verify.read_bytes() == script.read_bytes()
subprocess.run(['e2fsck', '-fn', str(root)], check=True)
# The result is for raw microSD flashing, with no stale sysupgrade metadata.
image = bytearray(original[:offset + size])
image[offset:offset + size] = root.read_bytes()
Path('ready-template.img.gz').write_bytes(gzip.compress(image, compresslevel=6, mtime=0))
print('Verified first-boot file and ext4 filesystem; template image created.')
