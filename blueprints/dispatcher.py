from flask import Blueprint, jsonify, request
import requests
bp = Blueprint('dispatcher', __name__, url_prefix='/dispatcher')
BASE_URL = 'http://localhost:5000'


@bp.route('/dispatch_data', methods=['GET'])
def draw():
    try:
        # 从请求中获取 JSON 数据
        data = request.get_json()
        if not data or 'dispatcher_id' not in data:
            return jsonify({"error": "Invalid input data"}), 400

        dispatcher_id = data['dispatcher_id']
        dispatcher_id_str = str(dispatcher_id)
        # 发送请求获取数据提供者的数据
        BASE_URL = 'http://127.0.0.1:5000'  # 替换为实际的数据提供者 URL
        response = requests.get(f'{BASE_URL}/admin/dispatch')
        response.raise_for_status()  # 检查请求是否成功

        # 解析响应为 JSON
        routs = response.json()
        print(routs)

        # 从响应数据中过滤出符合 dispatcher_id 的数据
        dispatch_data = None
        for route in routs:
            if dispatcher_id_str in route:
                dispatch_data = route[dispatcher_id_str]
                break

        if dispatch_data is None:
            return jsonify({"error": f"Dispatcher {dispatcher_id} not found"}), 404

        return jsonify(dispatch_data)

    except requests.exceptions.RequestException as e:
        # 捕获所有请求相关的异常
        return jsonify({"error": f"Error fetching data from data provider: {str(e)}"}), 500

    except ValueError as e:
        # 捕获 JSON 解析错误
        return jsonify({"error": "Error parsing JSON response"}), 500

    except Exception as e:
        # 捕获其他所有异常
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500


