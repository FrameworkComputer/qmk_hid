import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

# Allow the offline suite to run without hidapi installed.
try:
    import hid
except ImportError:
    sys.modules["hid"] = types.ModuleType("hid")

from qmk_hid import firmware_update, protocol, uf2conv


class FirmwareTests(unittest.TestCase):
    def test_releases_ignore_unrelated_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "releases"
            root.mkdir()
            (root / "notes.txt").write_text("notes")
            version = root / "1.0"
            version.mkdir()
            (version / "notes.txt").write_text("notes")
            firmware = version / "framework_gridpad_default.uf2"
            firmware.touch()
            self.assertEqual(firmware_update.find_releases(
                directory, r"framework_(.*)_default.*\.uf2"
            ), {"1.0": {"gridpad": str(firmware)}})

    def test_flash_only_new_drive(self):
        with tempfile.TemporaryDirectory() as directory:
            firmware = Path(directory) / "firmware.uf2"
            firmware.write_bytes(uf2conv.convert_to_uf2(b"firmware"))
            with patch.object(uf2conv, "get_drives", side_effect=[["old"], ["old", "new"]]), \
                 patch.object(firmware_update, "bootloader_jump") as jump, \
                 patch.object(firmware_update.time, "sleep"), \
                 patch.object(uf2conv, "board_id", return_value="test"), \
                 patch.object(uf2conv, "write_file") as write:
                self.assertTrue(firmware_update.flash_firmware({"path": b"test"}, firmware))
                jump.assert_called_once()
                self.assertEqual(write.call_args.args[0], "new/NEW.UF2")

    def test_invalid_firmware_does_not_reboot(self):
        with tempfile.NamedTemporaryFile() as firmware:
            firmware.write(b"bad")
            firmware.flush()
            with patch.object(firmware_update, "bootloader_jump") as jump:
                with self.assertRaises(ValueError):
                    firmware_update.flash_firmware({"path": b"test"}, firmware.name)
                jump.assert_not_called()


if __name__ == "__main__":
    unittest.main()
