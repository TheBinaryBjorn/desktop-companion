import time
import requests
from zeroconf import ServiceBrowser, ServiceStateChange, Zeroconf

discovered_wleds = {}

def _on_service_state_change(zeroconf, service_type, name, state_change):
    if state_change is ServiceStateChange.Added:
        info = zeroconf.get_service_info(service_type, name)
        if info and info.parsed_addresses():
            ip = info.parsed_addresses()[0]
            # Clean up the mDNS name (e.g., "wled-kitchen._wled._tcp.local." -> "wled-kitchen")
            clean_name = name.split(".")[0].lower()
            discovered_wleds[clean_name] = ip
            print(f"[WLED Scanner] Found {clean_name} at {ip}")

def scan_for_devices(timeout_seconds=4):
    print("Scanning local network for WLED devices...")
    zc = Zeroconf()
    browser = ServiceBrowser(zc, "_wled._tcp.local.", handlers=[_on_service_state_change])
    time.sleep(timeout_seconds)
    zc.close()
    print(f"[WLED Scanner] Scan complete. Devices ready: {list(discovered_wleds.keys())}")

def control_wled(device_name: str, power_state: bool, brightness: int, r: int, g: int, b: int) -> str:
    """
    Controls a WLED light strip.
    
    Args:
        device_name: The name of the light (e.g., 'wled-kitchen').
        power_state: True to turn on, False to turn off.
        brightness: Integer from 1 to 255.
        r: Red color value (0-255).
        g: Green color value (0-255).
        b: Blue color value (0-255).
    """
    target_ip = discovered_wleds.get(device_name.lower())
    
    if not target_ip:
        return f"Error: Device {device_name} not found on the network."

    url = f"http://{target_ip}/json/state"
    payload = {
        "on": power_state,
        "bri": brightness,
        "seg": [{"col": [[r, g, b]]}]
    }
    
    try:
        response = requests.post(url, json=payload, timeout=3)
        if response.status_code == 200:
            return f"Successfully updated {device_name}."
        else:
            return f"Failed to update {device_name}. Status: {response.status_code}"
    except Exception as e:
        return f"Network error when contacting {device_name}: {e}"