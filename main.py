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


# Number of LEDs around clock face
NUM_LEDS = 96
# Updates per second
UPDATES = 60
# Is the LED strip rotated?
OFFSET = 1

# Initalise the WS2812 / NeoPixel™ LEDs
led_strip = plasma.WS2812(
    NUM_LEDS, 0, 0, plasma_stick.DAT, color_order=plasma.COLOR_ORDER_GRB
)
led_strip.start()

# Set a red highlight colour at 50% brightness, HSV
HIGHLIGHT_RED = (0, 1.0, 0.5)
HIGHLIGHT_BLUE = (0.66, 1.0, 0.5)

def status_handler(mode, status, ip):
    """Report network status while connecting to wifi."""
    print(mode, status, ip)

def get_station_mappings():
    """Retrieve and parse station mappings from API query.

    returns a dictionary of station names to station codes.
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
        station_code: Three letter station code (e.g. 'MTS'),
        retrieved from the station mapping function.

    Returns:
        List of helper text strings for each platform
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

def get_train_times_in_secs_since_epoch(station_code, platform_num):
    """Query the API for the next train times for a given station and platform.

    Args:
        station_code: Three letter station code (e.g. 'MTS').
        platform_num: The platform number to query.

    Returns:
        List of train times in seconds since the epoch.
        Boolean status flag

    Returning seconds because we have problems passing tuples between functions,
    then into time.mktime(); lots of "'tuple'object has no attribute 'mktime'" errors.
    """

    try:
        url = f"https://metro-rti.nexus.org.uk/api/times/{station_code}/{platform_num}"
        response = urequests.get(url)
        train_data = response.json()

        train_times = []
        for train in train_data:
            timestamp = train["actualPredictedTime"]

            # Split into date and time parts
            date_part, time_part = timestamp.split('T')

            # Split the date part into year, month, day
            year, month, day = map(int, date_part.split('-'))

            # Split the time part into hour, minute, second
            time_part = time_part.split('.')[0]
            hour, minute, second = map(int, time_part.split(':'))

            # Not needed, as mktime() ignores the value anyway.
            # day_of_week = zeller_day(year, month, day)

            # Now assemble the date and time parts into a tuple,
            # matching the field order of rtc.datetime(),
            # and pass that to time.mktime() to return seconds since epoch.
            train_time_secs = time.mktime((year, month, day, hour, minute, second, 0, 0))

            # print(f">>> Train time in seconds: {train_time_secs}")

            # Append the train time to the list
            train_times.append(train_time_secs)

        return sorted(train_times), True

    except Exception as e:
        print(f"Error fetching departure data: {e}")
        return [], False


def get_next_train_waits(current_time_in_seconds, station, platform):
    """Return a list of the next train times in seconds from now.

    Args:
        current_time_in_seconds: The current time.
        station: The station code.
        platform: The platform number.

    Returns:
        A list of the next train times in seconds from now.
        Update status boolean
    """

    # Get the train times
    train_times, status = get_train_times_in_secs_since_epoch(station, platform)

    # Calculate the difference between the current time and the train times
    train_times_diff = [time - current_time_in_seconds for time in train_times]

    return train_times_diff, status


def minute_to_position(minute, num_leds = NUM_LEDS, offset = OFFSET):
    """Convert a minute on the clock to a position on the LED string.

    Args:
        minute: The minute to convert.
        num_leds: The number of LEDs on the clock face.
        offset: The offset of the LEDs.

    Returns:
        The position on the LED string.
    """

    angle_degree = minute / 60
    position = int(angle_degree * num_leds) % num_leds
    # Apply offset
    position = (position + offset) % num_leds

    return position


def update_display(current_time_in_seconds, current_time_minutes, station_code, platform_num, led_strip = led_strip):
    """Main function: retrieve train times and update the LED display.

    Args:
        current_time_in_seconds: The current time in seconds.
        current_time_minutes: The current minute.
        station_code: The station code.
        platform_num: The platform number.
        led_strip: The LED strip object.

    Returns:
        None
    """

    print(f"Current time in seconds: {current_time_in_seconds}")
    print(f"Current time in minutes: {current_time_minutes}")

    # Get the next train times
    train_waits_in_seconds, status = get_next_train_waits(current_time_in_seconds, station_code, 1)
    print("Got next train waits")

    # If status is True, update the display
    if status:
        # calculate the wait times in minutes, and print
        list_of_minutes = []
        list_of_positions = []
        for wait_seconds in train_waits_in_seconds:
            wait_minutes = wait_seconds // 60
            arrival_time = (current_time_minutes + (wait_seconds // 60)) % 60
            # reject train if more than 57 minutes away
            # (57 because we have diffused LEDs, so it can look like we've just missed
            # a train when it's actually an hour away. Better to hide it for a few minutes
            # until the hand has move aside..)
            if wait_minutes > 57:
                print(f"Skip train in {wait_minutes} mins, arrives at {arrival_time} minutes past the hour")
                continue
            list_of_minutes.append(arrival_time)
            list_of_positions.append(minute_to_position(arrival_time))
            print(f"Train in {wait_minutes} minutes, arrives at {arrival_time} minutes past the hour, position {minute_to_position(arrival_time)}")

        # Update the LED strip.
        for i in range(NUM_LEDS):
            # Set pixel to black, unless position is in list_of_positions,
            # in which case set to HIGHLIGHT.
            if i not in list_of_positions:
                led_strip.set_rgb(i, 0, 0, 0)
            else:
                led_strip.set_hsv(i, *HIGHLIGHT_RED)

    else:
        print("No train data available.")
        # Change the LED strip to display the previous data, but in blue.
        for i in range(NUM_LEDS):
            # Test the pixel colour at this position
            if led_strip.get(i) == "(155, 0, 0, 0)":
                continue
            else:
                # Pixel wasn't black, so change it to blue
                led_strip.set_hsv(i, *HIGHLIGHT_BLUE)


if __name__ == "__main__":
    # Connect to wifi
    nm = NetworkManager("GB", status_handler=status_handler)

    uasyncio.get_event_loop().run_until_complete(
        nm.client(WIFI_CONFIG.SSID, WIFI_CONFIG.PSK)
    )

    # Get the current time
    rtc = RTC()
    ntptime.settime()
    time.sleep(1)

    # Get the station mappings
    # station_mappings = get_station_mappings()
    # Get the platform information for a station
    # station_code = station_mappings["Whitley Bay"]
    # print(f"Station code for Whitley Bay: {station_code}")
    # platform_info = get_platform_info(station_code)
    # print(f"Platform information for Whitley Bay: {platform_info}")

    # Hard-code the station code and platform number
    # We don't need to do an API lookup, we're not moving that quickly
    station_code = "WTL"
    platform_number = 1

    while True:
        # Update the display
        current_time = time.localtime()
        current_time_in_seconds = time.mktime(current_time)
        current_time_minutes = current_time[4]
        update_display(current_time_in_seconds, current_time_minutes, station_code, platform_number)

        # Sleep for two minutes
        time.sleep(120)
