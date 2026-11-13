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


class ProtocolTests(unittest.TestCase):
    def transact(self, output, out_len=1):
        handle = Mock()
        handle.write.return_value = 33
        handle.read.return_value = output
        with patch.object(protocol.hid, "device", return_value=handle, create=True):
            result = protocol.send_message(
                {"path": b"test"}, protocol.CUSTOM_GET_VALUE, [3, 1], out_len
            )
        return result, handle

    def test_report_size_and_timeout(self):
        result, handle = self.transact([8, 3, 1, 120])
        self.assertEqual(result[3], 120)
        self.assertEqual(len(handle.write.call_args.args[0]), 33)
        handle.read.assert_called_once_with(32, 1000)
        handle.close.assert_called_once()

    def test_failures_close_device(self):
        for response, error in [([], TimeoutError), ([8], OSError), ([7, 3, 1, 0], OSError)]:
            handle = Mock()
            handle.write.return_value = 33
            handle.read.return_value = response
            with patch.object(protocol.hid, "device", return_value=handle, create=True):
                with self.assertRaises(error):
                    protocol.get_rgb_u8({"path": b"test"}, 1)
            handle.close.assert_called_once()

    def test_setter_waits_for_acknowledgement(self):
        handle = Mock()
        handle.write.return_value = 33
        handle.read.return_value = [7, 3, 1, 80]
        with patch.object(protocol.hid, "device", return_value=handle, create=True):
            protocol.set_rgb_brightness({"path": b"test"}, 80)
        handle.read.assert_called_once_with(32, 1000)
        handle.close.assert_called_once()

    def test_unsupported_command(self):
        self.assertIsNone(self.transact([255])[0])

    def test_discovery_prints_version_and_excludes_console(self):
        raw = dict(vendor_id=0x32AC, product_id=0x30, product_string="Pad",
                   manufacturer_string="Framework", serial_number="test",
                   interface_number=1, path=b"raw", usage_page=0xFF60,
                   release_number=0x0123)
        console = dict(raw, usage_page=0xFF31)
        with patch.object(protocol.hid, "enumerate", return_value=[raw, console], create=True):
            self.assertEqual(protocol.find_devs(True, False), [raw])


if __name__ == "__main__":
    unittest.main()
