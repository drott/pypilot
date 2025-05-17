from evdev import InputDevice, list_devices

def select_device(device_path):
    """
    Selects a device based on the provided path or MAC address.
    """
    try:
        if '/' in device_path:
            device = InputDevice(device_path)
        else:
            devices = [InputDevice(path) for path in list_devices()]
            device = next((dev for dev in devices if dev.uniq == device_path), None)
            if device is None:
                raise FileNotFoundError(f"No device with uniq '{device_path}' found.")
        return device
    except FileNotFoundError:
        print(f"Device not found: {device_path}")
        return None

def select_device_interactive():
    """
    Interactively select a device from the list of available devices.
    """
    devices = [InputDevice(path) for path in list_devices()]
    print("Available devices:")
    for idx, device in enumerate(devices):
        print(f"{idx}: {device.name} (Path: {device.path}, Unique ID: {device.uniq})")

    try:
        device_index = int(input("Enter the number of the device you want to select: "))
        if 0 <= device_index < len(devices):
            return devices[device_index]
        else:
            print("Invalid number. Please try again.")
            return None
    except ValueError:
        print("Invalid input. Please enter a number.")
        return None