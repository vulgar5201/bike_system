from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import text
from celery import Celery
from celery.schedules import crontab

# ljy
SECRET_KEY = 'xjuececuburvbvru'

# 数据库配置信息
HOSTNAME = '120.46.186.88'
PORT = '3306'
DATABASE = 'bike_system'
USERNAME = 'super'
PASSWORD = '1234'
DB_URI = f'mysql+pymysql://{USERNAME}:{PASSWORD}@{HOSTNAME}:{PORT}/{DATABASE}'
SQLALCHEMY_DATABASE_URI = DB_URI


def create_db_engine():
    """创建数据库引擎"""
    return create_engine(SQLALCHEMY_DATABASE_URI)


def test_database_connection(engine):
    """测试数据库连接"""
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            if result.fetchone():
                print("Database connection successful.")
                return True
    except SQLAlchemyError as e:
        print(f"Database connection failed: {e}")
        return False


def main():
    test_database_connection()


if __name__ == "__main__":
    main()

# 邮件服务器配置
MAIL_SERVER = 'smtp.qq.com'
MAIL_PORT = 587
MAIL_USE_SSL = False
MAIL_USE_TLS = True
MAIL_USERNAME = '3420678681@qq.com'
MAIL_PASSWORD = 'jegqmqeqtdphchee'
MAIL_DEFAULT_SENDER = '3420678681@qq.com'

# Celery配置
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_BEAT_SCHEDULE = {
    'delete-expired-captchas-every-2-minutes': {
        'task': 'tasks.delete_expired_captchas',
        'schedule': crontab(minute='*/2'),
    },
}
CELERY_TIMEZONE = 'UTC'


def execute_sql(engine, sql, params=None):
    """执行SQL语句"""
    try:
        with engine.connect() as connection:
            trans = connection.begin()  # 开始事务
            try:
                if params:
                    connection.execute(sql, params)
                else:
                    connection.execute(sql)
                trans.commit()  # 提交事务
            except Exception as e:
                trans.rollback()  # 回滚事务
                print(f"Error during SQL execution: {e}")
                raise
    except SQLAlchemyError as e:
        print(f"Failed to execute SQL: {e}")
