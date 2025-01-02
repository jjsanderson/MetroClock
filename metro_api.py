import urequests# Dictionary for station names

def get_station_mapping():
    """Retrieve and parse station mappings from API query."""

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
