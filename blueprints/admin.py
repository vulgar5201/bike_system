from datetime import datetime
from flask import Blueprint, jsonify, request
from extends import db
from models import Station
from predict import predict_demand

bp = Blueprint('admin', __name__, url_prefix='/admin')


# 查看站点接口
@bp.route('/check', methods=['GET'])
def check():
    # 查询所有站点信息
    stations = Station.query.all()

    # 将站点信息转换为字典列表
    stations_list = [{
        'station_id': station.station_id,
        'station_name': station.station_name,
        'station_lat': float(station.station_lat),
        'station_lng': float(station.station_lng),
        'bike_number': station.bike_number,
        'bike_demand': station.bike_demand
    } for station in stations]

    # 返回 JSON 响应
    return jsonify(stations_list)


# 更新站点接口
@bp.route('/update', methods=['POST'])
def change():
    data = request.get_json()
    id = data.get('station_id')
    station = Station.query.get(id)
    if not station:
        return jsonify({'status': 'error', 'msg': 'Station not found'}), 404

    station.station_name = data.get('station_name')
    station.station_lat = data.get('station_lat')
    station.station_lng = data.get('station_lng')
    station.bike_number = data.get('bike_number')
    station.bike_demand = data.get('bike_demand')
    try:
        db.session.commit()
        return jsonify({"code": 200, "message": "Station updated successfully!"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'msg': str(e)}), 500


@bp.route('/predict', methods=['POST'])
def predict():
    data = request.get_json()
    hour = data.get('time')
    date_str = data.get('date')
    day_of_week = -1
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        day_of_week = date_obj.weekday()
    except ValueError:
        # 如果日期字符串格式不正确，将捕获 ValueError 异常
        print("无效的日期格式")
    is_holiday = data.get('is_holiday')
    station_id = data.get('station_id')
    T = data.get('temperature')
    U = data.get('humidity')
    Ff = data.get('windSpeed')
    station = Station.query.get(data.get('station_id'))

    print(T, U, Ff)
    station.bike_demand = predict_demand(hour, day_of_week, is_holiday, station_id, T, U, Ff)
    db.session.add(station)
    db.session().commit()
