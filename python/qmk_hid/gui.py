#!/usr/bin/env python3
import os
import sys
import subprocess
import time

import tkinter as tk
from tkinter import ttk, messagebox

if os.name == 'nt':
    from win32api import GetKeyState, keybd_event
    from win32con import VK_NUMLOCK, VK_CAPITAL
    import winreg

import webbrowser

from qmk_hid.protocol import *
from qmk_hid import firmware_update

# TODO:
# - Get current values
#   - Set sliders to current values

PROGRAM_VERSION = "0.2.0"

DEBUG_PRINT = False

def debug_print(*args):
    if DEBUG_PRINT:
        print(args)

def format_fw_ver(fw_ver):
    fw_ver_major = (fw_ver & 0xFF00) >> 8
    fw_ver_minor = (fw_ver & 0x00F0) >> 4
    fw_ver_patch = (fw_ver & 0x000F)
    return f"{fw_ver_major}.{fw_ver_minor}.{fw_ver_patch}"


def get_numlock_state():
    if os.name == 'nt':
        return GetKeyState(VK_NUMLOCK)
    else:
        try:
            # TODO: This doesn't work on wayland
            # In GNOME we can do gsettings set org.gnome.settings-daemon.peripherals.keyboard numlock-state on
            output = subprocess.run(['numlockx', 'status'], stdout=subprocess.PIPE).stdout
            if b'on' in output:
                return True
            elif b'off' in output:
                return False
        except FileNotFoundError:
            # Ignore tool not found, just return None
            pass


def update_type(t):
    types = {
        'ansi': 0x0012,
        'iso': 0x0018,
        'jis': 0x0019,
        'macropad': 0x0013,
        'numpad': 0x0014,
    }
    if t not in types:
        print(f"Invalid type '{t}'")
        sys.exit(1)
    pid = types[t]

    #if is_pyinstaller():
    #    print("Not bundled executable. No releases available.")
    #    sys.exit(1)

    releases = find_releases()
    versions = sorted(list(releases.keys()), reverse=True)
    latest_version = versions[0]
    firmware_path = releases[latest_version][t]

    print(f"Firmware path: '{firmware_path}'")

    devices = find_devs(show=False, verbose=False)
    #print("Found {} devices".format(len(devices)))

    filtered_devs = [dev for dev in devices if dev['product_id'] == pid]

    if len(filtered_devs) == 0:
        print("No USB device with VID 32AC PID {:04X} found. Aborting".format(pid))
        sys.exit(1)

    if len(filtered_devs) > 1:
        print("More than 1 USB device with VID 32AC PID {:04X} found. Aborting".format(pid))
        sys.exit(1)

    print("Flashing firmware")
    flash_firmware(filtered_devs[0], firmware_path)

    print("Waiting 2 seconds for the keyboard to restart")
    time.sleep(2)


def main():
    devices = find_devs(show=False, verbose=False)

    root = tk.Tk()
    root.title("QMK Keyboard Control")
    ico = "logo_cropped_transparent_keyboard_48x48.ico"
    res_path = resource_path()
    if os.name == 'nt':
        root.iconbitmap(f"{res_path}/res/{ico}")

    tabControl = ttk.Notebook(root)
    tab1 = ttk.Frame(tabControl)
    tab_fw_update = ttk.Frame(tabControl)
    tab2 = ttk.Frame(tabControl)
    tabControl.add(tab1, text="Home")
    tabControl.add(tab_fw_update, text="Firmware Update")
    tabControl.add(tab2, text="Advanced")
    tabControl.pack(expand=1, fill="both")

    # Device Checkboxes
    detected_devices_frame = ttk.LabelFrame(tab1, text="Detected Devices", style="TLabelframe")
    detected_devices_frame.pack(fill="x", padx=10, pady=5)

    global device_checkboxes
    device_checkboxes = {}
    for dev in devices:
        device_info = "{}\nSerial No: {}\nFW Version: {}\n".format(
            dev['product_string'],
            dev['serial_number'],
            format_fw_ver(dev['release_number'])
        )
        checkbox_var = tk.BooleanVar(value=True)
        checkbox = ttk.Checkbutton(detected_devices_frame, text=device_info, variable=checkbox_var, style="TCheckbutton")
        checkbox.pack(anchor="w")
        device_checkboxes[dev['path']] = (checkbox_var, checkbox)

    # Online Info
    info_frame = ttk.LabelFrame(tab1, text="Online Info", style="TLabelframe")
    info_frame.pack(fill="x", padx=10, pady=5)
    infos = {
        "VIA Web Interface": "https://keyboard.frame.work",
        "Firmware Releases": "https://github.com/FrameworkComputer/qmk_firmware/releases",
        "Tool Releases": "https://github.com/FrameworkComputer/qmk_hid/releases",
        "Keyboard Hotkeys": "https://knowledgebase.frame.work/hotkeys-on-the-framework-laptop-16-keyboard-rkYIwFQPp",
        "Macropad Layout": "https://knowledgebase.frame.work/default-keymap-for-the-rgb-macropad-rkBIgqmva",
        "Numpad Layout": "https://knowledgebase.frame.work/default-keymap-for-the-numpad-rJZv44owa",
    }
    for (i, (text, url)) in enumerate(infos.items()):
        # Organize in columns of three
        row = int(i / 3)
        column = i % 3
        btn = ttk.Button(info_frame, text=text, command=lambda url=url: open_browser_func(url), style="TButton")
        btn.grid(row=row, column=column)

    # Device Control Buttons
    device_control_frame = ttk.LabelFrame(tab1, text="Device Control", style="TLabelframe")
    device_control_frame.pack(fill="x", padx=10, pady=5)
    control_buttons = {
        "Bootloader": "bootloader",
        "Save Changes": "save_changes",
    }
    for text, action in control_buttons.items():
        ttk.Button(device_control_frame, text=text, command=lambda a=action: perform_action(devices, a), style="TButton").pack(side="left", padx=5, pady=5)

    # Brightness Slider
    brightness_frame = ttk.LabelFrame(tab1, text="Brightness", style="TLabelframe")
    brightness_frame.pack(fill="x", padx=10, pady=5)
    global brightness_scale
    brightness_scale = tk.Scale(brightness_frame, from_=0, to=255, orient='horizontal', command=lambda value: perform_action(devices, 'brightness', value=int(value)))
    brightness_scale.set(120)  # Default value
    brightness_scale.pack(fill="x", padx=5, pady=5)

    # RGB color
    rgb_color_buttons = {
        "Red": "red",
        "Green": "green",
        "Blue": "blue",
        "White": "white",
        "Off": "off",
    }
    btn_frame = ttk.Frame(brightness_frame)
    btn_frame.pack(side=tk.TOP)
    for text, action in rgb_color_buttons.items():
        btn = ttk.Button(btn_frame, text=text, command=lambda a=action: perform_action(devices, a), style="TButton")
        btn.pack(side="left", padx=5, pady=5)

    # RGB Effect Combo Box
    rgb_effect_label = tk.Label(brightness_frame, text="RGB Effect")
    rgb_effect_label.pack(side=tk.LEFT, padx=5, pady=5)
    rgb_effect_combo = ttk.Combobox(brightness_frame, values=RGB_EFFECTS, style="TCombobox", state="readonly")
    rgb_effect_combo.pack(side=tk.LEFT, padx=5, pady=5)
    rgb_effect_combo.bind("<<ComboboxSelected>>", lambda event: perform_action(devices, 'rgb_effect', value=RGB_EFFECTS.index(rgb_effect_combo.get())))

    # White backlight keyboard
    rgb_effect_label = tk.Label(brightness_frame, text="White Effect")
    rgb_effect_label.pack(side=tk.LEFT, padx=5, pady=5)
    ttk.Button(brightness_frame, text="Breathing", command=lambda a=action: perform_action(devices, "breathing_on"), style="TButton").pack(side="left", padx=5, pady=5)
    ttk.Button(brightness_frame, text="None", command=lambda a=action: perform_action(devices, "breathing_off"), style="TButton").pack(side="left", padx=5, pady=5)

    # Tab 2
    # Advanced Device Control Buttons
    eeprom_frame = ttk.LabelFrame(tab2, text="EEPROM", style="TLabelframe")
    eeprom_frame.pack(fill="x", padx=5, pady=5)
    tk.Label(eeprom_frame, text="Clear user configured settings").pack(side="top", padx=5, pady=5)
    ttk.Button(eeprom_frame, text="Reset EEPROM", command=lambda: perform_action(devices, 'reset_eeprom'), style="TButton").pack(side="left", padx=5, pady=5)

    bios_mode_frame = ttk.LabelFrame(tab2, text="BIOS Mode", style="TLabelframe")
    bios_mode_frame.pack(fill="x", padx=5, pady=5)
    tk.Label(bios_mode_frame, text="Disable function buttons, force F1-12").pack(side="top", padx=5, pady=5)
    ttk.Button(bios_mode_frame, text="Enable", command=lambda: perform_action(devices, 'bios_mode', value=True), style="TButton").pack(side="left", padx=5, pady=5)
    ttk.Button(bios_mode_frame, text="Disable", command=lambda: perform_action(devices, 'bios_mode', value=False), style="TButton").pack(side="left", padx=5, pady=5)

    factory_mode_frame = ttk.LabelFrame(tab2, text="Factory Mode", style="TLabelframe")
    factory_mode_frame.pack(fill="x", padx=5, pady=5)
    tk.Label(factory_mode_frame, text="Ignore user configured keymap").pack(side="top", padx=5, pady=5)
    ttk.Button(factory_mode_frame, text="Enable", command=lambda: perform_action(devices, 'factory_mode', value=True), style="TButton").pack(side="left", padx=5, pady=5)
    ttk.Button(factory_mode_frame, text="Disable", command=lambda: perform_action(devices, 'factory_mode', value=False), style="TButton").pack(side="left", padx=5, pady=5)

    # Unreliable on Linux
    # Different versions of numlockx behave differently
    # Xorg vs Wayland is different
    if os.name == 'nt':
        numlock_frame = ttk.LabelFrame(tab2, text="OS Numlock Setting", style="TLabelframe")
        numlock_frame.pack(fill="x", padx=5, pady=5)
        numlock_state_var = tk.StringVar()
        numlock_state_var.set("State: Unknown")
        numlock_state_label = tk.Label(numlock_frame, textvariable=numlock_state_var).pack(side="top", padx=5, pady=5)
        refresh_btn = ttk.Button(numlock_frame, text="Refresh", command=lambda: update_numlock_state(numlock_state_var), style="TButton", state=tk.DISABLED)
        refresh_btn.pack(side="left", padx=5, pady=5)
        toggle_btn = ttk.Button(numlock_frame, text="Emulate numlock button press", command=lambda: toggle_numlock(), style="TButton", state=tk.DISABLED)
        toggle_btn.pack(side="left", padx=5, pady=5)

        update_numlock_state(numlock_state_var, refresh_btn, toggle_btn)

    # TODO: Maybe hide behind secret shortcut
    if os.name == 'nt':
        registry_frame = ttk.LabelFrame(tab2, text="Windows Registry Tweaks", style="TLabelframe")
        registry_frame.pack(fill="x", padx=5, pady=5)
        tk.Label(registry_frame, text="Disabled. Only for very advanced debugging").pack(side="top", padx=5, pady=5)
        ttk.Button(registry_frame, text="Enable Selective Suspend", command=lambda dev: selective_suspend_wrapper(dev, True), style="TButton", state=tk.DISABLED).pack(side="left", padx=5, pady=5)
        toggle_btn = ttk.Button(registry_frame, text="Disable Selective Suspend", command=lambda dev: selective_suspend_wrapper(dev, False), style="TButton", state=tk.DISABLED).pack(side="left", padx=5, pady=5)

    # Only in the pyinstaller bundle are the FW update binaries included
    releases = firmware_update.find_releases(resource_path(), r'framework_(.*)_default.*\.uf2')
    if not releases:
        tk.Label(tab_fw_update, text="Cannot find firmware updates").pack(side="top", padx=5, pady=5)
    else:
        versions = sorted(list(releases.keys()), reverse=True)

        flash_btn = None
        fw_type_combo = None

        fw_update_frame = ttk.LabelFrame(tab_fw_update, text="Update Firmware", style="TLabelframe")
        fw_update_frame.pack(fill="x", padx=5, pady=5)
        #tk.Label(fw_update_frame, text="Ignore user configured keymap").pack(side="top", padx=5, pady=5)
        fw_ver_combo = ttk.Combobox(fw_update_frame, values=versions, style="TCombobox", state="readonly")
        fw_ver_combo.pack(side=tk.LEFT, padx=5, pady=5)
        fw_ver_combo.current(0)
        fw_ver_combo.bind("<<ComboboxSelected>>", lambda event: select_fw_version(fw_ver_combo.get(), fw_type_combo, releases))
        fw_type_combo = ttk.Combobox(fw_update_frame, values=list(releases[versions[0]]), style="TCombobox", state="readonly")
        fw_type_combo.pack(side=tk.LEFT, padx=5, pady=5)
        fw_type_combo.bind("<<ComboboxSelected>>", lambda event: select_fw_type(fw_type_combo.get(), flash_btn))
        flash_btn = ttk.Button(fw_update_frame, text="Update", command=lambda: tk_flash_firmware(devices, releases, fw_ver_combo.get(), fw_type_combo.get()), state=tk.DISABLED, style="TButton")
        flash_btn.pack(side="left", padx=5, pady=5)

    program_ver_label = tk.Label(tab1, text=f"Program Version: {PROGRAM_VERSION}")
    program_ver_label.pack(side=tk.LEFT, padx=5, pady=5)

    root.mainloop()

def update_numlock_state(state_var, refresh_btn=None, toggle_btn=None):
    numlock_on = get_numlock_state()
    if numlock_on is None and os != 'nt':
        state_var.set("Unknown, please install the 'numlockx' command")
    else:
        if refresh_btn:
            refresh_btn.config(state=tk.NORMAL)
        if toggle_btn:
            toggle_btn.config(state=tk.NORMAL)
        state_var.set("On (Numbers)" if numlock_on else "Off (Arrows)")


def toggle_numlock():
    if os.name == 'nt':
        keybd_event(VK_NUMLOCK, 0x3A, 0x1, 0)
        keybd_event(VK_NUMLOCK, 0x3A, 0x3, 0)
    else:
        out = subprocess.check_output(['numlockx', 'toggle'])


def is_pyinstaller():
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')


def resource_path():
    """ Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return base_path

# TODO: Possibly use this
def backlight_watcher(window, devs):
    prev_brightness = {}
    while True:
        for dev in devs:
            brightness = get_backlight(dev, BACKLIGHT_VALUE_BRIGHTNESS)
            rgb_brightness = get_rgb_u8(dev, RGB_MATRIX_VALUE_BRIGHTNESS)

            br_changed = False
            rgb_br_changed = False
            if dev['path'] in prev_brightness:
                if brightness != prev_brightness[dev['path']]['brightness']:
                    debug_print("White Brightness Changed")
                    br_changed =  True
                if rgb_brightness != prev_brightness[dev['path']]['rgb_brightness']:
                    debug_print("RGB Brightness Changed")
                    rgb_br_changed =  True
            prev_brightness[dev['path']] = {
                'brightness': brightness,
                'rgb_brightness': rgb_brightness,
            }

            if br_changed or rgb_br_changed:
                # Update other keyboards
                new_brightness = brightness if br_changed else rgb_brightness
                debug_print("Updating based on {}".format(dev['product_string']))
                debug_print("Update other keyboards to: {:02.2f}% ({})".format(new_brightness * 100 / 255, new_brightness))
                for other_dev in devs:
                    debug_print("Updating {}".format(other_dev['product_string']))
                    if dev['path'] != other_dev['path']:
                            set_brightness(other_dev, new_brightness)
                            set_rgb_brightness(other_dev, new_brightness)
                            #time.sleep(1)
                            # Avoid it triggering an update in the other direction
                            prev_brightness[other_dev['path']] = {
                                'brightness': get_backlight(other_dev, BACKLIGHT_VALUE_BRIGHTNESS),
                                'rgb_brightness': get_rgb_u8(other_dev, RGB_MATRIX_VALUE_BRIGHTNESS),
                            }
                debug_print()
        # Avoid high CPU usage
        time.sleep(1)


def restart_hint():
    parent = tk.Tk()
    parent.title("Restart Application")
    message = tk.Message(parent, text="After updating a device,\n restart the application to reload the connections.", width=800)
    message.pack(padx=20, pady=20)
    parent.mainloop()

def info_popup(msg):
    parent = tk.Tk()
    parent.title("Info")
    message = tk.Message(parent, text=msg, width=800)
    message.pack(padx=20, pady=20)
    parent.mainloop()


def replug_hint():
    parent = tk.Tk()
    parent.title("Replug Keyboard")
    message = tk.Message(parent, text="After changing selective suspend setting, make sure to unplug and re-plug the device to apply the settings.", width=800)
    message.pack(padx=20, pady=20)
    parent.mainloop()



def selective_suspend_wrapper(dev, enable):
    if enable:
        selective_suspend_registry(dev['product_id'], False, set=True)
        replug_hint()
    else:
        selective_suspend_registry(dev['product_id'], False, set=False)
        replug_hint()


def selective_suspend_registry(pid, verbose, set=None):
    # The set of keys we care about (under HKEY_LOCAL_MACHINE) are
    # SYSTEM\CurrentControlSet\Enum\USB\VID_32AC&PID_0013\Device Parameters\SelectiveSuspendEnabled
    # SYSTEM\CurrentControlSet\Enum\USB\VID_32AC&PID_0013&MI_00\Device Parameters\SelectiveSuspendEnabled
    # SYSTEM\CurrentControlSet\Enum\USB\VID_32AC&PID_0013&MI_01\Device Parameters\SelectiveSuspendEnabled
    # SYSTEM\CurrentControlSet\Enum\USB\VID_32AC&PID_0013&MI_02\Device Parameters\SelectiveSuspendEnabled
    # SYSTEM\CurrentControlSet\Enum\USB\VID_32AC&PID_0013&MI_03\Device Parameters\SelectiveSuspendEnabled
    # Where 0013 is the USB PID
    #
    # Additionally
    # SYSTEM\CurrentControlSet\Control\usbflags\32AC00130026\osvc
    # Where 32AC is the VID, 0013 is the PID, 0026 is the bcdDevice (version)
    long_pid = "{:0>4X}".format(pid)
    aReg = winreg.ConnectRegistry(None, winreg.HKEY_LOCAL_MACHINE)

    if set is not None:
        if set:
            print("Setting SelectiveSuspendEnabled to ENABLE")
        else:
            print("Setting SelectiveSuspendEnabled to DISABLE")

    for mi in ['', '&MI_00', '&MI_01', '&MI_02', '&MI_03']:
        dev = f'VID_32AC&PID_{long_pid}'
        print(dev)
        parent_name = r'SYSTEM\CurrentControlSet\Enum\USB\\' + dev + mi
        try:
            aKey = winreg.OpenKey(aReg, parent_name)
        except EnvironmentError as e:
            raise e
            #continue
        numSubkeys, numValues, lastModified = winreg.QueryInfoKey(aKey)
        if verbose:
            print(dev)#, numSubkeys, numValues, lastModified)
        for i in range(numSubkeys):
            try:
                aValue_name = winreg.EnumKey(aKey, i)
                if verbose:
                    print(f'  {aValue_name}')
                aKey = winreg.OpenKey(aKey, aValue_name)

                with winreg.OpenKey(aKey, 'Device Parameters', access=winreg.KEY_WRITE) as oKey:
                    if set is not None:
                        if set:
                            #winreg.SetValueEx(oKey, 'SelectiveSuspendEnabled', 0, winreg.REG_BINARY, b'\x01')
                            winreg.SetValueEx(oKey, 'SelectiveSuspendEnabled', 0, winreg.REG_DWORD, 1)
                        else:
                            #winreg.SetValueEx(oKey, 'SelectiveSuspendEnabled', 0, winreg.REG_BINARY, b'\x00')
                            winreg.SetValueEx(oKey, 'SelectiveSuspendEnabled', 0, winreg.REG_DWORD, 0)

                with winreg.OpenKey(aKey, 'Device Parameters', access=winreg.KEY_READ+winreg.KEY_WRITE) as oKey:
                    (sValue, keyType) = winreg.QueryValueEx(oKey, "SelectiveSuspendEnabled")
                    if verbose:
                        if keyType == winreg.REG_DWORD:
                            print(f'    {sValue} (DWORD)')
                        elif keyType == winreg.REG_BINARY:
                            print(f'    {sValue} (BINARY)')
                        elif keyType == winreg.REG_NONE:
                            print(f'    {sValue} (NONE)')
                        else:
                            print(f'    {sValue} (Type: f{keyType})')
            except EnvironmentError as e:
                raise e

def disable_devices(devices):
    # Disable checkbox of selected devices
    for dev in devices:
        for path, (checkbox_var, checkbox) in device_checkboxes.items():
            if path == dev['path']:
                checkbox_var.set(False)
                checkbox.config(state=tk.DISABLED)

def perform_action(devices, action, value=None):
    if action == "bootloader":
        disable_devices(devices)
        restart_hint()

    if action == "off":
        brightness_scale.set(0)

    action_map = {
        "bootloader": lambda dev: bootloader_jump(dev),
        "save_changes": save,
        "eeprom_reset": eeprom_reset,
        "bios_mode": lambda dev: bios_mode(dev, value),
        "factory_mode": lambda dev: factory_mode(dev, value),
        "red": lambda dev: set_rgb_color(dev, RED_HUE, 255),
        "green": lambda dev: set_rgb_color(dev, GREEN_HUE, 255),
        "blue": lambda dev: set_rgb_color(dev, BLUE_HUE, 255),
        "white": lambda dev: set_rgb_color(dev, None, 0),
        "off": lambda dev: set_rgb_brightness(dev, 0),
        "breathing_on": lambda dev: set_white_effect(dev, True),
        "breathing_off": lambda dev: set_white_effect(dev, False),
        "brightness": lambda dev: set_white_rgb_brightness(dev, value),
        "rgb_effect": lambda dev: set_rgb_u8(dev, RGB_MATRIX_VALUE_EFFECT, value),
    }
    selected_devices = get_selected_devices(devices)
    for dev in selected_devices:
        if action in action_map:
            action_map[action](dev)

def get_selected_devices(devices):
    return [dev for dev in devices if dev['path'] in device_checkboxes and device_checkboxes[dev['path']][0].get()]

def set_pattern(devices, pattern_name):
    selected_devices = get_selected_devices(devices)
    for dev in selected_devices:
        pattern(dev, pattern_name)

def select_fw_version(ver, fw_type_combo, releases):
    # After selecting a version, we can list the types of firmware available for this version
    types = list(releases[ver])
    fw_type_combo.config(values=types)
    fw_type_combo.current(0)

def select_fw_type(_fw_type, flash_btn):
    # Once the user has selected a type, the exact firmware file is known and can be flashed
    flash_btn.config(state=tk.NORMAL)

def tk_flash_firmware(devices, releases, version, fw_type):
    selected_devices = get_selected_devices(devices)
    if len(selected_devices) != 1:
        info_popup('To flash select exactly 1 device.')
        return
    dev = selected_devices[0]
    firmware_update.flash_firmware(dev, releases[version][fw_type])
    # Disable device that we just flashed
    disable_devices(devices)
    restart_hint()

if __name__ == "__main__":
    # If the script/executable has one of these in the filename,
    # It's a special script to just update that device
    for t in ['ansi', 'iso', 'jis', 'macropad', 'numpad']:
        if t in sys.argv[0]:
            update_type(t)
            sys.exit(1)

    main()
