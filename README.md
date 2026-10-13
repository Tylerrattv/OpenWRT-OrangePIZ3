# Orange Pi Zero 3: OpenWrt with two Wi-Fi radios

Manual GitHub Actions build for an Orange Pi Zero 3 (including the 1 GB model),
using AW859A/UWE5622 onboard Wi-Fi and a MediaTek MT7921AU USB adapter.

**Status: build files prepared; no Actions compilation or hardware test has been
performed yet.** The onboard driver is a community port, with reported Zero 3
success, rather than official upstream support. A successful build still needs
boot, association, AP, and reboot testing on your board.

## Create your repository and run the build

1. Create an empty GitHub repository, e.g. `orangepi-zero3-openwrt`.
2. Extract this folder and upload its **contents** to the repository root.
   Include the hidden `.github` folder; `build.yml` must end up at
   `.github/workflows/build.yml`, not inside another enclosing folder.
   Using Git to push the folder is the most reliable way to include hidden files.
3. Open **Actions**, enable workflows if prompted, select **Build Orange Pi Zero 3**,
   then **Run workflow**. No secrets or credentials are required.
4. Wait for the job to finish. The first build can take several hours and is subject
   to your account's Actions limits. This workflow does not publish a release.
5. Download the artifact from the completed run. It includes firmware, checksums,
   the resolved build configuration, source revisions, and build logs. Failed builds
   also upload available logs; do not flash anything from a failed run.

## Sources and build choices

- OpenWrt **25.12.0**, commit `4da53efc2fe744601e6189492dbd06b8930d72b8`.
  The release's `feeds.conf.default` already pins feed revisions.
- Community Wi-Fi port: `Anieake/openwrt-orangepi-zero2-zero3-wifi-modem`, commit
  `b4b1d4c4abc88d055ca99f51e11d9ebafccf4680`, based on DeepAQ's UWE5622 port.
- Only UWE5622 wireless integration, its firmware package, and the board Wi-Fi
  device-tree patch are imported. Unrelated modem, GPU, HDMI, and board patches
  are excluded.
- `kmod-mt7921u`, MT7921 firmware, `wpad-mbedtls`, LuCI, and diagnostic tools.
- The vendor driver's compiler warnings remain visible, but do not fail its build.
  This workaround is inherited by driver subdirectories and survives clean builds.
- No Wi-Fi passwords are embedded. Radios retain OpenWrt's initial disabled state.
- Source versions are pinned for repeatability. The runner and Actions major versions
  can change; this is not a claim of byte-for-byte reproducibility or latest security fixes.
  Updating OpenWrt requires rechecking the kernel and driver patch compatibility.

## Flash and first boot

Use the image containing **`orangepi-zero3`**, not Zero 2 or Zero 2W.
The build produces ext4 and squashfs microSD images. Start with the
`squashfs-sdcard.img.gz` image if present; it supports OpenWrt's usual writable
overlay/reset behavior. The filename can include `sysupgrade`: for first install,
write the complete decompressed `.img` to the microSD with a disk imaging tool.

Writing the image erases the selected card. Verify the image against the supplied
`sha256sums` before flashing. Connect the board's Ethernet directly to your PC for
initial setup, then browse to `http://192.168.1.1`. Set a root password. If your
existing network uses that subnet, keep the board isolated until changing its LAN.

## Configure the repeater

The suggested arrangement is a **routed Wi-Fi repeater**:

```text
Existing router <-- Wi-Fi --> onboard AW859A [Wi-Fi WAN]
                                      Orange Pi
PCs/phones     <-- Wi-Fi --> USB MT7921AU [LAN access point]
Wired devices  <-- Ethernet ------------ [LAN]
```

This creates a separate LAN and uses NAT. Devices behind the Orange Pi have
internet access, but discovery/casting from the upstream network may not cross
the router. If you need every device on the existing router's subnet, configure
WDS only if both ends support it, or evaluate OpenWrt's relayd approach separately.
Ordinary Wi-Fi client mode cannot simply be bridged into Ethernet LAN.

1. In LuCI, change LAN to an unused subnet, for example `192.168.50.1/24`
   **only if it does not overlap the upstream network**. Keep LAN DHCP enabled.
   Reconnect at the new address.
2. Identify radios in **Network > Wireless**. Do not assume `radio0` or `wlan0`
   always refers to the onboard chip. `iw phy`, `iw dev`, `lsusb`, and `dmesg`
   help identify each device; USB hardware appears under a USB path.
3. Set the correct country for your actual location on both radios.
4. On the onboard radio, scan and join your existing router using its SSID and
   password. Create a DHCP-client network named `wwan` and assign it to the
   existing **wan** firewall zone. The zone should have masquerading enabled and
   forwarding from **lan** to **wan**.
5. On the MT7921AU radio, add an **Access Point** attached to **lan**. Start with
   a distinct SSID and WPA2-PSK, plus a strong password. Use a locally permitted
   non-DFS 5 GHz channel for initial testing; test wider channels and WPA3 later.
6. Enable both interfaces and save/apply. Keep Ethernet in `br-lan` for management
   and wired clients. Check the upstream connection before disconnecting your PC.

Using the same SSID/password later can be convenient, but does not guarantee
seamless roaming. Check the USB adapter has stable power if it resets under load.

## Validate on the board

Connect over Ethernet and run:

```sh
ubus call system board
free -h
lsusb
lsmod | grep -E 'sprdwl|uwe5622|mt7921'
iw phy
iw dev
logread | grep -Ei 'wcn|sprd|uwe5622|mt7921|firmware|hostapd|wpa'
dmesg | grep -Ei 'mmc|sdio|wcn|sprd|uwe5622|mt7921|firmware'
```

Confirm approximately 1 GB of physical RAM (usable memory is lower), both radios,
onboard client association, a USB AP client receiving LAN DHCP, DNS/internet access,
and recovery after reboot. The original DeepAQ port notes incomplete station/AP
information in LuCI; use command-line diagnostics as well.

For build failures, download the artifact and inspect the **first compiler/patch
error** in `build.log`. Do not bypass checks by creating fake build stamp files.
Kernel modules must come from this exact build; mixing arbitrary kmods from another
release/snapshot can fail because of the kernel ABI.

## References

- https://openwrt.org/toh/xunlong/orange_pi_zero_3
- https://github.com/openwrt/openwrt/issues/18494
- https://github.com/Anieake/openwrt-orangepi-zero2-zero3-wifi-modem
- https://github.com/DeepAQ/openwrt-uwe5622-sunxi
- https://github.com/armbian/uwe5622

Third-party driver patches retain their original notices and licenses. This
repository downloads them at build time rather than redistributing firmware blobs.
