//! Implementing the VIA protocol supported by QMK keyboard firmware

use hidapi::HidDevice;

use crate::raw_hid::*;

#[repr(u8)]
pub enum ViaCommandId {
    GetProtocolVersion = 0x01, // always 0x01
    GetKeyboardValue = 0x02,
    SetKeyboardValue = 0x03,
    //DynamicKeymapGetKeycode         = 0x04,
    //DynamicKeymapSetKeycode         = 0x05,
    //DynamicKeymapReset              = 0x06,
    CustomSetValue = 0x07,
    CustomGetValue = 0x08,
    //CustomSave                      = 0x09,
    EepromReset = 0x0A,
    BootloaderJump = 0x0B,
    //DynamicKeymapMacroGetCount      = 0x0C,
    //DynamicKeymapMacroGetBufferSize = 0x0D,
    //DynamicKeymapMacroGetBuffer     = 0x0E,
    //DynamicKeymapMacroSetBuffer     = 0x0F,
    //DynamicKeymapMacroReset         = 0x10,
    //DynamicKeymapGetLayerCount      = 0x11,
    //DynamicKeymapGetBuffer          = 0x12,
    //DynamicKeymapSetBuffer          = 0x13,
    //DynamicKeymapGetEncoder         = 0x14,
    //DynamicKeymapSetEncoder         = 0x15,
    //Unhandled                       = 0xFF,
}

pub enum ViaKeyboardValueId {
    Uptime = 0x01,
    LayoutOptions = 0x02,
    SwitchMatrixState = 0x03,
    FirmwareVersion = 0x04,
    DeviceIndication = 0x05,
}

pub enum ViaChannelId {
    //CustomChannel    = 0,
    BacklightChannel = 1,
    //RgblightChannel  = 2,
    RgbMatrixChannel = 3,
    //AudioChannel     = 4,
}

pub enum ViaBacklightValue {
    Brightness = 1,
    Effect = 2,
}

//enum ViaRgbLightValue {
//    Brightness  = 1,
//    Effect      = 2,
//    EffectSpeed = 3,
//    Color       = 4,
//}

pub enum ViaRgbMatrixValue {
    Brightness = 1,
    Effect = 2,
    EffectSpeed = 3,
    Color = 4,
}

/// Get the VIA protocol version. Latest one is 0x000B
pub fn get_protocol_ver(dev: &HidDevice) -> Result<u16, ()> {
    let output = send_message(dev, ViaCommandId::GetProtocolVersion as u8, None, 2)?;
    debug_assert_eq!(output.len(), 2);
    Ok(u16::from_be_bytes(output.try_into().unwrap()))
}

pub fn get_keyboard_value(dev: &HidDevice, value: ViaKeyboardValueId) -> Result<u32, ()> {
    // Must skip the first byte from the output, as we're sending a message of 1 and it's preserved in the output
    let msg = vec![value as u8];
    let output = send_message(dev, ViaCommandId::GetKeyboardValue as u8, Some(&msg), 5)?;
    assert_eq!(output.len(), 5);
    Ok(u32::from_be_bytes(output[1..5].try_into().unwrap()))
}

pub fn set_keyboard_value(
    dev: &HidDevice,
    value: ViaKeyboardValueId,
    number: u32,
) -> Result<(), ()> {
    assert!(number < (1 << 8)); // TODO: Support u32
    let msg = vec![value as u8, number as u8];
    send_message(dev, ViaCommandId::SetKeyboardValue as u8, Some(&msg), 0)?;
    Ok(())
}

pub fn get_rgb_u8(dev: &HidDevice, value: u8) -> Result<u8, ()> {
    let msg = vec![ViaChannelId::RgbMatrixChannel as u8, value];
    let output = send_message(dev, ViaCommandId::CustomGetValue as u8, Some(&msg), 3)?;
    //println!("Current value: {:?}", output);
    Ok(output[2])
}

pub fn set_rgb_u8(dev: &HidDevice, value: u8, value_data: u8) -> Result<(), ()> {
    // data = [ command_id, channel_id, value_id, value_data ]
    let msg = vec![ViaChannelId::RgbMatrixChannel as u8, value, value_data];
    send_message(dev, ViaCommandId::CustomSetValue as u8, Some(&msg), 0)?;
    Ok(())
}

pub fn set_rgb_color(dev: &HidDevice, hue: Option<u8>, saturation: Option<u8>) -> Result<(), ()> {
    let (cur_hue, cur_saturation) = get_rgb_color(dev).unwrap();

    let hue = hue.unwrap_or(cur_hue);
    let saturation = saturation.unwrap_or(cur_saturation);

    let msg = vec![
        ViaChannelId::RgbMatrixChannel as u8,
        ViaRgbMatrixValue::Color as u8,
        hue,
        saturation,
    ];
    send_message(dev, ViaCommandId::CustomSetValue as u8, Some(&msg), 0)?;

    Ok(())
}

pub fn get_rgb_color(dev: &HidDevice) -> Result<(u8, u8), ()> {
    let msg = vec![
        ViaChannelId::RgbMatrixChannel as u8,
        ViaRgbMatrixValue::Color as u8,
    ];
    let output = send_message(dev, ViaCommandId::CustomGetValue as u8, Some(&msg), 4)?;
    Ok((output[2], output[3]))
}

pub fn get_backlight(dev: &HidDevice, value: u8) -> Result<u8, ()> {
    let msg = vec![ViaChannelId::BacklightChannel as u8, value];
    let output = send_message(dev, ViaCommandId::CustomGetValue as u8, Some(&msg), 3)?;
    Ok(output[2])
}

pub fn set_backlight(dev: &HidDevice, value: u8, value_data: u8) -> Result<(), ()> {
    let msg = vec![ViaChannelId::BacklightChannel as u8, value, value_data];
    send_message(dev, ViaCommandId::CustomSetValue as u8, Some(&msg), 0)?;
    Ok(())
}

pub fn eeprom_reset(dev: &HidDevice) -> Result<(), ()> {
    let output = send_message(dev, ViaCommandId::EepromReset as u8, None, 0)?;
    debug_assert_eq!(output.len(), 0);
    Ok(())
}

pub fn bootloader_jump(dev: &HidDevice) -> Result<(), ()> {
    let output = send_message(dev, ViaCommandId::BootloaderJump as u8, None, 0)?;
    debug_assert_eq!(output.len(), 0);
    Ok(())
}
