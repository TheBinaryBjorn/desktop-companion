import time
import requests
from zeroconf import ServiceBrowser, ServiceStateChange, Zeroconf

discovered_wleds = {}
wled_effects = {"solid": 0} 
wled_palettes = {"default": 0} # 0 means "use the RGB color I passed in"

def _on_service_state_change(zeroconf, service_type, name, state_change):
    global wled_effects, wled_palettes
    if state_change is ServiceStateChange.Added:
        info = zeroconf.get_service_info(service_type, name)
        if info and info.parsed_addresses():
            ip = info.parsed_addresses()[0]
            clean_name = name.split(".")[0].lower()
            discovered_wleds[clean_name] = ip
            print(f"[WLED Scanner] Found {clean_name} at {ip}")
            
            # 1. Download Effects
            if len(wled_effects) <= 1:
                try:
                    response = requests.get(f"http://{ip}/json/eff", timeout=2)
                    if response.status_code == 200:
                        wled_effects = {eff.lower(): i for i, eff in enumerate(response.json())}
                        print(f"[WLED Scanner] Loaded {len(wled_effects)} effects.")
                except Exception as e:
                    print(f"[WLED Scanner] Could not fetch effects: {e}")
            
            # 2. Download Palettes
            if len(wled_palettes) <= 1:
                try:
                    response = requests.get(f"http://{ip}/json/pal", timeout=2)
                    if response.status_code == 200:
                        wled_palettes = {pal.lower(): i for i, pal in enumerate(response.json())}
                        print(f"[WLED Scanner] Loaded {len(wled_palettes)} palettes.")
                except Exception as e:
                    print(f"[WLED Scanner] Could not fetch palettes: {e}")

def scan_for_devices(timeout_seconds=4):
    print("Scanning local network for WLED devices...")
    zc = Zeroconf()
    browser = ServiceBrowser(zc, "_wled._tcp.local.", handlers=[_on_service_state_change])
    time.sleep(timeout_seconds)
    zc.close()
    print(f"[WLED Scanner] Scan complete. Devices ready: {list(discovered_wleds.keys())}")

def control_wled(device_name: str, power_state: bool, brightness: int, r: int, g: int, b: int, effect_name: str = "solid", palette_name: str = "default") -> str:
    """
    Controls a WLED light strip.
    
    Args:
        device_name: The name of the light (e.g., 'office-light').
        power_state: True to turn on, False to turn off.
        brightness: Integer from 1 to 255.
        r: Red color value (0-255).
        g: Green color value (0-255).
        b: Blue color value (0-255).
        effect_name: The animation effect to play (e.g., 'solid', 'aurora', 'rainbow'). Default is 'solid'.
        palette_name: The color palette to use (e.g., 'default', 'ocean', 'lava', 'party'). Default is 'default'.
    """
    print(f"\n--- [DEBUG WLED] Tool Triggered ---")
    print(f"[DEBUG] Target: '{device_name}', Effect: '{effect_name}', Palette: '{palette_name}'")
    
    target_ip = discovered_wleds.get(device_name.lower())
    
    if not target_ip:
        print("[DEBUG] STOPPING: Could not find IP.")
        return f"Error: Device {device_name} not found."

    # Fuzzy match Effect ID
    fx_id = 0
    requested_effect = effect_name.lower()
    for known_effect, known_id in wled_effects.items():
        if requested_effect in known_effect or known_effect in requested_effect:
            fx_id = known_id
            break

    # Fuzzy match Palette ID
    pal_id = 0
    requested_pal = palette_name.lower()
    for known_pal, known_p_id in wled_palettes.items():
        if requested_pal in known_pal or known_pal in requested_pal:
            pal_id = known_p_id
            break

    url = f"http://{target_ip}/json/state"
    payload = {
        "on": power_state,
        "bri": brightness,
        "seg": [{"col": [[r, g, b]], "fx": fx_id, "pal": pal_id}]
    }
    
    print(f"[DEBUG] Sending POST request to: {url}")
    print(f"[DEBUG] Payload: {payload}")
    
    try:
        response = requests.post(url, json=payload, timeout=3)
        if response.status_code == 200:
            return f"Successfully updated {device_name} to effect '{effect_name}' and palette '{palette_name}'."
        else:
            return f"Failed to update {device_name}. Status: {response.status_code}"
    except Exception as e:
        print(f"[DEBUG] CRASH/TIMEOUT: {e}")
        return f"Network error: {e}"
