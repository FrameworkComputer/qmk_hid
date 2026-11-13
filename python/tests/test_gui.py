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


class GuiTests(unittest.TestCase):
    def setUp(self):
        from qmk_hid import gui
        self.gui = gui
        self.dev = {"path": b"test"}
        self.selection = Mock()
        self.selection.get.return_value = True
        self.checkbox = Mock()
        self.gui.device_checkboxes = {b"test": (self.selection, self.checkbox)}

    def test_bootloader_sent_before_deselecting(self):
        def jump(dev):
            self.selection.set.assert_not_called()
        with patch.object(self.gui, "bootloader_jump", side_effect=jump) as boot, \
             patch.object(self.gui, "restart_hint") as hint:
            self.gui.perform_action([self.dev], "bootloader")
            boot.assert_called_once_with(self.dev)
            hint.assert_called_once()
        self.selection.set.assert_called_once_with(False)

    def test_reset_button_action(self):
        with patch.object(self.gui, "eeprom_reset") as reset:
            self.gui.perform_action([self.dev], "reset_eeprom")
            reset.assert_called_once_with(self.dev)

    def test_failed_flash_keeps_device_enabled(self):
        with patch.object(self.gui.firmware_update, "flash_firmware", return_value=False), \
             patch.object(self.gui.messagebox, "showerror"), \
             patch.object(self.gui, "restart_hint") as hint:
            self.gui.tk_flash_firmware([self.dev], {"v": {"pad": "file"}}, "v", "pad")
            self.selection.set.assert_not_called()
            hint.assert_not_called()


if __name__ == "__main__":
    unittest.main()
