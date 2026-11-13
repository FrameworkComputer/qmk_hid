use std::{thread, time::Duration};

use clap::{Parser, Subcommand};

extern crate hidapi;

use hidapi::{DeviceInfo, HidApi};

use qmk_hid::factory::*;
use qmk_hid::raw_hid::*;
use qmk_hid::via::*;
use qmk_hid::*;

#[derive(Subcommand, Debug)]
enum Commands {
    Factory(FactorySubcommand),
    Via(ViaSubcommand),
    Qmk(QmkSubcommand),
}

/// Factory
#[derive(Parser, Debug)]
#[command(arg_required_else_help = true)]
struct FactorySubcommand {
    /// Light up single LED
    #[arg(long)]
    led: Option<u8>,

    #[arg(short)]
    serialnum: bool,

    #[arg(long)]
    bios_mode: Option<bool>,

    #[arg(long)]
    factory_mode: Option<bool>,
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
#[command(group(clap::ArgGroup::new("operation")
    .args(["info", "device_indication", "eeprom_reset", "bootloader"])
    .conflicts_with_all(["rgb_brightness", "rgb_effect", "rgb_effect_speed", "rgb_hue", "rgb_color", "rgb_saturation", "backlight", "backlight_breathing", "save"])))]
struct ViaSubcommand {
    /// Get VIA protocol and config information (most likely NOT what you're looking for)
    #[arg(long)]
    info: bool,

    /// Flash device indication (backlight) 3x
    #[arg(long)]
    device_indication: bool,

    /// Set RGB brightness percentage or get, if no value provided
    #[arg(long, value_parser = clap::value_parser!(u8).range(0..=100))]
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
    #[arg(long, value_parser = clap::value_parser!(u8).range(0..=100))]
    backlight: Option<Option<u8>>,

    /// Set backlight breathing or get, if no value provided
    #[arg(long)]
    backlight_breathing: Option<Option<bool>>,

    /// Save RGB/backlight value, otherwise it won't persist through keyboard reboot. Can be used
    /// by itself or together with other argument.
    #[arg(long)]
    save: bool,

    // TODO:
    // - RGB light
    // - LED matrix
    // - audio
    /// Reset the EEPROM contents (Not supported by all firmware)
    #[arg(long)]
    eeprom_reset: bool,

    /// Jump to the bootloader (Not supported by all firmware)
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
    #[arg(long, value_parser = parse_usb_id)]
    vid: Option<String>,

    /// PID (Product ID) in hex digits
    #[arg(long, value_parser = parse_usb_id)]
    pid: Option<String>,
}

fn parse_usb_id(value: &str) -> Result<String, String> {
    u16::from_str_radix(value, 16)
        .map(|_| value.to_owned())
        .map_err(|_| "expected a 16-bit hexadecimal USB ID".to_owned())
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<String> = std::env::args().collect();
    let args = ClapCli::parse_from(args);

    match HidApi::new() {
        Ok(api) => {
            let found = find_devices(
                &api,
                args.list,
                args.verbose,
                args.vid.as_deref(),
                args.pid.as_deref(),
            );

            let dev_infos = match args.command {
                Some(Commands::Qmk(_)) => found.console_usages,
                Some(_) => found.raw_usages,
                None => return Ok(()),
            };

            if dev_infos.is_empty() {
                return Err("No device found".into());
            } else if dev_infos.len() == 1 {
                use_device(&args, &api, &dev_infos[0])?;
            } else {
                return Err(
                    "More than 1 device found. Select a specific device with --vid and --pid"
                        .into(),
                );
            }
        }
        Err(e) => {
            return Err(e.into());
        }
    };
    Ok(())
}

fn use_device(
    args: &ClapCli,
    api: &HidApi,
    dev_info: &DeviceInfo,
) -> Result<(), Box<dyn std::error::Error>> {
    let vid = dev_info.vendor_id();
    let pid = dev_info.product_id();
    let interface = dev_info.interface_number();

    if args.verbose {
        println!("Connecting to {vid:04X}:{pid:04X} Interface: {interface}");
    }

    let device = dev_info.open_device(api)?;

    match &args.command {
        Some(Commands::Factory(args)) => {
            if args.serialnum {
                send_factory_command(&device, 0x04, 0)?;
            }
            if let Some(bios_mode) = args.bios_mode {
                send_factory_command(&device, 0x05, bios_mode as u8)?;
            }
            if let Some(factory_mode) = args.factory_mode {
                send_factory_command(&device, 0x06, factory_mode as u8)?;
            }
            if let Some(led) = args.led {
                println!("Lighting up LED: {led}");
                send_factory_command(&device, 0x02, led)?;
            }
        }
        Some(Commands::Qmk(args)) => {
            if args.console {
                qmk_console(&device);
            }
        }
        Some(Commands::Via(args)) => {
            if args.eeprom_reset {
                eeprom_reset(&device)?;
            } else if args.bootloader {
                bootloader_jump(&device)?;
            } else if args.info {
                let prot_ver = get_protocol_ver(&device)?;
                let uptime = get_keyboard_value(&device, ViaKeyboardValueId::Uptime)?;
                let layout_opts = get_keyboard_value(&device, ViaKeyboardValueId::LayoutOptions)?;
                let matrix_state =
                    get_keyboard_value(&device, ViaKeyboardValueId::SwitchMatrixState)?;
                let fw_ver = get_keyboard_value(&device, ViaKeyboardValueId::FirmwareVersion)?;

                println!("Uptime:               {:?}s", uptime / 1000);
                println!("VIA Protocol Version: 0x{prot_ver:04X}");
                println!("Layout Options:       0x{layout_opts:08X}");
                println!("Switch Matrix State:  0x{matrix_state:08X}"); // TODO: Decode
                println!("VIA FWVER:            0x{fw_ver:08X}");
            } else if args.device_indication {
                // Works with RGB and single zone backlight keyboards
                // Device indication doesn't work well with all effects
                // So it's best to save the currently configured one, switch to solid color and later back.
                // Backlight-only modules do not implement the RGB channel.
                let cur_effect = get_rgb_u8(&device, ViaRgbMatrixValue::Effect as u8).ok();
                if cur_effect.is_some() {
                    set_rgb_u8(&device, ViaRgbMatrixValue::Effect as u8, 1)?;
                }
                let indication = (|| -> Result<(), QmkError> {
                    for _ in 0..6 {
                        set_keyboard_value(&device, ViaKeyboardValueId::DeviceIndication, 0)?;
                        thread::sleep(Duration::from_millis(200));
                    }
                    Ok(())
                })();
                // Attempt restoration even if indication failed.
                let restoration = if let Some(effect) = cur_effect {
                    set_rgb_u8(&device, ViaRgbMatrixValue::Effect as u8, effect)
                } else {
                    Ok(())
                };
                indication?;
                restoration?;
            }
            if let Some(arg_brightness) = args.rgb_brightness {
                if let Some(percentage) = arg_brightness {
                    let brightness = (255.0 * percentage as f32) / 100.0;
                    set_rgb_u8(
                        &device,
                        ViaRgbMatrixValue::Brightness as u8,
                        brightness.round() as u8,
                    )?;
                }
                let brightness = get_rgb_u8(&device, ViaRgbMatrixValue::Brightness as u8)?;
                let percentage = (100.0 * brightness as f32) / 255.0;
                println!("Brightness: {}%", percentage.round());
            }
            if let Some(arg_effect) = args.rgb_effect {
                if let Some(effect) = arg_effect {
                    set_rgb_u8(&device, ViaRgbMatrixValue::Effect as u8, effect)?;
                }
                let effect = get_rgb_u8(&device, ViaRgbMatrixValue::Effect as u8)?;
                println!("Effect: {effect}");
            }
            if let Some(arg_speed) = args.rgb_effect_speed {
                if let Some(speed) = arg_speed {
                    set_rgb_u8(&device, ViaRgbMatrixValue::EffectSpeed as u8, speed)?;
                }
                let speed = get_rgb_u8(&device, ViaRgbMatrixValue::EffectSpeed as u8)?;
                println!("Effect Speed: {speed}");
            }
            if let Some(arg_saturation) = &args.rgb_saturation {
                if let Some(saturation) = arg_saturation {
                    set_rgb_color(&device, None, Some(*saturation))?;
                }
                let (hue, saturation) = get_rgb_color(&device)?;
                println!("Color Hue:        {hue}");
                println!("Color Saturation: {saturation}");
            }
            if let Some(arg_hue) = &args.rgb_hue {
                if let Some(hue) = arg_hue {
                    set_rgb_color(&device, Some(*hue), None)?;
                }
                let (hue, saturation) = get_rgb_color(&device)?;
                println!("Color Hue:        {hue}");
                println!("Color Saturation: {saturation}");
            }
            if let Some(color) = &args.rgb_color {
                if let Color::White = color {
                    set_rgb_color(&device, None, Some(0))?;
                } else {
                    set_rgb_color(&device, Some(color_as_hue(*color)), Some(255))?;
                }
                let (hue, saturation) = get_rgb_color(&device)?;
                println!("Color Hue:        {hue}");
                println!("Color Saturation: {saturation}");
            }
            if let Some(arg_backlight) = args.backlight {
                if let Some(percentage) = arg_backlight {
                    let brightness = (255.0 * percentage as f32) / 100.0;
                    set_backlight(
                        &device,
                        ViaBacklightValue::Brightness as u8,
                        brightness.round() as u8,
                    )?;
                }
                let brightness = get_backlight(&device, ViaBacklightValue::Brightness as u8)?;
                let percentage = (100.0 * brightness as f32) / 255.0;
                println!("Brightness: {}%", percentage.round());
            }
            if let Some(arg_breathing) = args.backlight_breathing {
                if let Some(breathing) = arg_breathing {
                    set_backlight(&device, ViaBacklightValue::Effect as u8, breathing as u8)?;
                }
                let breathing = get_backlight(&device, ViaBacklightValue::Effect as u8)?;
                println!("Breathing: {:?}", breathing == 1);
            }
            if args.save {
                let rgb = args.rgb_brightness.is_some()
                    || args.rgb_effect.is_some()
                    || args.rgb_effect_speed.is_some()
                    || args.rgb_hue.is_some()
                    || args.rgb_color.is_some()
                    || args.rgb_saturation.is_some();
                let backlight = args.backlight.is_some() || args.backlight_breathing.is_some();
                if rgb {
                    save_rgb(&device)?;
                }
                if backlight {
                    save_backlight(&device)?;
                }
                if !rgb && !backlight {
                    save(true, &device)?;
                }
            }
        }
        _ => {}
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn validates_ids_and_percentages_before_opening_devices() {
        for args in [
            vec!["qmk_hid", "--vid", "xyz", "--list"],
            vec!["qmk_hid", "--pid", "10000", "--list"],
            vec!["qmk_hid", "via", "--backlight", "101"],
            vec!["qmk_hid", "via", "--rgb-brightness", "255"],
            vec!["qmk_hid", "via", "--bootloader", "--backlight", "50"],
        ] {
            assert!(ClapCli::try_parse_from(args).is_err());
        }
        assert!(
            ClapCli::try_parse_from([
                "qmk_hid",
                "via",
                "--rgb-brightness",
                "50",
                "--rgb-color",
                "red",
                "--save"
            ])
            .is_ok()
        );
    }
}
