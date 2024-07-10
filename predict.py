from datetime import datetime
import joblib
import onnxruntime as ort
import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from get_weather import fetch_weather_data, parse_weather_data
from config import create_db_engine, test_database_connection, execute_sql

# 加载缩放器参数
scaler = joblib.load('scaler.joblib')

# 加载ONNX模型
onnx_model = 'test.onnx'
ort_session = ort.InferenceSession(onnx_model)

# 创建数据库引擎
engine = create_db_engine()


def predict_demand_from_db(is_holiday=0):
    """从API获取天气数据和站点数据进行需求预测"""
    engine = create_db_engine()
    if test_database_connection(engine):
        try:
            # 获取天气数据
            api_data = fetch_weather_data()
            weather_data = parse_weather_data(api_data)

            if weather_data:
                with engine.connect() as connection:
                    # 获取所有 station_id
                    station_query = text("SELECT station_id FROM station")
                    station_data = connection.execute(station_query).fetchall()

                    if station_data:
                        # 从 weather_data 获取 T, U, Ff
                        T = weather_data['T']
                        U = weather_data['U']
                        Ff = weather_data['Ff']

                        # 获取日期相关信息
                        date = datetime.strptime(weather_data['data'], '%Y-%m-%d %H:%M:%S')
                        hour = date.hour
                        day_of_week = date.isoweekday()  # 1-7 表示周一到周日

                        # 构建 station_id 列表
                        station_ids = [row[0] for row in station_data]  # 假设 'station_id' 是第一列

                        # 构建新的数据 DataFrame
                        new_data = pd.DataFrame({
                            'hour': [hour] * len(station_ids),
                            'day_of_week': [day_of_week] * len(station_ids),
                            'is_holiday': [is_holiday] * len(station_ids),
                            'station_id': station_ids,
                            'T': [T] * len(station_ids),
                            'U': [U] * len(station_ids),
                            'Ff': [Ff] * len(station_ids)
                        })

                        # 将 station_id 转换为数值
                        new_data['station_id'] = new_data['station_id'].astype('category').cat.codes

                        # 使用与训练时相同的缩放器进行特征缩放
                        new_data_scaled = scaler.transform(new_data)

                        # 将数据调整为模型输入的形状
                        new_data_scaled = new_data_scaled.reshape(
                            (new_data_scaled.shape[0], 1, new_data_scaled.shape[1]))

                        # 运行推理
                        ort_inputs = {ort_session.get_inputs()[0].name: new_data_scaled.astype(np.float32)}
                        ort_outs = ort_session.run(None, ort_inputs)

                        predicted = ort_outs[0]

                        # 根据需要的比例调整预测结果
                        predicted_demand = predicted * 4

                        # 将预测结果保存到字典中，key为station_id，value为预测结果
                        demand_dict = {station_ids[i]: int(predicted_demand[i][0]) for i in range(len(station_ids))}

                        # 更新 station_info 表中的 bike_demand
                        for station_id, demand in demand_dict.items():
                            update_query = text(
                                "UPDATE station SET bike_demand = :bike_demand WHERE station_id = :station_id")
                            params = {"bike_demand": demand, "station_id": station_id}
                            execute_sql(engine, update_query, params)
                    else:
                        print("No station_info data available.")
            else:
                print("No weather data available.")
        except SQLAlchemyError as e:
            print(f"An error occurred: {e}")
    else:
        print("Failed to connect to the database.")


def predict_demand(hour, day_of_week, is_holiday, station_id, T, U, Ff):
    # 构建新的数据 DataFrame
    new_data = pd.DataFrame({
        'hour': [hour],
        'day_of_week': [day_of_week],
        'is_holiday': [is_holiday],
        'station_id': [station_id],
        'T': [T],
        'U': [U],
        'Ff': [Ff]
    })

    # 将 station_id 转换为数值
    new_data['station_id'] = new_data['station_id'].astype('category').cat.codes

    # 使用与训练时相同的缩放器进行特征缩放
    new_data_scaled = scaler.transform(new_data)

    # 将数据调整为模型输入的形状
    new_data_scaled = new_data_scaled.reshape((new_data_scaled.shape[0], 1, new_data_scaled.shape[1]))

    # 运行推理
    ort_inputs = {ort_session.get_inputs()[0].name: new_data_scaled.astype(np.float32)}
    ort_outs = ort_session.run(None, ort_inputs)

    predicted = ort_outs[0]

    predicted_demand = predicted * 4

    return int(predicted_demand[0][0])


# 使用方法示例
predict_demand_from_db(is_holiday=0)
result = predict_demand(hour=8, day_of_week=3, is_holiday=0, station_id='TA1307000126', T=25.0, U=50.0, Ff=5.0)
print(f'Predicted demand for specific input: {result}')
