from datetime import datetime, timedelta
import requests

def fetch_weather_data():
    """从OpenWeatherMap API获取天气数据"""
    api_url = 'https://api.openweathermap.org/data/2.5/weather?id=4887398&appid=6555acfc7bc4a04c4a41dd56bef3930b&units=metric'
    response = requests.get(api_url)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to fetch data: {response.status_code}")
        return None


def parse_weather_data(api_data):
    """解析API返回的天气数据"""
    if not api_data:
        return None
    current_time_utc = datetime.utcnow() - timedelta(seconds=18000)
    parsed_data = {
        'data': current_time_utc.strftime('%Y-%m-%d %H:%M:%S'),
        'T': api_data['main']['temp'],
        'U': api_data['main']['humidity'],
        'Ff': api_data['wind']['speed']
    }
    return parsed_data

