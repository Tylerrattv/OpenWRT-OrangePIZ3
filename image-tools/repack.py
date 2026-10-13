import gzip
import hashlib
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
subprocess.run(['python3', 'image-tools/check-policy.py'], check=True)
# Inspect the existing root and check the exact ARM relayd binary against its
# installed loader and libraries, rather than replacing unrelated core packages.
Path('root-tree').mkdir()
subprocess.run(['debugfs', '-R', 'rdump / root-tree', str(root)], check=True)
relayd = Path('relay-package/usr/sbin/relayd')
assert relayd.is_file()
subprocess.run(['readelf', '-h', str(relayd)], check=True)
probe = subprocess.run(['qemu-aarch64', '-L', 'root-tree', str(relayd), '-h'], capture_output=True, text=True)
assert 'Usage:' in probe.stderr or 'Usage:' in probe.stdout, probe.stderr
files = {
    '/etc/uci-defaults/99-repeater': script,
    '/usr/sbin/repeater-auto': Path('image-tools/repeater-auto').resolve(),
    '/usr/lib/repeater-probe': Path('image-tools/repeater-probe').resolve(),
    '/etc/init.d/repeater-auto': Path('image-tools/repeater-auto.init').resolve(),
    '/usr/sbin/relayd': relayd.resolve(),
}
commands = Path('debugfs.commands')
lines = []
for dest, src in files.items():
    lines += [f'write {src} {dest}', f'set_inode_field {dest} mode 0100755']
lines.append('symlink /etc/rc.d/S95repeater-auto ../init.d/repeater-auto')
commands.write_text('\n'.join(lines) + '\n')
result = subprocess.run(['debugfs', '-w', '-f', str(commands), str(root)], capture_output=True, text=True, check=True)
print(result.stdout, result.stderr)
for index, (dest, src) in enumerate(files.items()):
    verify = Path(f'verified-{index}')
    subprocess.run(['debugfs', '-R', f'dump {dest} {verify}', str(root)], check=True)
    assert verify.read_bytes() == src.read_bytes()
subprocess.run(['e2fsck', '-fn', str(root)], check=True)
# The result is for raw microSD flashing, with no stale sysupgrade metadata.
image = bytearray(original[:offset + size])
image[offset:offset + size] = root.read_bytes()
Path('ready-template.img.gz').write_bytes(gzip.compress(image, compresslevel=6, mtime=0))
print('Verified first-boot file and ext4 filesystem; template image created.')
