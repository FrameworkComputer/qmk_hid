#!/usr/bin/env python3
import os
import sys
import subprocess
import time

import PySimpleGUI as sg
import hid
if os.name == 'nt':
    from win32api import GetKeyState, keybd_event
    from win32con import VK_NUMLOCK, VK_CAPITAL

import uf2conv

# TODO:
# - Get current values
#   - Set sliders to current values

PROGRAM_VERSION = "0.1.9"
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

def debug_print(args=""):
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
            output = subprocess.run(['numlockx', 'status'], stdout=subprocess.PIPE).stdout
            if b'on' in output:
                return True
            elif b'off' in output:
                return False
        except FileNotFoundError:
            # Ignore tool not found, just return None
            pass


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
        [sg.Text("Backlight Brightness")],
        # TODO: Get default from device
        [sg.Slider((0, 255), orientation='h', default_value=120,
                   k='-BRIGHTNESS-', enable_events=True)],
        #[sg.Button("Enable Breathing", k='-ENABLE-BREATHING-')],
        #[sg.Button("Disable Breathing", k='-DISABLE-BREATHING-')],

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
        [sg.Text("State: "), sg.Text("", k='-NUMLOCK-STATE-'), sg.Push() ,sg.Button("Refresh", k='-NUMLOCK-REFRESH-', disabled=True)],
        [sg.Button("Send Numlock Toggle", k='-NUMLOCK-TOGGLE-', disabled=True)],

        [sg.HorizontalSeparator()],
        [
            sg.Column([
                [sg.Text("BIOS Mode")],
                [sg.Button("Enable", k='-BIOS-MODE-ENABLE-'), sg.Button("Disable", k='-BIOS-MODE-DISABLE-')],
            ]),
            sg.VSeperator(),
            sg.Column([
                [sg.Text("Factory Mode")],
                [sg.Button("Enable", k='-FACTORY-MODE-ENABLE-'), sg.Button("Disable", k='-FACTORY-MODE-DISABLE-')],
            ])
        ],

        [sg.HorizontalSeparator()],
        [sg.Text("Save Settings")],
        [sg.Button("Save", k='-SAVE-'), sg.Button("Clear EEPROM", k='-CLEAR-EEPROM-')],
        [sg.Text(f"Program Version: {PROGRAM_VERSION}")],
    ]

    icon_path = None
    if os.name == 'nt':
        ICON_NAME = 'logo_cropped_transparent_keyboard_48x48.ico'
        icon_path = os.path.join(resource_path(), 'res', ICON_NAME) if is_pyinstaller() else os.path.join('res', ICON_NAME)
    window = sg.Window("QMK Keyboard Control", layout, finalize=True, icon=icon_path)

    selected_devices = []

    # Optionally sync brightness between keyboards
    # window.start_thread(lambda: backlight_watcher(window, devices), (THREAD_KEY, THREAD_EXITING))
    window.start_thread(lambda: periodic_event(window), (THREAD_KEY, THREAD_EXITING))

    while True:
        numlock_on = get_numlock_state()
        if numlock_on is None and os != 'nt':
            window['-NUMLOCK-STATE-'].update("Unknown, please install the 'numlockx' command")
        else:
            window['-NUMLOCK-REFRESH-'].update(disabled=False)
            window['-NUMLOCK-TOGGLE-'].update(disabled=False)
            window['-NUMLOCK-STATE-'].update("On (Numbers)" if numlock_on else "Off (Arrows)")

        event, values = window.read()
        # print('Event', event)
        # print('Values', values)

        for dev in devices:
            debug_print("Dev {} is {}".format(dev['product_string'], dev.get('disconnected')))
            if 'disconnected' in dev:
                window['-CHECKBOX-{}-'.format(dev['path'])].update(False, disabled=True)

        selected_devices = [
            dev for dev in devices if
            values and values['-CHECKBOX-{}-'.format(dev['path'])]
        ]
        # print("Selected {} devices".format(len(selected_devices)))

        # Updating firmware
        if event == "-VERSION-":
            # After selecting a version, we can list the types of firmware available for this version
            types = list(releases[values['-VERSION-']])
            window['-TYPE-'].update(value=types[0], values=types)
        if event == "-TYPE-":
            # Once the user has selected a type, the exact firmware file is known and can be flashed
            window['-FLASH-'].update(disabled=False)
        if event == "-FLASH-":
            if len(selected_devices) != 1:
                sg.Popup('To flash select exactly 1 device.')
                continue
            dev = selected_devices[0]
            ver = values['-VERSION-']
            t = values['-TYPE-']
            flash_firmware(dev, releases[ver][t])
            restart_hint()
            window['-CHECKBOX-{}-'.format(dev['path'])].update(False, disabled=True)

        if event == "-NUMLOCK-TOGGLE-":
            if os.name == 'nt':
                keybd_event(VK_NUMLOCK, 0x3A, 0x1, 0)
                keybd_event(VK_NUMLOCK, 0x3A, 0x3, 0)
            else:
                out = subprocess.check_output(['numlockx', 'toggle'])

        # Run commands on all selected devices
        for dev in selected_devices:
            if event == "-BOOTLOADER-":
                bootloader_jump(dev)
                window['-CHECKBOX-{}-'.format(dev['path'])].update(False, disabled=True)
                restart_hint()

            if event == "-BIOS-MODE-ENABLE-":
                bios_mode(dev, True)
            if event == "-BIOS-MODE-DISABLE-":
                bios_mode(dev, False)

            if event == "-FACTORY-MODE-ENABLE-":
                factory_mode(dev, True)
            if event == "-FACTORY-MODE-DISABLE-":
                factory_mode(dev, False)

            if event == '-BRIGHTNESS-':
                set_brightness(dev, int(values['-BRIGHTNESS-']))
                set_rgb_brightness(dev, int(values['-BRIGHTNESS-']))

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
                set_rgb_brightness(dev, 0)

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


THREAD_KEY = '-THREAD-'
THREAD_EXITING = '-THREAD EXITING-'
def periodic_event(window):
    while True:
        window.write_event_value('-PERIODIC-EVENT-', None)
        time.sleep(1)


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
        dev['disconnected'] = True
        debug_print("Error: ", ex)
        # Doesn't actually exit the process, pysimplegui catches it
        # But it avoids the return value being used
        # TODO: Get rid of this ugly hack and properly make the caller handle the failure
        sys.exit(1)

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


def set_rgb_color(dev, hue, saturation):
    (cur_hue, cur_sat) = get_rgb_color(dev)
    if not hue:
        hue = cur_hue
    msg = [CHANNEL_RGB_MATRIX, RGB_MATRIX_VALUE_COLOR, hue, saturation]
    send_message(dev, CUSTOM_SET_VALUE, msg, 0)


def restart_hint():
    sg.Popup('After updating a device, \nrestart the application\nto reload the connections.')


def flash_firmware(dev, fw_path):
    print(f"Flashing {fw_path}")

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


if __name__ == "__main__":
    devices = find_devs(show=False, verbose=False)
    print("Found {} devices".format(len(devices)))

    main(devices)
