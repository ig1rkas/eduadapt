# register_and_auth.py
import smtplib
from datetime import datetime
from random import randint
from sqlalchemy.orm import Session
from data.users import User
from data.verification_code import VerificationCode
from data import db_session
from flask import jsonify, request
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import EMAIL_FROM, EMAIL_PASSWORT, SMPT_PORT, SMPT_SERVER


class AuthService:

    @staticmethod
    def validate_request_method(expected_method: str = "POST"):
        if request.method != expected_method:
            return jsonify({"error": f"Use {expected_method} method", "success": False}), 405
        return None

    @staticmethod
    def validate_required_fields(data: dict, required_fields: list):
        if not all(field in data for field in required_fields):
            missing_fields = [field for field in required_fields if field not in data]
            return jsonify({
                "error": f"Не хватает данных: {', '.join(missing_fields)}",
                "success": False
            }), 400
        return None

    @staticmethod
    def get_user_response_data(user: User) -> dict:
        response_data = {
            "id": user.id,
            "username": user.username,
            "native_language": user.native_lang,
            "email": user.email,
            "russian_level": user.russian_level,
            "status": user.status,
            "registration_date": user.registration_date.isoformat() if user.registration_date else None,
        }

        if hasattr(user, 'verified_at') and user.verified_at:
            response_data["verified_at"] = user.verified_at.isoformat()

        return response_data

    @staticmethod
    def create_verification_code(db_sess: Session, user_id: int) -> str:
        key = str(randint(100000, 999999))

        # delete old verification code
        old_codes = db_sess.query(VerificationCode).filter(
            VerificationCode.user_id == user_id
        ).all()

        for old_code in old_codes:
            db_sess.delete(old_code)

        # create new verification code
        verification = VerificationCode(
            user_id=user_id,
            code=key,
            expiry_minutes=2
        )

        db_sess.add(verification)
        return key

    @staticmethod
    def cleanup_user_and_verification(user_id: int):
        """delete user and verification code (rollback) in case of failing to send email"""
        cleanup_session = db_session.create_session()
        try:
            user_to_delete = cleanup_session.query(User).filter(User.id == user_id).first()
            if user_to_delete:
                cleanup_session.delete(user_to_delete)

            code_to_delete = cleanup_session.query(VerificationCode).filter(
                VerificationCode.user_id == user_id
            ).first()
            if code_to_delete:
                cleanup_session.delete(code_to_delete)

            cleanup_session.commit()
        finally:
            cleanup_session.close()


class RegistrationService(AuthService):

    @staticmethod
    def handle_registration():
        error_response = AuthService.validate_request_method("POST")
        if error_response:
            return error_response

        data = request.get_json()
        required_fields = ["username", "password", "email", "native_language", "russian_level"]
        error_response = AuthService.validate_required_fields(data, required_fields)
        if error_response:
            return error_response

        db_sess = None

        try:
            db_sess = db_session.create_session()

            # check if user exists
            existing_user = db_sess.query(User).filter(
                (User.username == data["username"]) | (User.email == data["email"])
            ).first()

            if existing_user:
                db_sess.close()
                return jsonify({
                    "error": "Логин или почта уже зарегистрирован",
                    "success": False
                }), 409

            # create new user
            user = User()
            user.username = data["username"]
            user.password = data["password"]
            user.email = data["email"]
            user.native_lang = data["native_language"]
            user.russian_level = data["russian_level"]
            user.registration_date = datetime.now()
            user.status = "unverified"

            db_sess.add(user)
            db_sess.commit()
            db_sess.refresh(user)

            user_id = user.id
            email = user.email

            # create verification code
            key = AuthService.create_verification_code(db_sess, user_id)
            db_sess.commit()

            # send secret key
            if not send_secret_key(email, key):
                # rollback when fail to send email
                AuthService.cleanup_user_and_verification(user_id)
                return jsonify({
                    "error": "Регистрация не прошла. Не удалось отправить код на почту.",
                    "success": False
                }), 500


            response_data = AuthService.get_user_response_data(user)

            return jsonify({
                "error": None,
                "success": True,
                "data": response_data
            }), 200

        except Exception as e:
            if db_sess:
                db_sess.rollback()
            return jsonify({
                "error": f"Регистрация не прошла: {str(e)}",
                "success": False
            }), 500
        finally:
            if db_sess:
                db_sess.close()


class VerificationService(AuthService):

    @staticmethod
    def handle_verification():
        error_response = AuthService.validate_request_method("POST")
        if error_response:
            return error_response

        data = request.get_json()
        user_id = data.get('user_id')
        verification_code = data.get('verification_code')

        if not user_id or not verification_code:
            return jsonify({
                "success": False,
                "error": "Отсутствует user_id или verification_code"
            }), 400

        db_sess = None

        try:
            db_sess = db_session.create_session()

            # check user
            user = db_sess.query(User).filter(User.id == user_id).first()
            if not user:
                return jsonify({
                    "success": False,
                    "error": "Пользователя отсутствует"
                }), 404

            # check if email is verified
            if user.status == "active":
                return jsonify({
                    "success": True,
                    "error": None,
                    "message": "Данная почта уже была подтверждена"
                }), 200

            # check verification code
            verification = db_sess.query(VerificationCode).filter(
                VerificationCode.user_id == user_id
            ).first()

            if not verification:
                return jsonify({
                    "success": False,
                    "error": "Код подтверждения отсутствует или уже не действует"
                }), 404

            # check if verification code is expired
            if verification.is_expired():
                db_sess.delete(verification)
                db_sess.commit()
                return jsonify({
                    "success": False,
                    "error": "Код подтверждения отсутствует уже не действует"
                }), 410

            # check if verification code is right
            if verification.code != str(verification_code):
                return jsonify({
                    "success": False,
                    "error": "Код подтверждения неверный"
                }), 401

            # verification successed
            db_sess.delete(verification)
            user.status = "active"
            user.verified_at = datetime.now()
            db_sess.commit()

            response_data = AuthService.get_user_response_data(user)

            return jsonify({
                "data": response_data,
                "success": True,
                "error": None,
                "message": "Верификация прошла успешно."
            }), 200

        except Exception as e:
            if db_sess:
                db_sess.rollback()
            return jsonify({
                "success": False,
                "error": f"Верификация не прошла: {str(e)}"
            }), 500
        finally:
            if db_sess:
                db_sess.close()


class LoginService(AuthService):

    @staticmethod
    def handle_login():

        error_response = AuthService.validate_request_method("POST")
        if error_response:
            return error_response

        data = request.get_json()

        if not data or "login" not in data or "password" not in data:
            return jsonify({"error": "Missing login or password", "success": False}), 400

        db_sess = None

        try:
            db_sess = db_session.create_session()

            login_input = data["login"]
            password_input = data["password"]

            # check user (by username or email)
            user = db_sess.query(User).filter(User.username == login_input).first()

            if not user:
                user = db_sess.query(User).filter(User.email == login_input).first()

            if not user:
                return jsonify({
                    "error": "Wrong login or password",
                    "success": False
                }), 401

            # check password
            if user.password != password_input:
                return jsonify({
                    "error": "Wrong login or password",
                    "success": False
                }), 401

            # check status
            if user.status != "active":
                return jsonify({
                    "error": "Account not verified. Please verify your email first.",
                    "success": False
                }), 403

            response_data = AuthService.get_user_response_data(user)

            return jsonify({
                "data": response_data,
                "success": True,
                "error": None,
                "message": "Login successful"
            }), 200

        except Exception as e:
            print(f"Login error: {e}")
            return jsonify({
                "error": f"Login failed: {str(e)}",
                "success": False
            }), 500
        finally:
            if db_sess:
                db_sess.close()


def send_secret_key(email, key):
    """
    Отправляет 6-значный код подтверждения на указанный email.

    Возвращает True в случае успеха, False в случае неудачи.
    """
    subject = f'Ваш код подтверждения в EduAdapt: {key}'
    body = f"""
      Здравствуйте, ваш секретный код в EduAdapt:
      {key}
      """

    msg = MIMEMultipart()
    msg['From'] = EMAIL_FROM
    msg['To'] = email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP(SMPT_SERVER, SMPT_PORT)
        server.starttls()
        server.login(EMAIL_FROM, EMAIL_PASSWORT)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        return False