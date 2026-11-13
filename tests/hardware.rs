//! Opt-in tests for attached Framework modules. Never save settings to EEPROM.
use qmk_hid::{new_hidapi, raw_hid::RAW_USAGE_PAGE, via::*};

#[test]
#[ignore = "requires attached Framework ANSI keyboard and RGB macropad"]
fn lighting_round_trip() {
    let api = new_hidapi().unwrap();
    for (pid, rgb) in [(0x0012, false), (0x0013, true)] {
        let info = api
            .device_list()
            .find(|d| {
                d.vendor_id() == 0x32ac && d.product_id() == pid && d.usage_page() == RAW_USAGE_PAGE
            })
            .expect("required module is not attached");
        let dev = info.open_device(&api).unwrap();
        assert!(get_protocol_ver(&dev).unwrap() > 0);
        let get = || {
            if rgb {
                get_rgb_u8(&dev, 1)
            } else {
                get_backlight(&dev, 1)
            }
        };
        let set = |value| {
            if rgb {
                set_rgb_u8(&dev, 1, value)
            } else {
                set_backlight(&dev, 1, value)
            }
        };
        let original = get().unwrap();
        let result = set(255).and_then(|()| get());
        let restored = set(original).and_then(|()| get());
        assert_eq!(restored.unwrap(), original, "failed to restore {pid:04x}");
        assert_eq!(
            result.unwrap(),
            if rgb { 254 } else { 255 },
            "brightness round trip for {pid:04x}"
        );
        if rgb {
            let original = get_rgb_color(&dev).unwrap();
            let result =
                set_rgb_color(&dev, Some(85), Some(200)).and_then(|()| get_rgb_color(&dev));
            let restored = set_rgb_color(&dev, Some(original.0), Some(original.1))
                .and_then(|()| get_rgb_color(&dev));
            assert_eq!(restored.unwrap(), original);
            assert_eq!(result.unwrap(), (85, 200));
        }
    }
}
