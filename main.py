import asyncio
from dataclasses import dataclass

import python_weather
import requests
import time
import math
from geopy.geocoders import Nominatim
from python_weather.forecast import Weather

earth_radius_km = 6371        
polling_interval = 5 


@dataclass
class Coordinates:
    latitude: float
    longitude: float


@dataclass
class IssPosition:
    time: int
    coords: Coordinates


async def get_weather(city: str) -> Weather:
    async with python_weather.Client(unit=python_weather.METRIC) as client:
        return await client.get(city)


def get_iss_position() -> IssPosition:
    response = requests.get('http://api.open-notify.org/iss-now.json')
    data = response.json()
    data_position = data['iss_position']
    
    return IssPosition(
        int(data['timestamp']),
        Coordinates(
            float(data_position['latitude']),
            float(data_position['longitude']),
        ),
    )


def get_city_name(coords: Coordinates) -> str | None:
    geolocator = Nominatim(user_agent="purplemapping")
    location = geolocator.reverse(f"{coords.latitude}, {coords.longitude}")
    if location is None:
        return None
    city = location.raw['address'].get('city')
    return city


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


previous_poll_time: int | None = None
previous_pos: IssPosition | None = None

est_dtime_error = 0
learning_rate = 0.1


def poll_iss():
    global previous_pos
    global previous_poll_time
    global est_dtime_error
    
    current_pos = get_iss_position()
    current_poll_time = time.time()
    
    print(f'Position: {current_pos.coords}')
    city = get_city_name(current_pos.coords)
    
    if city is not None:
        print(f"Flying over {city}")
        weather = asyncio.run(get_weather(city))
        print(f"Currently {weather}")
    
    if previous_pos is not None:
        distance = calculate_distance(previous_pos.coords, current_pos.coords)
        # Delta time from the API's response timestamp, which precision is seconds
        dtime_api = current_pos.time - previous_pos.time
        # Delta time from the polling interval, which precision is milliseconds
        dtime_poll = current_poll_time - previous_poll_time
        
        dtime_error = dtime_poll - polling_interval
        
        print(f'error: {dtime_error}')
        
        est_dtime_error += learning_rate * dtime_error
        
        print(f'est_dtime_error: {est_dtime_error}')
        
        adj_dtime_poll = polling_interval + est_dtime_error
        
        print(f'Distance traveled: {round(distance, 2)} Kilometers '
              f'in {round(dtime_api, 1)} seconds (a), '
              f'{round(dtime_poll, 2)} seconds (p)')
        print(f'Δ Time (a): {dtime_api}')
        print(f'Δ Time (p): {dtime_poll}')
        print(f'Δ Time (adjusted): {adj_dtime_poll}')
        print(f'Speed (a): {round(distance / dtime_api, 2)} km/s')
        print(f'Speed (p): {round(distance / dtime_poll, 2)} km/s')
        print(f'Speed (adjusted): {round(distance / adj_dtime_poll, 2)} km/s')

    previous_pos = current_pos
    previous_poll_time = current_poll_time


def main():
    while True:
        poll_iss()
        time.sleep(5)


main()
