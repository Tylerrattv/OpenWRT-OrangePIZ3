"""Validate classification and switch ordering with commands replaced by mocks."""
from pathlib import Path
import os
import subprocess
import tempfile

scripts = Path('image-tools').resolve()
for filename in ['99-repeater', 'repeater-auto', 'repeater-probe', 'repeater-auto.init']:
    subprocess.run(['sh', '-n', str(scripts / filename)], check=True)

# The DHCP probe must not install routes or IP addresses. An unrelated DHCP
# server must not cause us to treat a directly connected computer as Peplink.
probe = (scripts / 'repeater-probe').read_text()
with tempfile.TemporaryDirectory() as directory:
    tmp = Path(directory)
    hook = tmp / 'probe'
    marker = tmp / 'wired-offer'
    hook.write_text(probe.replace('/tmp/repeater-wired-offer', str(marker)))
    for router, subnet, ip, expected in [
        ('192.168.50.1', '255.255.255.0', '192.168.50.210', True),
        ('192.168.51.1', '255.255.255.0', '192.168.51.10', False),
        ('192.168.50.1', '255.255.0.0', '192.168.50.10', False),
        ('192.168.50.1', '255.255.255.0', '192.168.60.10', False),
    ]:
        marker.unlink(missing_ok=True)
        subprocess.run(['sh', str(hook), 'bound'], env={**os.environ, 'router': router, 'subnet': subnet, 'ip': ip}, check=True)
        assert marker.exists() is expected

    controller = tmp / 'controller'
    controller.write_text((scripts / 'repeater-auto').read_text().replace('/tmp/repeater-mode', str(tmp / 'mode')))
    checks = tmp / 'checks'
    checks.write_text('''
uci() { echo radio0; }
ifup() { echo "ifup $*"; }
ifdown() { echo "ifdown $*"; }
wifi() { echo "wifi $*"; }
ip() { echo "ip $*"; }
iw() { :; }
logger() { :; }
set -- --functions
. "$CONTROLLER"
set_wired
''')
    trace = subprocess.check_output(['sh', str(checks)], env={**os.environ, 'CONTROLLER': str(controller)}, text=True)
    assert trace.index('ifdown wwan') < trace.index('wifi down radio0') < trace.index('master br-lan') < trace.index('ifup wired')

    # If the station remains present after shutdown, Ethernet stays isolated.
    checks.write_text(checks.read_text().replace('wifi() { echo "wifi $*"; }', 'wifi() { echo "wifi $*"; return 1; }').replace('set_wired\n', 'set_wired || true\n'))
    trace = subprocess.check_output(['sh', str(checks)], env={**os.environ, 'CONTROLLER': str(controller)}, text=True)
    assert 'master br-lan' not in trace and 'ifup wired' not in trace
print('Shell syntax, DHCP classification, switch ordering, and shutdown-failure isolation checks passed.')
