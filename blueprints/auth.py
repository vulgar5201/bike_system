import random
import string
from flask import Blueprint, jsonify, session
from flask_mail import Message
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from extends import mail, db
from models import EmailCaptchaModel, User
from flask import request
from flask_cors import CORS
from sqlalchemy.exc import SQLAlchemyError
bp = Blueprint('auth', __name__, url_prefix='/auth')
CORS(bp)


# 常量定义
MIN_PASSWORD_LENGTH = 6
captcha_store = {}


# 注册接口
@bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    email = data.get('email')
    confirm_password = data.get('confirm_password')
    role = data.get('role')
    captcha = data.get('captcha')

    # # 检查必填字段
    # if not all([username, password, email, confirm_password, role]):
    #     return jsonify({'message': '所有字段都是必填的'}), 400
    #
    # # 检查密码长度
    # if len(password) < MIN_PASSWORD_LENGTH:
    #     return jsonify({'message': '密码长度不能少于6位'}), 401
    #
    # # 检查密码是否一致
    # if password != confirm_password:
    #     return jsonify({'message': '密码不一致，请重新输入'}), 402

    # 检查用户名、手机号和邮箱是否已经存在
    if User.query.filter_by(username=username).first():
        return jsonify({'message': '用户名已经存在'}), 403
    if User.query.filter_by(email=email).first():
        return jsonify({'message': '邮箱已经存在'}), 403

    # 检查邮箱验证码正确性
    captcha_record = EmailCaptchaModel.query.filter_by(email=email, captcha=captcha).first()
    if not captcha_record:
        return jsonify({'message': '验证码错误'}), 403
    if captcha_record:
        if datetime.utcnow() - captcha_record.timestamp <= timedelta(minutes=2):
            db.session.delete(captcha_record)
            db.session.commit()
        else:
            db.session.delete(captcha_record)
            db.session.commit()
            return jsonify({'message': '验证码已失效'}), 403

    # 创建用户
    try:
        hashed_password = generate_password_hash(password)
        new_user = User(username=username, password=hashed_password, email=email, role=role)
        db.session.add(new_user)
        db.session.commit()
        return jsonify({'message': '注册成功'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': '注册过程中发生错误，请重试', 'error': str(e)}), 500


# 邮箱验证接口
@bp.route("/captcha/email", methods=['GET'])
def captcha():
    email = request.args.get("email")
    if not email:
        return jsonify({"code": 400, "message": "Email is required", "data": None}), 400

    source = string.digits * 4
    captcha = random.sample(source, 4)
    captcha = "".join(captcha)

    # 删除旧的验证码
    db.session.query(EmailCaptchaModel).filter_by(email=email).delete()

    message = Message(subject="鸿运齐天共享单车注册验证码",
                      recipients=[email],
                      body=f"您的验证码是：{captcha},有效时间2分钟，请勿泄露")
    mail.send(message)

    # 保存新的验证码
    captcha_store[email] = {'captcha': captcha, 'timestamp': datetime.utcnow()}
    email_captcha = EmailCaptchaModel(email=email, captcha=captcha)
    db.session.add(email_captcha)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"code": 500, "message": str(e), "data": None}), 500

    return jsonify({"code": 200, "message": "", "data": None})


# 邮箱和验证码登录接口
@bp.route('/login_with_email_code', methods=['POST'])
def login_with_email_code():
    data = request.get_json()
    email = data.get('email')
    captcha = data.get('captcha')

    # 检查邮箱验证码正确性
    captcha_record = EmailCaptchaModel.query.filter_by(email=email, captcha=captcha).first()
    if not captcha_record:
        return jsonify({'message': '验证码错误'}), 403

    # 查找用户
    user = User.query.filter_by(email=email).first()
    if user:
        return jsonify({
            'message': '登录成功',
            'user_id': user.id,
            'username': user.username,
            'role': user.role
        }), 200
    return jsonify({'message': '用户不存在'}), 404


# 用户名和密码登录
@bp.route('/login_with_password', methods=['POST'])
def login_with_phone():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    # 查找用户
    user = User.query.filter_by(username=username).first()

    if user is None:
        return jsonify({'message': '该用户未注册，请先注册账户'}), 404

    if user and check_password_hash(user.password, password):
        session['user_id'] = user.id
        return jsonify({
            'message': '登录成功',
            'user_id': user.id,
            'username': user.username,
            'role': user.role
        }), 200
    return jsonify({'message': '密码错误，请重试'}), 401


# 邮箱验证码修改密码
@bp.route('/reset_password', methods=['POST'])
def reset_password():
    try:
        data = request.get_json()
        password = data.get('password')
        email = data.get('email')
        captcha = data.get('verificationCode')

        if not email or not password or not captcha:
            return jsonify({'status': 'error', 'msg': '缺少必要的参数'}), 400

        user = User.query.filter_by(email=email).first()
        if not user:
            return jsonify({'status': 'error', 'msg': '用户未找到'}), 404

        # 检查邮箱验证码正确性
        captcha_record = EmailCaptchaModel.query.filter_by(email=email, captcha=captcha).first()
        if not captcha_record:
            return jsonify({'status': 'error', 'msg': '验证码错误'}), 408

        if datetime.utcnow() - captcha_record.timestamp > timedelta(minutes=2):
            db.session.delete(captcha_record)
            db.session.commit()
            return jsonify({'status': 'error', 'msg': '验证码已失效'}), 408

        # 验证成功，更新密码
        hashed_password = generate_password_hash(password)
        user.password = hashed_password
        db.session.delete(captcha_record)  # 删除验证码记录
        db.session.commit()

        return jsonify({'status': 'success', 'msg': '密码更新成功'}), 200

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'msg': '数据库错误', 'error': str(e)}), 500

    except Exception as e:
        return jsonify({'status': 'error', 'msg': '内部服务器错误', 'error': str(e)}), 500