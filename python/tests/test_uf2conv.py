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


class ConversionTests(unittest.TestCase):
    def test_short_input_detection(self):
        for data in (b"", b"x", b"1234567"):
            self.assertFalse(uf2conv.is_uf2(data))
            self.assertFalse(uf2conv.is_hex(data))

    def test_hex_with_blank_lines(self):
        data = uf2conv.convert_from_hex_to_uf2("\n:0400000001020304F2\n\n:00000001FF\n")
        uf2conv.validate_uf2(data)
        self.assertEqual(data[32:36], b"\x01\x02\x03\x04")

    def test_bad_hex_checksum(self):
        with self.assertRaises(ValueError):
            uf2conv.convert_from_hex_to_uf2(":040000000102030400")

    def test_bad_uf2_end_magic(self):
        data = uf2conv.convert_to_uf2(b"test")
        with self.assertRaises(ValueError):
            uf2conv.convert_from_uf2(data[:-4] + b"bad!")

    def test_linux_mount_locations(self):
        with patch.object(uf2conv.sys, "platform", "linux"), \
             patch.dict(uf2conv.os.environ, {"USER": "tester"}), \
             patch.object(uf2conv.os.path, "isdir", return_value=True), \
             patch.object(uf2conv.os, "listdir", return_value=["RP2"]), \
             patch.object(uf2conv.os.path, "isfile", return_value=True):
            self.assertIn("/run/media/tester/RP2", uf2conv.get_drives())


if __name__ == "__main__":
    unittest.main()
