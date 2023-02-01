use hidapi::HidDevice;

use crate::raw_hid::send_message;
use crate::via::ViaCommandId;

/// Send a factory command, currently only supported in Lotus
pub fn send_factory_command(dev: &HidDevice, command: u8, value: u8) -> Result<(), ()> {
    let msg = vec![command, value];
    let _ = send_message(dev, ViaCommandId::BootloaderJump as u8, Some(&msg), 0)?;
    Ok(())
}
