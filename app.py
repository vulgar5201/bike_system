from flask import Flask
import config
from extends import db, mail
from models import User
from blueprints.admin import bp as am_bp
from blueprints.dispatcher import bp as dp_bp
from blueprints.auth import bp as auth_bp
from flask_migrate import Migrate
from flask_cors import CORS


app = Flask(__name__)
# 绑定配置文件
app.config.from_object(config)


mail.init_app(app)  # 初始化mail
db.init_app(app)
migrate = Migrate(app, db)

app.register_blueprint(am_bp)
app.register_blueprint(dp_bp)
app.register_blueprint(auth_bp)


if __name__ == '__main__':
    app.run()



