import math, requests
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import text
from config import create_db_engine, test_database_connection


# 从数据库获取站点数据
def fetch_station_data(engine):
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT station_id, station_lat, station_lng, bike_demand FROM station"))
            stations = {'station_id': [], 'latitude': [], 'longitude': [], 'extra_bikes': []}
            for row in result.mappings():
                stations['station_id'].append(row['station_id'])
                # 将经纬度数据转换为浮点数
                stations['latitude'].append(float(row['station_lat']))
                stations['longitude'].append(float(row['station_lng']))
                stations['extra_bikes'].append(row['bike_demand'])
            return stations
    except SQLAlchemyError as e:
        print(f"Error fetching station data: {e}")
        return None


# 计算两个站点之间的距离
def calculate_distance(lat1, lon1, lat2, lon2):
    return math.sqrt((lat2 - lat1) ** 2 + (lon2 - lon1) ** 2)


# 将调度员分配到站点并运输车辆
def assign_dispatchers_and_transport(stations, dispatcher_count):
    # 将数据组合成易于处理的字典列表
    station_data = [
        {'station_id': stations['station_id'][i],
         'latitude': stations['latitude'][i],
         'longitude': stations['longitude'][i],
         'extra_bikes': stations['extra_bikes'][i]}
        for i in range(len(stations['station_id']))
    ]

    # 按车辆数（从多到少）排序站点
    station_data.sort(key=lambda x: x['extra_bikes'], reverse=True)

    # 将站点分为有车站点和缺车站点
    surplus_stations = [station for station in station_data if station['extra_bikes'] > 0]
    deficit_stations = [station for station in station_data if station['extra_bikes'] < 0]

    # 分配调度员到站点并运输车辆
    assignments = {}
    for i in range(min(dispatcher_count, len(surplus_stations))):
        surplus_station = surplus_stations[i]
        initial_extra_bikes = surplus_station['extra_bikes']
        assignments[f'调度员 {i + 1}'] = {'from': surplus_station, 'initial_extra_bikes': initial_extra_bikes,
                                          'to': []}

        current_location = surplus_station

        # 尽量减少调度员的总运行距离
        while surplus_station['extra_bikes'] > 0 and deficit_stations:
            # 找到最近的缺车站点，优先处理缺车严重的站点
            deficit_station = min(deficit_stations, key=lambda x: (
                calculate_distance(current_location['latitude'], current_location['longitude'], x['latitude'],
                                   x['longitude']),
                x['extra_bikes']))

            # 计算运输的车辆数量
            transfer_bikes = min(surplus_station['extra_bikes'], -deficit_station['extra_bikes'])
            surplus_station['extra_bikes'] -= transfer_bikes
            deficit_station['extra_bikes'] += transfer_bikes

            assignments[f'调度员 {i + 1}']['to'].append(
                {'station_id': deficit_station['station_id'], 'bikes': transfer_bikes,
                 'from_lat': current_location['latitude'], 'from_lon': current_location['longitude'],
                 'to_lat': deficit_station['latitude'], 'to_lon': deficit_station['longitude']})

            current_location = deficit_station

            if deficit_station['extra_bikes'] == 0:
                deficit_stations.remove(deficit_station)

    return assignments, station_data

# 主函数
def main(dispatcher_count):
    # 创建数据库引擎并测试连接
    engine = create_db_engine()
    if not test_database_connection(engine):
        return None

    # 从数据库获取站点数据
    stations = fetch_station_data(engine)
    if not stations:
        return None

    # 获取分配和运输结果
    assignments, station_data = assign_dispatchers_and_transport(stations, dispatcher_count)

    all_routes = []
    for dispatcher, info in assignments.items():
        from_station = info['from']
        routes = []
        for to_station in info['to']:
            route = {
                "from_lat": from_station['latitude'],
                "from_lon": from_station['longitude'],
                "to_lat": to_station['to_lat'],
                "to_lon": to_station['to_lon'],
                "bikes": to_station['bikes']
            }
            routes.append(route)
            from_station = {
                'latitude': to_station['to_lat'],
                'longitude': to_station['to_lon']
            }
        all_routes.append({dispatcher: routes})

    print(all_routes)

    # 返回所有调度员的完整路线列表
    return all_routes

if __name__ == '__main__':
    main(5)
