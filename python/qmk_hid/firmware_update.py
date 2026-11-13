import os
import time

from qmk_hid.protocol import bootloader_jump
from qmk_hid import uf2conv

def dev_to_str(dev):
    return dev['path']

def flash_firmware(dev, fw_path):
    print(f"Flashing {fw_path} onto {dev_to_str(dev)}")

    # Validate the input before changing the device state.
    with open(fw_path, 'rb') as f:
        fw_buf = f.read()
    uf2conv.validate_uf2(fw_buf)

    # Only consider a drive that appears after the selected device reboots.
    existing = set(uf2conv.get_drives())
    bootloader_jump(dev)
    for _ in range(10):
        time.sleep(0.5)
        drives = set(uf2conv.get_drives()) - existing
        if len(drives) > 1:
            raise RuntimeError("Multiple new UF2 drives found; cannot identify selected device")
        if drives:
            drive = drives.pop()
            print("Flashing {} ({})".format(drive, uf2conv.board_id(drive)))
            uf2conv.write_file(os.path.join(drive, "NEW.UF2"), fw_buf)
            print("Flashing finished")
            return True
    print("Failed to find selected device in bootloader")
    return False


# Example return value
# {
#   '0.1.7': {
#     'ansi': 'framework_ansi_default_v0.1.7.uf2',
#     'gridpad': 'framework_gridpad_default_v0.1.7.uf2'
#   },
#   '0.1.8': {
#     'ansi': 'framework_ansi_default.uf2',
#     'gridpad': 'framework_gridpad_default.uf2',
#   }
# }
def find_releases(res_path, filename_format):
    from os import listdir
    from os.path import isfile, join
    import re

    releases = {}
    try:
        versions = listdir(os.path.join(res_path, "releases"))
    except FileNotFoundError:
        return releases

    for version in versions:
        path = join(res_path, "releases", version)
        if not os.path.isdir(path):
            continue
        files = {}
        for filename in listdir(path):
            if not isfile(join(path, filename)):
                continue
            type_search = re.fullmatch(filename_format, filename)
            if not type_search:
                continue
            fw_type = type_search.group(1)
            files[fw_type] = os.path.join(res_path, "releases", version, filename)
        if files:
            releases[version] = files
    return releases
