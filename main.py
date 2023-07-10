import asyncio
from dataclasses import dataclass

import python_weather
import requests
import time
import math
from geopy.geocoders import Nominatim
from python_weather.forecast import Weather

earth_radius_km = 6379
polling_interval = 5 


@dataclass
class Coordinates:
    latitude: float
    longitude: float


def get_iss_position() -> Coordinates:
    response = requests.get('http://api.open-notify.org/iss-now.json')
    data_position = response.json()['iss_position']
    return Coordinates(
        float(data_position['latitude']),
        float(data_position['longitude']),
    )


def get_city_name(coords: Coordinates) -> str | None:
    geolocator = Nominatim(user_agent="purplemapping")
    location = geolocator.reverse(f"{coords.latitude}, {coords.longitude}")
    if location is None:
        return None
    city = location.raw['address'].get('city')
    return city


async def get_weather(city: str) -> Weather:
    async with python_weather.Client(unit=python_weather.METRIC) as client:
        return await client.get(city)


def calculate_distance(coords1: Coordinates, coords2: Coordinates) -> float:
    lat1_rad = math.radians(coords1.latitude)
    lng1_rad = math.radians(coords1.longitude)
    lat2_rad = math.radians(coords2.latitude)
    lng2_rad = math.radians(coords2.longitude)
    
    # Haversine formula
    dlat = lat2_rad - lat1_rad
    dlng = lng2_rad - lng1_rad
    a = (
        math.sin(dlat / 2) ** 2 +
        math.cos(lat1_rad) *
        math.cos(lat2_rad) *
        math.sin(dlng / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    distance = earth_radius_km * c
    return distance


previous_pos: Coordinates | None = None


def poll_iss():
    global previous_pos

    current_pos = get_iss_position()
    print(f'Current position: {current_pos}')

    if previous_pos is not None:
        distance = calculate_distance(previous_pos, current_pos)
        speed = distance / polling_interval

        print(f'Distance traveled: {round(distance, 2)} kms')
        print(f'Est. Speed: {round(speed, 2)} km/s')
    
    previous_pos = current_pos

    city = get_city_name(current_pos)
    
    if city is not None:
        print(f"Over {city}")
        weather = asyncio.run(get_weather(city))
        print(f"Currently {weather}")


def main():
    while True:
        poll_iss()
        time.sleep(5)


main()
