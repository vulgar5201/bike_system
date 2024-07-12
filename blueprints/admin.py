from datetime import datetime
from flask import Blueprint, jsonify, request, session
from models import Station, User
from run import main
from extends import db
from predict import predict_demand, predict_demand_from_db

bp = Blueprint('admin', __name__, url_prefix='/admin')


# dispatchers_list = []
# result = []
# [
#     {
#         'from_lat': float(station.station_lat),
#         'from_lng': float(station.station_lng),
#         'to_lat': float(station.station_lat),
#         'to_lng': float(station.station_lng),
#         dispatch_num:""
#         'from_lat': float(station.station_lat),
#         'from_lng': float(station.station_lng),
#         'to_lat': float(station.station_lat),
#         'to_lng': float(station.station_lng),
#         dispatch_num: ""
#     }
#
# ]


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
        # db.session.add(station)
        db.session.commit()
        return jsonify({"code": 200, "message": "Station updated successfully!"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'msg': str(e)}), 500


@bp.route('/predict', methods=['POST'])
def predict():
    from predict import predict_demand
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


@bp.route('/predict_implement', methods=['GET'])
def predict_implement():
    is_holiday = request.args.get('is_holiday', default=0, type=int)
    result, status_code = predict_demand_from_db(is_holiday)
    return jsonify(result), status_code


@bp.route('/dispatch', methods=['GET'])
def dispatch():
    try:
        num = User.query.filter_by(role='dispatcher').count()

        if num is None:
            return jsonify({"error": "Missing 'num' parameter"}), 400

        try:
            num = int(num)
        except ValueError:
            return jsonify({"error": "'num' parameter must be an integer"}), 400

        # 调用调度算法获取 n 个数据, 存到 json_data_list 中
        routes = main(num)

        if not isinstance(routes, list):
            return jsonify({"error": "'main' function must return a list"}), 500

        # 查询数据库获取 role 为 'dispatcher' 的前 num 个用户
        dispatchers = User.query.filter_by(role='dispatcher').limit(num).all()

        # 提取用户 ID 并放入列表
        dispatchers_list = [dispatcher.id for dispatcher in dispatchers]

        result = []  # 初始化result列表

        for i, dispatcher_id in enumerate(dispatchers_list):
            route = routes[i]
            for key in route:
                result.append({f"{dispatcher_id}": route[key]})

        return jsonify(result)

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

# @bp.route('/data_provider', methods=['GET'])
# def data_provider():
#     try:
#         # 返回 JSON 数据列表
#         return jsonify(result)
#     except Exception as e:
#         # 捕获所有异常并返回错误信息
#         return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500


# @bp.route('/dispatcher_id_provider', methods=['GET'])
# def dispatcher_id_provider():
#     try:
#         return jsonify(dispatchers_list)
#     except Exception as e:
#         # 捕获所有异常并返回错误信息
#         return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500
