import urequests
import json
import uasyncio
import plasma
from plasma import plasma_stick
import time
import WIFI_CONFIG
from network_manager import NetworkManager
import urequests
from machine import RTC
import ntptime


# We'll move parts to a separate file eventually.
# from metro_api import get_station_mapping, get_platform_info


# Number of LEDs around clock face
NUM_LEDS = 96
# Updates per second
UPDATES = 60
# Is the LED strip rotated?
OFFSET = 0

# Initalise the WS2812 / NeoPixel™ LEDs
led_strip = plasma.WS2812(
    NUM_LEDS, 0, 0, plasma_stick.DAT, color_order=plasma.COLOR_ORDER_RGB
)
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
        response = urequests.get("https://metro-rti.nexus.org.uk/api/stations")
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
        response = urequests.get(
            "https://metro-rti.nexus.org.uk/api/stations/platforms"
        )
        platforms_data = response.json()

        if station_code not in platforms_data:
            return []

        station_platforms = platforms_data[station_code]
        helper_texts = [platform["helperText"] for platform in station_platforms]

        return helper_texts

    except Exception as e:
        print(f"Error fetching platform data: {e}")
        return []


def get_platform_times(station_code, platform_num):
    try:
        url = f"https://metro-rti.nexus.org.uk/api/times/{station_code}/{platform_num}"
        response = urequests.get(url)
        times_data = response.json()

        departure_times = []
        for train in times_data:
            timestamp = train["actualPredictedTime"].split(".")[0]
            year, month, day = map(int, timestamp[0:10].split("-"))
            hour, minute, second = map(int, timestamp[11:19].split(":"))

            # Create tuple matching time.localtime() format:
            # (year, month, day, hour, min, sec, weekday, yearday)
            weekday = 0  # Can calculate if needed
            yearday = 0  # Can calculate if needed
            departure_time = (year, month, day, hour, minute, second, weekday, yearday)
            departure_times.append(departure_time)

        return sorted(departure_times)

    except Exception as e:
        print(f"Error fetching times for {station_code} platform {platform_num}: {e}")
        return []


def get_next_trains(departure_times):
    """Get departure times of trains due to leave within the next hour."""

    now = time.time()
    hour_from_now = now + 3600
    next_trains = []

    for departure in departure_times:
        # TODO: Revisit when we enter BST, I guess this might break?
        # Reorder tuple for mktime (year,month,day,hour,min,sec,weekday,yearday,isdst)
        departure_time = time.mktime(
            (
                departure[0],  # year
                departure[1],  # month
                departure[2],  # day
                departure[4],  # hour
                departure[5],  # minute
                departure[6],  # second
                departure[3],  # weekday
                0,  # yearday (not used)
                0,  # type: ignore # isdst flag
            )
        )

        if departure_time > now and departure_time < hour_from_now:
            next_trains.append(departure)

    return next_trains


def next_train_minutes(departure_times):
    """Return a list of the minutes only for the next trains."""

    next_trains = get_next_trains(departure_times)
    # Return just the minutes for the next trains
    return [train[4] for train in next_trains]


def minutes_to_position(next_trains_minutes):
    """Convert a list of minutes to LED positions.

    We have a string of NUM_LEDS which we can assume wraps around a clock face,
    ie. 60 minutes. We also want to factor in an OFFSET, which is the number of
    pixels we're out from the 12 o'clock position. We'll need to wrap minutes
    around the 12 o'clock.
    """

    return [(time_to_LED_number(minute) + OFFSET) % NUM_LEDS for minute in next_trains_minutes]


def display_minutes(next_trains_minutes):
    """Display the minutes on the LED strip.

    First convert to LED positions, then light up the LEDs.
    """

    positions = minutes_to_position(next_trains_minutes)
    blank_leds()

    for position in positions:
        # Unpack the HIGHLIGHT tuple into the set_hsv method
        led_strip.set_hsv(position, *HIGHLIGHT)

    led_strip.show()



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
    print(f"Station code: {whitley_bay}")
    print(f"Platforms: {get_platform_info(whitley_bay)}")

    print(f"Current time: {time.localtime()}")
    # print(
    #     f"Departures in next hour: {get_next_trains(get_platform_times(whitley_bay, 1))}"
    # )

    # Let's test our LED calculations.
    # Output the next train timestamps (one per line), then the next train minutes
    # (as a list), and finally the corresponding LED numbers (as a list)
    departure_times = get_platform_times(whitley_bay, 1)
    print(f"Next departures: {departure_times}")
    next_trains_minutes = next_train_minutes(departure_times)
    print(f"Next train minutes: {next_trains_minutes}")
    # print({minutes_to_position(next_trains_minutes)})
    # display_minutes(next_trains_minutes)


# if __name__ == "__main__":
#     stations = get_station_mapping()
#     if stations:
#         whitley_bay = stations.get("Whitley Bay")

#         while True:
#             departure_times = get_platform_times(whitley_bay, 1)
#             next_trains_minutes = next_train_minutes(departure_times)
#             display_minutes(next_trains_minutes)
#             time.sleep(60)
