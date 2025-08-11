use windows::Win32::Devices::DeviceAndDriverInstallation::{
    CM_Get_DevNode_Status, SetupDiChangeState, SetupDiEnumDeviceInfo, SetupDiGetClassDevsW,
    SetupDiGetDevicePropertyW, SetupDiSetClassInstallParamsW, CM_PROB_DISABLED, CR_SUCCESS,
    DICS_DISABLE, DICS_ENABLE, DICS_FLAG_GLOBAL, DIF_PROPERTYCHANGE, DIGCF_ALLCLASSES, HDEVINFO,
    SP_CLASSINSTALL_HEADER, SP_DEVINFO_DATA, SP_PROPCHANGE_PARAMS,
};
use windows::Win32::Devices::Properties::{DEVPKEY_Device_HardwareIds, DEVPROPTYPE};
use windows::{
    core::*, Devices::Enumeration::*, Foundation::*, Win32::Foundation::*,
    Devices::Lights::*,
    Win32::System::Threading::*,
};

// TODO:
// - [ ] Remove unsafe
// - [ ] Remove unnecessary imports
// - [ ] Print lamp array information
// - [ ] Print info about each lamp in the array
pub unsafe fn enumerate_lamparray() -> Result<()> {
    let selector = LampArray::GetDeviceSelector();
    let watcher = DeviceInformation::CreateWatcher(selector)?;

    watcher.Added(&TypedEventHandler::<DeviceWatcher, DeviceInformation>::new(
        |_, info| {
            let info = info.as_ref().expect("info");
            let name = info.Name()?;

            if name.to_string().contains("Intel") {
                println!("Id: {}, Name: {}", info.Id()?, info.Name()?);
            }
            Ok(())
        },
    ))?;

    watcher.EnumerationCompleted(&TypedEventHandler::new(move |_, _| {
        println!("done!");
        SetEvent(handle.0);
        Ok(())
    }))?;

    watcher.Start()?;
    WaitForSingleObject(handle.0, INFINITE);

    Ok(())
}
