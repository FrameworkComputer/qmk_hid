mod factory;
mod keycodes;
mod raw_hid;
mod via;

use std::{thread, time::Duration};

use clap::{Parser, Subcommand};

extern crate hidapi;

use hidapi::{DeviceInfo, HidApi, HidDevice};

use crate::factory::*;
use crate::keycodes::*;
use crate::raw_hid::*;
use crate::via::*;

#[derive(Subcommand, Debug)]
enum Commands {
    Factory(FactorySubcommand),
    Via(ViaSubcommand),
    Qmk(QmkSubcommand),
}

#[derive(Clone, Copy, Debug, PartialEq, clap::ValueEnum)]
enum Color {
    /// 0° and 255° => 0
    Red,
    /// Yellow (120°) => 43
    Yellow,
    /// Green (120°) => 85
    Green,
    /// Cyan (180°) => 125
    Cyan,
    /// Blue (240°) => 170
    Blue,
    /// Purple (300°) => 213
    Purple,
    /// Saturation 0
    White,
}

/// Factory
#[derive(Parser, Debug)]
#[command(arg_required_else_help = true)]
struct FactorySubcommand {
    /// Emulate keypress
    #[arg(long)]
    keycode: Option<u16>,

    /// Emulate keypress of all keycodes, one after the other
    #[arg(long)]
    all_keycodes: bool,

    /// Light up single LED
    #[arg(long)]
    led: Option<u8>,
}

/// QMK
#[derive(Parser, Debug)]
#[command(arg_required_else_help = true)]
struct QmkSubcommand {
    /// Listen to the console. Better to use `qmk console` (https://github.com/qmk/qmk_cli)
    #[arg(short, long)]
    console: bool,
}

/// Via
#[derive(Parser, Debug)]
#[command(arg_required_else_help = true)]
struct ViaSubcommand {
    /// Show protocol version
    #[arg(long)]
    version: bool,

    /// Get device information
    #[arg(long)]
    info: bool,

    /// Flash device indication (backlight) 3x
    #[arg(long)]
    device_indication: bool,

    /// Set RGB brightness percentage or get, if no value provided
    #[arg(long)]
    rgb_brightness: Option<Option<u8>>,

    /// Set RGB effect or get, if no value provided
    #[arg(long)]
    rgb_effect: Option<Option<u8>>,

    /// Set RGB effect speed or get, if no value provided (0-255)
    #[arg(long)]
    rgb_effect_speed: Option<Option<u8>>,

    /// Set RGB hue or get, if no value provided. (0-255)
    #[arg(long)]
    rgb_hue: Option<Option<u8>>,

    /// Set RGB color
    #[arg(long)]
    #[clap(value_enum)]
    rgb_color: Option<Color>,

    /// Set RGB saturation or get, if no value provided. (0-255)
    #[arg(long)]
    rgb_saturation: Option<Option<u8>>,

    /// Set backlight brightness percentage or get, if no value provided
    #[arg(long)]
    backlight: Option<Option<u8>>,

    /// Set backlight breathing or get, if no value provided
    #[arg(long)]
    backlight_breathing: Option<Option<bool>>,

    // TODO:
    // - RGB light
    // - LED matrix
    // - audio
    /// Reset the EEPROM contents (Not supported by all firmware)
    #[arg(long)]
    eeprom_reset: bool,

    /// Jump to the bootloader
    #[arg(long)]
    bootloader: bool,
}

/// RAW HID and VIA commandline for QMK devices
#[derive(Parser, Debug)]
#[command(version, arg_required_else_help = true)]
struct ClapCli {
    #[command(subcommand)]
    command: Option<Commands>,

    /// List connected HID devices
    #[arg(short, long)]
    list: bool,

    /// Verbose outputs to the console
    #[arg(short, long)]
    verbose: bool,

    /// VID (Vendor ID) in hex digits
    #[arg(long)]
    vid: Option<String>,

    /// PID (Product ID) in hex digits
    #[arg(long)]
    pid: Option<String>,
}

const QMK_INTERFACE: i32 = 0x01;

struct Found {
    raw_usages: Vec<DeviceInfo>,
    console_usages: Vec<DeviceInfo>,
}

/// Format BCD version
///
/// # Examples
///
/// ```
/// let ver = format_bcd(0x0213);
/// assert_eq!(ver, "2.1.3");
/// ```
fn format_bcd(bcd: u16) -> String {
    let bytes = bcd.to_be_bytes();
    let major = bytes[0];
    let minor = (bytes[1] & 0xF0) >> 4;
    let patch = bytes[1] & 0x0F;
    format!("{major}.{minor}.{patch}")
}

const NOT_SET: &str = "NOT SET";

fn find_devices(api: &HidApi, args: &ClapCli) -> Found {
    let mut found: Found = Found {
        raw_usages: vec![],
        console_usages: vec![],
    };
    for dev_info in api.device_list() {
        let vid = dev_info.vendor_id();
        let pid = dev_info.product_id();
        let interface = dev_info.interface_number();

        // Print device information
        let usage_page = dev_info.usage_page();
        if ![RAW_USAGE_PAGE, CONSOLE_USAGE_PAGE].contains(&usage_page) {
            continue;
        }

        if (args.list && usage_page == RAW_USAGE_PAGE) || args.verbose {
            println!("{vid:04x}:{pid:04x}");
            let fw_ver = dev_info.release_number();
            println!(
                "  Manufacturer: {:?}",
                dev_info.manufacturer_string().unwrap_or(NOT_SET)
            );
            println!(
                "  Product:      {:?}",
                dev_info.product_string().unwrap_or(NOT_SET)
            );
            println!("  FW Version:   {}", format_bcd(fw_ver));
            println!(
                "  Serial No:    {:?}",
                dev_info.serial_number().unwrap_or(NOT_SET)
            );

            if args.verbose {
                println!("  VID/PID:      {vid:04x}:{pid:04x}");
                println!("  Interface:    {}", dev_info.interface_number());
                println!("  Path:         {:?}", dev_info.path());
                print!("  Usage Page:   0x{:04X}", dev_info.usage_page());
                match usage_page {
                    RAW_USAGE_PAGE => println!(" (RAW_USAGE_PAGE)"),
                    CONSOLE_USAGE_PAGE => println!(" (CONSOLE_USAGE_PAGE)"),
                    G_DESK_USAGE_PAGE => println!(" (Generic Desktop Usage Page)"),
                    CONSUMER_USAGE_PAGE => println!(" (CONSUMER_USAGE_PAGE)"),
                    _ => println!(),
                }
            }
        }

        // TODO: Use clap-num for this
        let args_vid = args
            .vid
            .as_ref()
            .map(|s| u16::from_str_radix(s, 16).unwrap());
        let args_pid = args
            .pid
            .as_ref()
            .map(|s| u16::from_str_radix(s, 16).unwrap());

        // If filtering for specific VID or PID, skip all that don't match
        if let Some(args_vid) = args_vid {
            if vid != args_vid {
                continue;
            }
        }
        if let Some(args_pid) = args_pid {
            if pid != args_pid {
                continue;
            }
        }

        match usage_page {
            RAW_USAGE_PAGE => {
                if interface != QMK_INTERFACE {
                    println!(
                        "Something is wrong with {vid}:{pid}. The interface isn't {QMK_INTERFACE}"
                    );
                } else {
                    found.raw_usages.push(dev_info.clone());
                }
            }
            CONSOLE_USAGE_PAGE => {
                found.console_usages.push(dev_info.clone());
            }
            _ => {}
        }
    }

    found
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let args = ClapCli::parse_from(args);

    match HidApi::new() {
        Ok(api) => {
            let found = find_devices(&api, &args);

            let dev_infos = match args.command {
                Some(Commands::Qmk(_)) => found.console_usages,
                Some(_) => found.raw_usages,
                None => return,
            };

            if dev_infos.is_empty() {
                println!("No device found");
            } else if dev_infos.len() == 1 {
                use_device(&args, &api, dev_infos.first().unwrap());
            } else {
                println!("More than 1 device found. Select a specific device with --vid and --pid");
            }
        }
        Err(e) => {
            eprintln!("Error: {e}");
        }
    };
}

fn all_keycodes(device: &HidDevice) {
    let ansi = [
        KC_ESC, KC_F1, KC_F2, KC_F3, KC_F4, KC_F5, KC_F6, KC_F7, KC_F8, KC_F9, KC_F10, KC_F11,
        KC_F12, KC_DEL, KC_GRV, KC_1, KC_2, KC_3, KC_4, KC_5, KC_6, KC_7, KC_8, KC_9, KC_0,
        KC_MINS, KC_EQL, KC_BSPC, KC_TAB, KC_Q, KC_W, KC_E, KC_R, KC_T, KC_Y, KC_U, KC_I, KC_O,
        KC_P, KC_LBRC, KC_RBRC, KC_BSLS, KC_CAPS, KC_A, KC_S, KC_D, KC_F, KC_G, KC_H, KC_J, KC_K,
        KC_L, KC_SCLN, KC_QUOT, KC_ENT, KC_LSFT, KC_Z, KC_X, KC_C, KC_V, KC_B, KC_N, KC_M, KC_COMM,
        KC_DOT, KC_SLSH, KC_RSFT, KC_LCTL, KC_LGUI, KC_LALT, KC_SPC, KC_RALT, KC_RCTL, KC_LEFT,
        KC_UP, KC_DOWN, KC_RGHT,
    ];
    for keycode in ansi {
        println!("Emulating keycode: {keycode}");
        send_factory_command(device, 0x01, keycode).unwrap();
        thread::sleep(Duration::from_millis(100));
    }
}

fn use_device(args: &ClapCli, api: &HidApi, dev_info: &DeviceInfo) {
    let vid = dev_info.vendor_id();
    let pid = dev_info.product_id();
    let interface = dev_info.interface_number();

    if args.verbose {
        println!("Connecting to {vid:04X}:{pid:04X} Interface: {interface}");
    }

    let device = dev_info.open_device(api).unwrap();

    match &args.command {
        Some(Commands::Factory(args)) => {
            if let Some(keycode) = args.keycode {
                println!("Emulating keycode: {keycode}");
                send_factory_command(&device, 0x01, keycode as u8).unwrap();
            }
            if let Some(led) = args.led {
                println!("Lighting up LED: {led}");
                send_factory_command(&device, 0x02, led).unwrap();
            }
            if args.all_keycodes {
                all_keycodes(&device);
            }
        }
        Some(Commands::Qmk(args)) => {
            if args.console {
                qmk_console(&device);
            }
        }
        Some(Commands::Via(args)) => {
            if args.version {
                let prot_ver = get_protocol_ver(&device).unwrap();
                println!("Protocol Version: {prot_ver:04X}");
            } else if args.eeprom_reset {
                eeprom_reset(&device).unwrap();
            } else if args.bootloader {
                bootloader_jump(&device).unwrap();
            } else if args.info {
                let prot_ver = get_protocol_ver(&device).unwrap();
                let uptime = get_keyboard_value(&device, ViaKeyboardValueId::Uptime).unwrap();
                let layout_opts =
                    get_keyboard_value(&device, ViaKeyboardValueId::LayoutOptions).unwrap();
                let matrix_state =
                    get_keyboard_value(&device, ViaKeyboardValueId::SwitchMatrixState).unwrap();
                let fw_ver =
                    get_keyboard_value(&device, ViaKeyboardValueId::FirmwareVersion).unwrap();

                println!("Protocol Version:     {prot_ver:04X}");
                println!("Uptime:               {:?}s", uptime / 1000);
                println!("Layout Options:       {layout_opts:?}");
                println!("Switch Matrix State:  {matrix_state:?}"); // TODO: Decode
                println!("VIA Firmware Version: {fw_ver:?}");
            } else if args.device_indication {
                // Works with RGB and single zone backlight keyboards
                // Device indication doesn't work well with all effects
                // So it's best to save the currently configured one, switch to solid color and later back.
                let cur_effect = get_rgb_u8(&device, ViaRgbMatrixValue::Effect as u8).unwrap();
                // Solid effect is always 1
                set_rgb_u8(&device, ViaRgbMatrixValue::Effect as u8, 1).unwrap();

                // QMK recommends to repeat this 6 times, every 200ms
                for _ in 0..6 {
                    set_keyboard_value(&device, ViaKeyboardValueId::DeviceIndication, 0).unwrap();
                    thread::sleep(Duration::from_millis(200));
                }

                // Restore effect
                set_rgb_u8(&device, ViaRgbMatrixValue::Effect as u8, cur_effect).unwrap();
            } else if let Some(arg_brightness) = args.rgb_brightness {
                if let Some(percentage) = arg_brightness {
                    let brightness = (255.0 * percentage as f32) / 100.0;
                    set_rgb_u8(
                        &device,
                        ViaRgbMatrixValue::Brightness as u8,
                        brightness.round() as u8,
                    )
                    .unwrap();
                }
                let brightness = get_rgb_u8(&device, ViaRgbMatrixValue::Brightness as u8).unwrap();
                let percentage = (100.0 * brightness as f32) / 255.0;
                println!("Brightness: {}%", percentage.round())
            } else if let Some(arg_effect) = args.rgb_effect {
                if let Some(effect) = arg_effect {
                    set_rgb_u8(&device, ViaRgbMatrixValue::Effect as u8, effect).unwrap();
                }
                let effect = get_rgb_u8(&device, ViaRgbMatrixValue::Effect as u8).unwrap();
                println!("Effect: {effect}")
            } else if let Some(arg_speed) = args.rgb_effect_speed {
                if let Some(speed) = arg_speed {
                    set_rgb_u8(&device, ViaRgbMatrixValue::EffectSpeed as u8, speed).unwrap();
                }
                let speed = get_rgb_u8(&device, ViaRgbMatrixValue::EffectSpeed as u8).unwrap();
                println!("Effect Speed: {speed}")
            } else if let Some(arg_saturation) = &args.rgb_saturation {
                if let Some(saturation) = arg_saturation {
                    set_rgb_color(&device, None, Some(*saturation)).unwrap();
                }
                let (hue, saturation) = get_rgb_color(&device).unwrap();
                println!("Color Hue:        {hue}");
                println!("Color Saturation: {saturation}");
            } else if let Some(arg_hue) = &args.rgb_hue {
                if let Some(hue) = arg_hue {
                    set_rgb_color(&device, Some(*hue), None).unwrap();
                }
                let (hue, saturation) = get_rgb_color(&device).unwrap();
                println!("Color Hue:        {hue}");
                println!("Color Saturation: {saturation}");
            } else if let Some(color) = &args.rgb_color {
                if let Color::White = color {
                    set_rgb_color(&device, None, Some(0)).unwrap();
                } else {
                    set_rgb_color(&device, Some(color_as_hue(*color)), Some(255)).unwrap();
                }
                let (hue, saturation) = get_rgb_color(&device).unwrap();
                println!("Color Hue:        {hue}");
                println!("Color Saturation: {saturation}");
            } else if let Some(arg_backlight) = args.backlight {
                if let Some(percentage) = arg_backlight {
                    let brightness = (255.0 * percentage as f32) / 100.0;
                    set_backlight(
                        &device,
                        ViaBacklightValue::Brightness as u8,
                        brightness.round() as u8,
                    )
                    .unwrap();
                }
                let brightness =
                    get_backlight(&device, ViaBacklightValue::Brightness as u8).unwrap();
                let percentage = (100.0 * brightness as f32) / 255.0;
                println!("Brightness: {}%", percentage.round())
            } else if let Some(arg_breathing) = args.backlight_breathing {
                if let Some(breathing) = arg_breathing {
                    set_backlight(&device, ViaBacklightValue::Effect as u8, breathing as u8)
                        .unwrap();
                }
                let breathing = get_backlight(&device, ViaBacklightValue::Effect as u8).unwrap();
                println!("Breathing: : {:?}", breathing == 1)
            //} else if args.rgb_matrix_save {
            // TODO
            //set_rgb_u8(&device, ViaRgbMatrixValue::Effect as u8, effect).unwrap();
            } else {
                println!("No command specified.");
            }
        }
        _ => {}
    }
}

fn color_as_hue(color: Color) -> u8 {
    match color {
        Color::Red => 0,
        Color::Yellow => 43,
        Color::Green => 85,
        Color::Cyan => 125,
        Color::Blue => 170,
        Color::Purple => 213,
        Color::White => 0, // Doesn't matter, only hue needs to be 0
    }
}
