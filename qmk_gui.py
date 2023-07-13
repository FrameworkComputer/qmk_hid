#!/usr/bin/env python3
import os
import sys
import time

import PySimpleGUI as sg
import hid
# TODO: Linux
from win32api import GetKeyState, keybd_event
from win32con import VK_NUMLOCK, VK_CAPITAL

import uf2conv

# TODO:
# - Clear EEPROM
# - Save settings
# - Get current values
#   - Set sliders to current values
# - Show connected devices
#   - Get firmware version

PROGRAM_VERSION = "0.1.7"
FWK_VID = 0x32AC

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

def format_fw_ver(fw_ver):
    fw_ver_major = (fw_ver & 0xFF00) >> 8
    fw_ver_minor = (fw_ver & 0x00F0) >> 4
    fw_ver_patch = (fw_ver & 0x000F)
    return f"{fw_ver_major}.{fw_ver_minor}.{fw_ver_patch}"

def get_numlock_state():
    # TODO: Handle Linux
    return GetKeyState(VK_NUMLOCK)

def main(devices):
    device_checkboxes = []
    for dev in devices:
        device_info = "{}\nSerial No: {}\nFW Version: {}\n".format(
            dev['product_string'],
            dev['serial_number'],
            format_fw_ver(dev['release_number'])
        )
        checkbox = sg.Checkbox(device_info, default=True, key='-CHECKBOX-{}-'.format(dev['path']), enable_events=True)
        device_checkboxes.append([checkbox])



    # Only in the pyinstaller bundle are the FW update binaries included
    if is_pyinstaller():
        releases = find_releases()
        versions = sorted(list(releases.keys()), reverse=True)

        bundled_update = [
            [sg.Text("Update Version")],
            [sg.Text("Version"), sg.Push(), sg.Combo(versions, k='-VERSION-', enable_events=True, default_value=versions[0])],
            [sg.Text("Type"), sg.Push(), sg.Combo(list(releases[versions[0]]), k='-TYPE-', enable_events=True)],
            [sg.Text("Make sure the firmware is compatible with\nALL selected devices!")],
            [sg.Button("Flash", k='-FLASH-', disabled=True)],
            [sg.HorizontalSeparator()],
        ]
    else:
        bundled_update = []


    layout = [
        [sg.Text("Detected Devices")],
    ] + device_checkboxes + [
        [sg.HorizontalSeparator()],

        [sg.Text("Bootloader")],
        [sg.Button("Bootloader", k='-BOOTLOADER-')],
        [sg.HorizontalSeparator()],
    ] + bundled_update + [
        [sg.Text("Single-Zone Brightness")],
        # TODO: Get default from device
        [sg.Slider((0, 255), orientation='h', default_value=120,
                   k='-BRIGHTNESS-', enable_events=True)],
        #[sg.Button("Enable Breathing", k='-ENABLE-BREATHING-')],
        #[sg.Button("Disable Breathing", k='-DISABLE-BREATHING-')],

        [sg.Text("RGB Brightness")],
        # TODO: Get default from device
        [sg.Slider((0, 255), orientation='h', default_value=120,
                   k='-RGB-BRIGHTNESS-', enable_events=True)],

        [sg.Text("RGB Color")],
        [
            sg.Button("Red", k='-RED-'),
            sg.Button("Green", k='-GREEN-'),
            sg.Button("Blue", k='-BLUE-'),
            sg.Button("White", k='-WHITE-'),
            sg.Button("Off", k='-OFF-'),
        ],

        [sg.Text("RGB Effect")],
        [sg.Combo(RGB_EFFECTS, k='-RGB-EFFECT-', enable_events=True)],
        [sg.HorizontalSeparator()],

        [sg.Text("OS Numlock Setting")],
        [sg.Text("State: "), sg.Text("", k='-NUMLOCK-STATE-'), sg.Push() ,sg.Button("Refresh")],
        [sg.Button("Send Numlock Toggle", k='-NUMLOCK-TOGGLE-')],

        [sg.HorizontalSeparator()],
        [sg.Text("Save Settings")],
        [sg.Button("Save", k='-SAVE-'), sg.Button("Clear EEPROM", k='-CLEAR-EEPROM-')],
        [sg.Text(f"Program Version: {PROGRAM_VERSION}")],
    ]
    window = sg.Window("QMK Keyboard Control", layout, finalize=True)

    selected_devices = []

    while True:
        numlock_on = get_numlock_state()
        if numlock_on is not None:
            window['-NUMLOCK-STATE-'].update("On (Numbers)" if numlock_on else "Off (Arrows)")

        event, values = window.read()
        #print('Event', event)
        #print('Values', values)

        selected_devices = [
            dev for dev in devices if
            values and values['-CHECKBOX-{}-'.format(dev['path'])]
        ]
            # print("Selected {} devices".format(len(selected_devices)))

        # Updating firmware
        if event == "-FLASH-" and len(selected_devices) != 1:
            sg.Popup('To flash select exactly 1 device.')
            continue
        if event == "-VERSION-":
            # After selecting a version, we can list the types of firmware available for this version
            types = list(releases[values['-VERSION-']])
            window['-TYPE-'].update(value=types[0], values=types)
        if event == "-TYPE-":
            # Once the user has selected a type, the exact firmware file is known and can be flashed
            window['-FLASH-'].update(disabled=False)
        if event == "-FLASH-":
            ver = values['-VERSION-']
            t = values['-TYPE-']
            # print("Flashing", releases[ver][t])
            flash_firmware(dev, releases[ver][t])
            restart_hint()
            window['-CHECKBOX-{}-'.format(dev['path'])].update(False, disabled=True)

        if event == "-NUMLOCK-TOGGLE-":
            # TODO: Linux
            keybd_event(VK_NUMLOCK, 0x3A, 0x1, 0)
            keybd_event(VK_NUMLOCK, 0x3A, 0x3, 0)

        # Run commands on all selected devices
        for dev in selected_devices:
            if event == "-BOOTLOADER-":
                bootloader_jump(dev)
                window['-CHECKBOX-{}-'.format(dev['path'])].update(False, disabled=True)
                restart_hint()

            if event == '-BRIGHTNESS-':
                brightness(dev, int(values['-BRIGHTNESS-']))

            if event == '-RGB-BRIGHTNESS-':
                rgb_brightness(dev, int(values['-RGB-BRIGHTNESS-']))

            if event == '-RGB-EFFECT-':
                effect = RGB_EFFECTS.index(values['-RGB-EFFECT-'])
                set_rgb_u8(dev, RGB_MATRIX_VALUE_EFFECT, effect)
                # TODO: Get effect

            if event == '-RED-':
                set_rgb_color(dev, RED_HUE, 255)
            if event == '-GREEN-':
                set_rgb_color(dev, GREEN_HUE, 255)
            if event == '-BLUE-':
                set_rgb_color(dev, BLUE_HUE, 255)
            if event == '-WHITE-':
                set_rgb_color(dev, None, 0)
            if event == '-OFF-':
                window['-RGB-BRIGHTNESS-'].Update(0)
                rgb_brightness(dev, 0)

            if event == '-SAVE-':
                save(dev)

            if event == '-CLEAR-EEPROM-':
                eeprom_reset(dev)

        if event == sg.WIN_CLOSED:
            break

    window.close()


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

    res_path = resource_path()
    versions = listdir(os.path.join(res_path, "releases"))
    releases = {}
    for version in versions:
        path = join(res_path, "releases", version)
        releases[version] = {}
        for filename in listdir(path):
            if not isfile(join(path, filename)):
                continue
            type_search = re.search('framework_(.*)_default.*\.uf2', filename)
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

        fw_ver = device_dict["release_number"]

        if (os.name == 'nt' and device_dict['usage_page'] == RAW_USAGE_PAGE) or verbose:
            if show:
                print(f"Manufacturer: {manufacturer}")
                print(f"Product:      {product}")
                print("FW Version:   {}".format(format_fw_ver(fw_ver)))
                print(f"Serial No:    {sn}")

            if verbose:
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

        out_data = h.read(out_len)
        return out_data
    except IOError as ex:
        print(ex)
        sys.exit(1)

def set_keyboard_value(dev, value, number):
    msg = [value, number]
    send_message(dev, SET_KEYBOARD_VALUE, msg, 0)

def set_rgb_u8(dev, value, value_data):
    msg = [CHANNEL_RGB_MATRIX, value, value_data]
    send_message(dev, CUSTOM_SET_VALUE, msg, 0)

def get_rgb_u8(dev, value):
    msg = [CHANNEL_RGB_MATRIX, value]
    output = send_message(dev, CUSTOM_SET_VALUE, msg, 3)
    print("output", output)
    return output[2]

def get_backlight(dev, value, value_data):
    msg = [CHANNEL_BACKLIGHT, value]
    output = send_message(dev, CUSTOM_SET_VALUE, msg, 3)
    print(output[2])
    return output[2]

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


def rgb_brightness(dev, brightness):
    set_rgb_u8(dev, RGB_MATRIX_VALUE_BRIGHTNESS, brightness)
    #brightness = get_rgb_u8(dev, RGB_MATRIX_VALUE_BRIGHTNESS)
    #print(f"New Brightness: {brightness}")


def brightness(dev, brightness):
    set_backlight(dev, BACKLIGHT_VALUE_BRIGHTNESS, brightness)
    #brightness = get_backlight(dev, BACKLIGHT_VALUE_BRIGHTNESS)
    #print(f"New Brightness: {brightness}")


def set_rgb_color(dev, hue, saturation):
    if not hue:
        # TODO: Just choose current hue
        hue = 0
    msg = [CHANNEL_RGB_MATRIX, RGB_MATRIX_VALUE_COLOR, hue, saturation]
    send_message(dev, CUSTOM_SET_VALUE, msg, 0)


def restart_hint():
    sg.Popup('After updating a device, \nrestart the application\nto reload the connections.')


def flash_firmware(dev, fw_path):
    print(f"Flashing {fw_path}")

    # First jump to bootloader
    drives = uf2conv.list_drives()
    if not drives:
        print("jump to bootloader")
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


if __name__ == "__main__":
    devices = find_devs(show=False, verbose=False)
    print("Found {} devices".format(len(devices)))

    main(devices)
