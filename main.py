import urequests
import json
import uasyncio
import plasma
from plasma import plasma_stick
import time
import WIFI_CONFIG
from network_manager import NetworkManager
import urequests# Dictionary for station names

# We'll move this to a separate file eventually.
# from metro_api import get_station_mapping, get_platform_info


# Number of LEDs around clock face
NUM_LEDS = 96
# Updates per second
UPDATES = 60

# Initalise the WS2812 / NeoPixel™ LEDs
led_strip = plasma.WS2812(NUM_LEDS, 0, 0, plasma_stick.DAT, color_order=plasma.COLOR_ORDER_RGB)
led_strip.start()

# Set a red highlight colour at 50% brightness, HSV
HIGHLIGHT = (0, 1.0, 0.5)

def status_handler(mode, status, ip):
    print(mode, status, ip)


def time_to_LED_number(minutes):
    """Convert time in minutes to the corresponding position in the LED array.

    Note that we're running at NUM_LEDS for 60 minutes, so need to scale accordingly.
    """

    return int((minutes / 60) * NUM_LEDS)


def blank_leds():
    """Set all LEDs to off."""
    for i in range(NUM_LEDS):
        led_strip.set_hsv(i, 0, 0, 0)





def get_station_mapping():
    """Retrieve and parse station mappings from API query.

    TODO: move to separate module.
    """

    try:
        response = urequests.get('https://metro-rti.nexus.org.uk/api/stations')
        stations_data = response.json()

        name_to_code = {}
        for code, name in stations_data.items():
            name_to_code[name] = code

        return name_to_code
    except Exception as e:
        print(f"Error fetching station data: {e}")
        return {}


def get_platform_info(station_code):
    """Get platform information for a station.

    Args:
        station_code: Three letter station code (e.g. 'MTS')

    Returns:
        List of helper text strings for each platform

    TODO: Move to separate module.
    """
    try:
        response = urequests.get('https://metro-rti.nexus.org.uk/api/stations/platforms')
        platforms_data = response.json()

        if station_code not in platforms_data:
            return []

        station_platforms = platforms_data[station_code]
        helper_texts = [platform['helperText'] for platform in station_platforms]

        return helper_texts

    except Exception as e:
        print(f"Error fetching platform data: {e}")
        return []


def get_platform_times(station_code, platform_num):
    """Get real-time train departures for specified platform.

    Args:
        station_code (str): Three letter station code (e.g. 'WTL')
        platform_num (int): Platform number (1 or 2)

    Returns:
        list: Departure times and destinations
    """
    try:
        url = f'https://metro-rti.nexus.org.uk/api/times/{station_code}/{platform_num}'
        response = urequests.get(url)
        times_data = response.json()

        departures = []
        for train in times_data:
            departure = {
                'destination': train['destination'],
                'time': train['due'],
                'expected': train['expected']
            }
            departures.append(departure)

        return departures

    except Exception as e:
        print(f"Error fetching times for {station_code} platform {platform_num}: {e}")
        return []


# Connect to WiFi
netman = NetworkManager("GB", status_handler=status_handler)

uasyncio.get_event_loop().run_until_complete(
    netman.client(WIFI_CONFIG.SSID, WIFI_CONFIG.PSK)
)

# Example usage
stations = get_station_mapping()
if stations:
    print("Station mappings loaded successfully")
    # Example lookup
    whitley_bay = stations.get("Whitley Bay")
    print(whitley_bay)
    print(get_platform_info(whitley_bay))

    print(get_platform_times(whitley_bay, 1))
