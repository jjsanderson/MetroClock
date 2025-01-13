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
OFFSET = 0

# Initalise the WS2812 / NeoPixel™ LEDs
led_strip = plasma.WS2812(
    NUM_LEDS, 0, 0, plasma_stick.DAT, color_order=plasma.COLOR_ORDER_RGB
)
led_strip.start()

# Set a red highlight colour at 50% brightness, HSV
HIGHLIGHT = (0, 1.0, 0.5)

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

        return sorted(train_times)

    except Exception as e:
        print(f"Error fetching departure data: {e}")
        return []


def get_train_times(station_code, platform_num):
    """TODO: REMOVE THIS FUNCTION AND USE get_train_times_in_secs_since_epoch() INSTEAD"""
    try:
        url = f"https://metro-rti.nexus.org.uk/api/times/{station_code}/{platform_num}"
        response = urequests.get(url)
        train_data = response.json()

        train_times = []
        for train in train_data:
            timestamp = train["actualPredictedTime"]

            # Split into date and time parts
            date_part, time_part = timestamp.split('T')

            # print(f"Date part: {date_part}")
            # print(f"Time part: {time_part}")

            # Split the date part into year, month, day
            year, month, day = map(int, date_part.split('-'))
            # print(f"Year: {year}, Month: {month}, Day: {day}")

            # Split the time part into hour, minute, second
            time_part = time_part.split('.')[0]
            hour, minute, second = map(int, time_part.split(':'))
            # print(f"Hour: {hour}, Minute: {minute}, Second: {second}")

            day_of_week = zeller_day(year, month, day)

            # Now assemble the date and time parts into a tuple,
            # matching the field order of rtc.datetime()
            train_time = (year, month, day, day_of_week, hour, minute, second, 0)

            train_time_secs = time.mktime((year, month, day, hour, minute, second, 0, 0))

            print(f">>> Train time in seconds: {train_time_secs}")

            # print(f"Train time:   {train_time}")

            # Append the train time to the list
            train_times.append(train_time)

        return sorted(train_times)

    except Exception as e:
        print(f"Error fetching departure data: {e}")
        return []


def zeller_day(year, month, day):
    """Zeller's Congruence: calculate day of the week.
    Returns 0=Monday through 6=Sunday
    """
    if month < 3:
        month += 12
        year -= 1

    k = year % 100
    j = year // 100

    day_of_week = (
        day
        + ((13 * (month + 1)) // 5)
        + k
        + (k // 4)
        + (j // 4)
        - (2 * j)
    ) % 7

    # Convert from Zeller's (0=Saturday) to ISO (0=Monday)
    return (day_of_week + 5) % 7

def time_to_8_tuple_time(time):
    """Convert a time tuple to an 8-tuple time tuple.

    Args:
        time: Tuple of (year, month, day, day_of_week, hour, minute, second, 0)

    Returns:
        time: Tuple of (year, month, mday, hour, minute, second, weekday, yearday)
    """

    year, month, day, day_of_week, hour, minute, second, fraction = time

    # Calculate days in each month, accounting for leap years
    days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

    # Adjust February for leap years
    if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0):
        days_in_month[1] = 29

    # Calculate yearday by summing completed months plus current month days
    yearday = sum(days_in_month[:month-1]) + day

    # Make sure everything is an int
    year = int(year)
    month = int(month)
    day = int(day)
    hour = int(hour)
    minute = int(minute)
    second = int(second)
    day_of_week = int(day_of_week)
    yearday = int(yearday)

    t_return = (year, month, day, hour, minute, second, 0, 0)
    print(f"Time tuple: {t_return}")
    # Convert to seconds since epoch
    t_secs = time.mktime(t_return)
    print(f"Time in seconds: {t_secs}")

    # Return 8-tuple in required format
    # return (year, month, day, hour, minute, second, day_of_week, yearday)
    # return (year, month, day, hour, minute, second, 0, 0)
    return t_return



def time_difference(time1, time2):
    """Calculate the difference in seconds between two times.

    Args:
        time1: Tuple of (year, month, day, day_of_week, hour, minute, second, 0)
        time2: Tuple of (year, month, day, day_of_week, hour, minute, second, 0)

    Returns:
        Time difference in seconds
    """

    print(f"Time1 orig: {time1}")
    time1 = time_to_8_tuple_time(time1)
    print(f"Time1 proc: {time1}")
    # print(f"Time2 orig: {time2}")
    # time2 = time_to_8_tuple_time(time2)
    # print(f"Time2 proc: {time2}")

    t1_year, t1_month, t1_day, t1_hour, t1_minute, t1_second, t1_weekday, t1_yearday = time1

    t1 = (t1_year, t1_month, t1_day, t1_hour, t1_minute, t1_second, 0, 0)
    # Convert the times to seconds since the epoch
    time1_seconds = time.mktime(time1)
    # time1_seconds = time.mktime(time1)
    print(f"Time1 seconds: {time1_seconds}")
    # time2_seconds = time.mktime(time2)

    # print(f"Time2 seconds: {time2_seconds}")

    # return time1_seconds - time2_seconds



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
    station_code = "WTL"
    # print(f"Station code for Whitley Bay: {station_code}")
    # platform_info = get_platform_info(station_code)
    # print(f"Platform information for Whitley Bay: {platform_info}")

    # print the current time
    # current_time = rtc.datetime()
    current_time = time.localtime()
    # (year, month, day, day_of_week, hour, minute, second, fraction) = current_time
    # current_time = (year, month, day, day_of_week, hour, minute, second, 0)
    print(f"Current time: {current_time}")
    current_time_in_seconds = time.mktime(current_time)
    print(f"Current time in seconds: {current_time_in_seconds}")

    train_times = get_train_times_in_secs_since_epoch(station_code, 1)
    print(f"Next train times: {train_times}")

    for time in train_times:
        print(f"Time difference: {time - current_time_in_seconds}")

