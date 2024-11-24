#!/usr/bin/env python3
import os
import sys
import subprocess
import time

import tkinter as tk
from tkinter import ttk, messagebox

import hid
if os.name == 'nt':
    from win32api import GetKeyState, keybd_event
    from win32con import VK_NUMLOCK, VK_CAPITAL
    import winreg

import webbrowser

from qmk_hid import uf2conv

# TODO:
# - Get current values
#   - Set sliders to current values

PROGRAM_VERSION = "0.2.0"
FWK_VID = 0x32AC

DEBUG_PRINT = False

QMK_INTERFACE = 0x01
RAW_HID_BUFFER_SIZE = 32

RAW_USAGE_PAGE = 0xFF60
CONSOLE_USAGE_PAGE = 0xFF31
# Generic Desktop
G_DESK_USAGE_PAGE = 0x01
CONSUMER_USAGE_PAGE = 0x0C

GET_PROTOCOL_VERSION = 0x01  # always 0x01
GET_KEYBOARD_VALUE = 0x02
SET_KEYBOARD_VALUE = 0x03
# DynamicKeymapGetKeycode         = 0x04
# DynamicKeymapSetKeycode         = 0x05
# DynamicKeymapReset              = 0x06
CUSTOM_SET_VALUE = 0x07
CUSTOM_GET_VALUE = 0x08
CUSTOM_SAVE = 0x09
EEPROM_RESET = 0x0A
BOOTLOADER_JUMP = 0x0B

CHANNEL_CUSTOM = 0
CHANNEL_BACKLIGHT = 1
CHANNEL_RGB_LIGHT = 2
CHANNEL_RGB_MATRIX = 3
CHANNEL_AUDIO = 4

BACKLIGHT_VALUE_BRIGHTNESS = 1
BACKLIGHT_VALUE_EFFECT = 2

RGB_MATRIX_VALUE_BRIGHTNESS = 1
RGB_MATRIX_VALUE_EFFECT = 2
RGB_MATRIX_VALUE_EFFECT_SPEED = 3
RGB_MATRIX_VALUE_COLOR = 4

RED_HUE = 0
YELLOW_HUE = 43
GREEN_HUE = 85
CYAN_HUE = 125
BLUE_HUE = 170
PURPLE_HUE = 213

RGB_EFFECTS = [
    "Off",
    "SOLID_COLOR",
    "ALPHAS_MODS",
    "GRADIENT_UP_DOWN",
    "GRADIENT_LEFT_RIGHT",
    "BREATHING",
    "BAND_SAT",
    "BAND_VAL",
    "BAND_PINWHEEL_SAT",
    "BAND_PINWHEEL_VAL",
    "BAND_SPIRAL_SAT",
    "BAND_SPIRAL_VAL",
    "CYCLE_ALL",
    "CYCLE_LEFT_RIGHT",
    "CYCLE_UP_DOWN",
    "CYCLE_OUT_IN",
    "CYCLE_OUT_IN_DUAL",
    "RAINBOW_MOVING_CHEVRON",
    "CYCLE_PINWHEEL",
    "CYCLE_SPIRAL",
    "DUAL_BEACON",
    "RAINBOW_BEACON",
    "RAINBOW_PINWHEELS",
    "RAINDROPS",
    "JELLYBEAN_RAINDROPS",
    "HUE_BREATHING",
    "HUE_PENDULUM",
    "HUE_WAVE",
    "PIXEL_FRACTAL",
    "PIXEL_FLOW",
    "PIXEL_RAIN",
    "TYPING_HEATMAP",
    "DIGITAL_RAIN",
    "SOLID_REACTIVE_SIMPLE",
    "SOLID_REACTIVE",
    "SOLID_REACTIVE_WIDE",
    "SOLID_REACTIVE_MULTIWIDE",
    "SOLID_REACTIVE_CROSS",
    "SOLID_REACTIVE_MULTICROSS",
    "SOLID_REACTIVE_NEXUS",
    "SOLID_REACTIVE_MULTINEXUS",
    "SPLASH",
    "MULTISPLASH",
    "SOLID_SPLASH",
    "SOLID_MULTISPLASH",
]

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

def main():
    devices = find_devs(show=False, verbose=False)
    # print("Found {} devices".format(len(devices)))

    root = tk.Tk()
    root.title("QMK GUI")
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
    releases = find_releases()
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

    program_ver_label = tk.Label(tab1, text="Program Version: 0.2.0")
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
def find_releases():
    from os import listdir
    from os.path import isfile, join
    import re

    releases = {}
    res_path = resource_path()
    try:
        versions = listdir(os.path.join(res_path, "releases"))
    except FileNotFoundError:
        return releases

    for version in versions:
        path = join(res_path, "releases", version)
        releases[version] = {}
        for filename in listdir(path):
            if not isfile(join(path, filename)):
                continue
            type_search = re.search(r'framework_(.*)_default.*\.uf2', filename)
            if not type_search:
                print(f"Filename '{filename}' not matching patten!")
                sys.exit(1)
                continue
            fw_type = type_search.group(1)
            releases[version][fw_type] = os.path.join(res_path, "releases", version, filename)
    return releases


def find_devs(show, verbose):
    if verbose:
        show = True

    devices = []
    for device_dict in hid.enumerate():
        vid = device_dict["vendor_id"]
        pid = device_dict["product_id"]
        product = device_dict["product_string"]
        manufacturer = device_dict["manufacturer_string"]
        sn = device_dict['serial_number']
        interface = device_dict['interface_number']
        path = device_dict['path']

        if vid != FWK_VID:
            if verbose:
                print("Vendor ID not matching")
            continue

        if interface != QMK_INTERFACE:
            if verbose:
                print("Interface not matching")
            continue
        # For some reason on Linux it'll always show usage_page==0
        if os.name == 'nt' and device_dict['usage_page'] not in [RAW_USAGE_PAGE, CONSOLE_USAGE_PAGE]:
            if verbose:
                print("Usage Page not matching")
            continue
        # Lots of false positives, so at least skip Framework false positives
        if vid == FWK_VID and pid not in [0x12, 0x13, 0x14, 0x18, 0x19]:
            if verbose:
                print("False positive, device is not allowed")
            continue

        fw_ver = device_dict["release_number"]

        if (os.name == 'nt' and device_dict['usage_page'] == RAW_USAGE_PAGE) or verbose:
            if show:
                print(f"Manufacturer: {manufacturer}")
                print(f"Product:      {product}")
                print("FW Version:   {}".format(format_fw_ver(fw_ver)))
                print(f"Serial No:    {sn}")

            if verbose:
                print(f"Path:         {path}")
                print(f"VID/PID:      {vid:02X}:{pid:02X}")
                print(f"Interface:    {interface}")
                # TODO: print Usage Page
                print("")

        devices.append(device_dict)

    return devices


def send_message(dev, message_id, msg, out_len):
    data = [0xFE] * RAW_HID_BUFFER_SIZE
    data[0] = 0x00 # NULL report ID
    data[1] = message_id

    if msg:
        if len(msg) > RAW_HID_BUFFER_SIZE-2:
            print("Message too big. BUG. Please report")
            sys.exit(1)
        for i, x in enumerate(msg):
            data[2+i] = x

    try:
        # TODO: Do this somewhere outside
        h = hid.device()
        h.open_path(dev['path'])
        #h.set_nonblocking(0)
        h.write(data)

        if out_len == 0:
            return None

        out_data = h.read(out_len+3)
        return out_data
    except (IOError, OSError) as ex:
        disable_devices([dev])
        debug_print("Error ({}): ".format(dev['path']), ex)

def set_keyboard_value(dev, value, number):
    msg = [value, number]
    send_message(dev, SET_KEYBOARD_VALUE, msg, 0)

def set_rgb_u8(dev, value, value_data):
    msg = [CHANNEL_RGB_MATRIX, value, value_data]
    send_message(dev, CUSTOM_SET_VALUE, msg, 0)

# Returns brightness level: x/255
def get_rgb_u8(dev, value):
    msg = [CHANNEL_RGB_MATRIX, value]
    output = send_message(dev, CUSTOM_GET_VALUE, msg, 1)
    if output[0] == 255: # Not RGB
        return None
    return output[3]

# Returns (hue, saturation)
def get_rgb_color(dev):
    msg = [CHANNEL_RGB_MATRIX, RGB_MATRIX_VALUE_COLOR]
    output = send_message(dev, CUSTOM_GET_VALUE, msg, 2)
    return (output[3], output[4])

# Returns brightness level: x/255
def get_backlight(dev, value):
    msg = [CHANNEL_BACKLIGHT, value]
    output = send_message(dev, CUSTOM_GET_VALUE, msg, 1)
    return output[3]

def set_backlight(dev, value, value_data):
    msg = [CHANNEL_BACKLIGHT, value, value_data]
    send_message(dev, CUSTOM_SET_VALUE, msg, 0)

def save(dev):
    save_rgb(dev)
    save_backlight(dev)

def save_rgb(dev):
    msg = [CHANNEL_RGB_MATRIX]
    send_message(dev, CUSTOM_SAVE, msg, 0)

def save_backlight(dev):
    msg = [CHANNEL_BACKLIGHT]
    send_message(dev, CUSTOM_SAVE, msg, 0)

def eeprom_reset(dev):
    send_message(dev, EEPROM_RESET, None, 0)


def bootloader_jump(dev):
    send_message(dev, BOOTLOADER_JUMP, None, 0)


def bios_mode(dev, enable):
    param = 0x01 if enable else 0x00
    send_message(dev, BOOTLOADER_JUMP, [0x05, param], 0)


def factory_mode(dev, enable):
    param = 0x01 if enable else 0x00
    send_message(dev, BOOTLOADER_JUMP, [0x06, param], 0)


def set_rgb_brightness(dev, brightness):
    set_rgb_u8(dev, RGB_MATRIX_VALUE_BRIGHTNESS, brightness)


def set_brightness(dev, brightness):
    set_backlight(dev, BACKLIGHT_VALUE_BRIGHTNESS, brightness)

def set_white_effect(dev, breathing_on):
    set_backlight(dev, BACKLIGHT_VALUE_EFFECT, breathing_on)

# Set both
def set_white_rgb_brightness(dev, brightness):
    set_brightness(dev, brightness)
    set_rgb_brightness(dev, brightness)


def set_rgb_color(dev, hue, saturation):
    (cur_hue, cur_sat) = get_rgb_color(dev)
    if hue is None:
        hue = cur_hue
    msg = [CHANNEL_RGB_MATRIX, RGB_MATRIX_VALUE_COLOR, hue, saturation]
    send_message(dev, CUSTOM_SET_VALUE, msg, 0)


def restart_hint():
    parent = tk.Tk()
    parent.title("Restart Application")
    message = tk.Message(parent, text="After updating a device,\n restart the application to reload the connections.", width=800)
    message.pack(padx=20, pady=20)
    parent.mainloop()

def info_popup(msg):
    parent = tk.Tk()
    parent.title("Info")
    message = tk.Message(parent, text="msg", width=800)
    message.pack(padx=20, pady=20)
    parent.mainloop()


def replug_hint():
    parent = tk.Tk()
    parent.title("Replug Keyboard")
    message = tk.Message(parent, text="After changing selective suspend setting, make sure to unplug and re-plug the device to apply the settings.", width=800)
    message.pack(padx=20, pady=20)
    parent.mainloop()


def flash_firmware(dev, fw_path):
    print(f"Flashing {fw_path} onto {dev['path']}")

    # First jump to bootloader
    drives = uf2conv.list_drives()
    if not drives:
        print("Jump to bootloader")
        bootloader_jump(dev)

    timeout = 10  # 5s
    while not drives:
        if timeout == 0:
            print("Failed to find device in bootloader")
            # TODO: Handle return value
            return False
        # Wait for it to appear
        time.sleep(0.5)
        timeout -= 1
        drives = uf2conv.get_drives()


    if len(drives) == 0:
        print("No drive to deploy.")
        return False

    # Firmware is pretty small, can just fit it all into memory
    with open(fw_path, 'rb') as f:
        fw_buf = f.read()

    for d in drives:
        print("Flashing {} ({})".format(d, uf2conv.board_id(d)))
        uf2conv.write_file(d + "/NEW.UF2", fw_buf)

    print("Flashing finished")

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
    flash_firmware(dev, releases[version][fw_type])
    # Disable device that we just flashed
    disable_devices(devices)
    restart_hint()

if __name__ == "__main__":
    main()
