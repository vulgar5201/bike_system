from datetime import datetime
from flask import Blueprint, jsonify, request
from extends import db
from models import Station, User
from predict import predict_demand
from run import main

bp = Blueprint('admin', __name__, url_prefix='/admin')
json_data_list = []


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
    try:
        # 获取并验证请求中的 JSON 数据
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid input data"}), 400

        hour = data.get('time')
        date_str = data.get('date')
        is_holiday = data.get('is_holiday')
        station_id = data.get('station_id')
        T = data.get('temperature')
        U = data.get('humidity')
        Ff = data.get('windSpeed')

        # 验证必需字段是否存在
        if any(v is None for v in [hour, date_str, is_holiday, station_id, T, U, Ff]):
            return jsonify({"error": "Missing required fields"}), 400

        # 解析日期并获取星期几
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            day_of_week = date_obj.weekday()
        except ValueError:
            return jsonify({"error": "Invalid date format. Expected YYYY-MM-DD."}), 400

        # 从数据库中查询站点信息
        station = Station.query.get(station_id)
        if not station:
            return jsonify({"error": "Station not found"}), 404

        # 调用预测函数
        bike_demand = predict_demand(hour, day_of_week, is_holiday, station_id, T, U, Ff)

        # 更新站点信息
        station.bike_demand = bike_demand
        db.session.add(station)
        db.session.commit()

        return jsonify({"message": "Prediction successful", "bike_demand": bike_demand})

    except Exception as e:
        # 捕获所有其他异常并返回错误信息
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500


# 分配调度路线
@bp.route('/dispatch', methods=['POST'])
def dispatch():
    try:
        # 获取请求中的 JSON 数据
        data = request.get_json()
        num = data.get('num')

        if num is None:
            return jsonify({"error": "Missing 'num' parameter"}), 400

        try:
            num = int(num)
        except ValueError:
            return jsonify({"error": "'num' parameter must be an integer"}), 400

        if num <= 0:
            return jsonify({"error": "'num' parameter must be a positive integer"}), 400

        # 调用调度算法获取 n 个数据, 存到 json_data_list 中
        json_data_list = main(num)

        if not isinstance(json_data_list, list):
            return jsonify({"error": "'main' function must return a list"}), 500

        # 查询数据库获取 role 为 'dispatcher' 的前 num 个用户
        dispatchers = User.query.filter_by(role='dispatcher').limit(num).all()

        # 提取用户 ID 并放入列表
        dispatcher_ids = [dispatcher.id for dispatcher in dispatchers]

        # 提取 json_data_list 中所有 station_id
        station_ids = [member.get('station_id') for member in json_data_list if 'station_id' in member]

        # 查询数据库获取所有 station_id 对应的经纬度
        stations = Station.query.filter(Station.station_id.in_(station_ids)).all()
        station_dict = {station.station_id: (station.station_lat, station.station_lng) for station in stations}

        # 将 dispatcher_ids 和经纬度信息插入到 json_data_list 中每个成员的相应字段
        for member in json_data_list:
            member['dispatcher_id'] = dispatcher_ids
            station_id = member.get('station_id')
            if station_id and station_id in station_dict:
                member['station_lat'], member['station_lng'] = station_dict[station_id]
            else:
                member['station_lat'], member['station_lng'] = None, None  # 或者处理未找到的情况

        return jsonify(json_data_list)

    except Exception as e:
        # 捕获所有异常并返回错误信息
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500


# 获得调度的数据
@bp.route('/data_provider', methods=['GET'])
def data_provider():
    try:
        # 返回 JSON 数据列表
        return jsonify(json_data_list)
    except Exception as e:
        # 捕获所有异常并返回错误信息
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500


# 修改身份接口
@bp.route('/modify', methods=['POST'])
def modify():
    data = request.get_json()
    id = data.get('id')
    user = User.query.get(id)
    if not user:
        return jsonify({'status': 'error', 'msg': 'user not found'}), 404

    new_role = data.get('role')
    if new_role not in ['admin', 'dispatcher']:
        return jsonify({'status': 'error', 'msg': 'Invalid role'}), 400

    user.username = data.get('username')
    user.role = new_role
    try:
        db.session.commit()
        return jsonify({"code": 200, "message": "User modified successfully!"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'msg': str(e)}), 500


# 删除用户接口
@bp.route('/delete', methods=['POST'])
def delete():
    data = request.get_json()
    id = data.get('id')
    user = User.query.get(id)
    if not user:
        return jsonify({'status': 'error', 'msg': 'user not found'}), 404

    try:
        db.session.delete(user)
        db.session.commit()
        return jsonify({"code": 200, "message": "User deleted successfully!"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'msg': str(e)}), 500
