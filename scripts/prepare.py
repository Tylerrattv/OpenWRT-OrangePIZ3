"""Apply the minimum Wi-Fi integration to the pinned OpenWrt tree."""
from pathlib import Path
import shutil
import sys

root, port = map(Path, sys.argv[1:])
mac = root / "package/kernel/mac80211"
source_mac = port / "package/kernel/mac80211"

# The port's mac80211 Makefile differs only by these three hooks.
makefile = mac / "Makefile"
content = makefile.read_text()
hooks = [
    ("include realtek.mk\n", "include unisoc.mk\n"),
    ("\t$(call PatchDir,$(PKG_BUILD_DIR),$(PATCH_DIR)/rtl,rtl/)\n",
     "\t$(call PatchDir,$(PKG_BUILD_DIR),$(PATCH_DIR)/unisoc,unisoc/)\n"),
    ("\t$(call Quilt/RefreshDir,$(PKG_BUILD_DIR),$(PATCH_DIR)/rtl,rtl/)\n",
     "\t$(call Quilt/RefreshDir,$(PKG_BUILD_DIR),$(PATCH_DIR)/unisoc,unisoc/)\n"),
]
for anchor, addition in hooks:
    if content.count(anchor) != 1 or addition in content:
        raise RuntimeError(f"Unexpected Makefile or already applied integration: {anchor!r}")
    content = content.replace(anchor, anchor + addition)
makefile.write_text(content)
shutil.copy2(source_mac / "unisoc.mk", mac / "unisoc.mk")
shutil.copytree(source_mac / "patches/unisoc", mac / "patches/unisoc")
shutil.copytree(port / "package/firmware/armbian-firmware",
                root / "package/firmware/armbian-firmware")

# Limit the warning workaround to this vendor driver; child directories inherit it.
# Applied as a source patch on every clean build, never by forging build stamps.
(mac / "patches/unisoc/999-fix-werror.patch").write_text(
    "--- a/drivers/net/wireless/uwe5622/Makefile\n"
    "+++ b/drivers/net/wireless/uwe5622/Makefile\n"
    "@@ -1,3 +1,5 @@\n"
    "+subdir-ccflags-y += -Wno-error\n"
    "+\n"
    " obj-$(CPTCFG_AW_WIFI_DEVICE_UWE5622) += unisocwcn/\n"
    " obj-$(CPTCFG_WLAN_UWE5622)    += unisocwifi/\n"
    " obj-$(CPTCFG_TTY_OVERY_SDIO)  += tty-sdio/\n"
)
name = "arm64-dts-h616-add-wifi-support-for-orange-pi-zero-2-and-zero3.patch"
shutil.copy2(port / "target/linux/sunxi/patches-6.12" / name,
             root / "target/linux/sunxi/patches-6.12/999-uwe5622-zero3-wifi.patch")
print("Applied UWE5622 package, firmware, and Zero 3 SDIO device-tree integration.")
