from flask import Blueprint, jsonify, request
import requests
bp = Blueprint('dispatcher', __name__, url_prefix='/dispatcher')
BASE_URL = 'http://localhost:5000'


@bp.route('/dispatch_data', methods=['GET'])
def draw():
    try:
        # 从请求中获取 JSON 数据
        data_1 = request.get_json()
        if not data_1 or 'dispatcher_id' not in data_1:
            return jsonify({"error": "Invalid input data"}), 400

        dispatcher_id = data_1['dispatcher_id']

        # 发送请求获取数据提供者的数据
        response = requests.get(f'{BASE_URL}/data_provider')
        response.raise_for_status()  # 检查请求是否成功

        # 解析响应为 JSON
        data_2 = response.json()

        # 从响应数据中过滤出符合 dispatcher_id 的数据
        dispatch_data = [item for item in data_2 if item.get('dispatcher_id') == dispatcher_id]

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

