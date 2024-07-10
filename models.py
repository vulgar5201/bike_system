from extends import db
from datetime import datetime


class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    role = db.Column(db.String(120), unique=False, nullable=False)
    join_time = db.Column(db.DateTime, default=datetime.now)

    def __repr__(self):
        return f"Dispatcher(username='{self.username}', email='{self.email}', phone='{self.phone}, role='{self.role}')"


class EmailCaptchaModel(db.Model):
    __tablename__ = "email_apt"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(100), nullable=False)
    captcha = db.Column(db.String(100), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __init__(self, email, captcha):
        self.email = email
        self.captcha = captcha
        self.timestamp = datetime.utcnow()


# 新增
class Station(db.Model):
    __tablename__ = 'station'
    station_id = db.Column(db.String(50), primary_key=True)
    station_name = db.Column(db.String(255), nullable=False)
    station_lat = db.Column(db.Numeric(10, 6), nullable=False)
    station_lng = db.Column(db.Numeric(10, 6), nullable=False)
    bike_number = db.Column(db.Integer, default=0)
    bike_demand = db.Column(db.Integer, default=0)
