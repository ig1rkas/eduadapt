# update_user.py
from datetime import datetime
from random import randint
from sqlalchemy.orm import Session
from data.users import User
from data.verification_code import VerificationCode
from data import db_session
from flask import jsonify, request
from modules.register_and_auth import send_secret_key


class UpdateUserService:

    @staticmethod
    def validate_request_method(expected_method: str = "POST"):
        if request.method != expected_method:
            return jsonify({"error": f"Use {expected_method} method", "success": False}), 405
        return None

    @staticmethod
    def validate_required_fields(data: dict, required_fields: list):
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({
                "error": f"Missing required fields: {', '.join(missing_fields)}",
                "success": False
            }), 400
        return None

    @staticmethod
    def get_user_response_data(user: User, include_message: str = None) -> dict:

        response_data = {
            "id": user.id,
            "username": user.username,
            "native_language": user.native_lang,
            "email": user.email,
            "russian_level": user.russian_level,
            "updated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

        if include_message:
            response_data["message"] = include_message

        return response_data

    @staticmethod
    def create_verification_for_email_change(db_sess: Session, user_id: int, new_email: str) -> str:

        verification_key = str(randint(100000, 999999))

        # delete old VerificationCode
        db_sess.query(VerificationCode).filter(
            VerificationCode.user_id == user_id
        ).delete()

        # create new VerificationCode
        verification = VerificationCode(user_id=user_id, code=verification_key)
        db_sess.add(verification)

        return verification_key


class ProfileUpdateService(UpdateUserService):

    @staticmethod
    def handle_profile_update():
        error_response = UpdateUserService.validate_request_method("POST")
        if error_response:
            return error_response

        data = request.get_json()
        if not data or "user_id" not in data:
            return jsonify({"error": "Missing user_id", "success": False}), 400

        db_sess = None

        try:
            db_sess = db_session.create_session()

            user = db_sess.query(User).filter(User.id == data["user_id"]).first()
            if not user:
                db_sess.close()
                return jsonify({"error": "user not found", "success": False}), 404

            # update username if it does not exist or repeat the old one
            if "username" in data:
                existing_user = db_sess.query(User).filter(User.username == data["username"]).first()
                if existing_user and existing_user.id != user.id:
                    db_sess.close()
                    return jsonify({"error": "username already exists", "success": False}), 409
                user.username = data["username"]

            # update native language
            if "native_language" in data:
                user.native_lang = data["native_language"]

            # update russian level
            if "russian_level" in data:
                user.russian_level = data["russian_level"]

            db_sess.commit()
            db_sess.refresh(user)

            response_data = UpdateUserService.get_user_response_data(user)

            return jsonify({
                "data": response_data,
                "success": True,
                "error": None,
            }), 200

        except Exception as e:
            if db_sess:
                db_sess.rollback()
            return jsonify({
                "error": f"Failed to update profile: {str(e)}",
                "success": False
            }), 500
        finally:
            if db_sess:
                db_sess.close()


class PasswordChangeService(UpdateUserService):

    @staticmethod
    def handle_password_change():

        error_response = UpdateUserService.validate_request_method("POST")
        if error_response:
            return error_response

        data = request.get_json()
        required_fields = ["user_id", "new_password", "current_password"]
        error_response = UpdateUserService.validate_required_fields(data, required_fields)
        if error_response:
            return error_response

        db_sess = None

        try:
            db_sess = db_session.create_session()

            user = db_sess.query(User).filter(User.id == data["user_id"]).first()
            if not user:
                db_sess.close()
                return jsonify({"error": "user not found", "success": False}), 404

            # check the current password
            if user.password != data["current_password"]:
                db_sess.close()
                return jsonify({"error": "invalid current password", "success": False}), 400

            # check if new password is same as the old one
            if data["current_password"] == data["new_password"]:
                db_sess.close()
                return jsonify({
                    "error": "new password must be different from current password",
                    "success": False
                }), 400

            user.password = data["new_password"]
            db_sess.commit()
            db_sess.refresh(user)

            response_data = UpdateUserService.get_user_response_data(user, "password changed successfully")

            return jsonify({
                "data": response_data,
                "success": True,
                "error": None,
            }), 200

        except Exception as e:
            if db_sess:
                db_sess.rollback()
            return jsonify({
                "error": f"Failed to change password: {str(e)}",
                "success": False
            }), 500
        finally:
            if db_sess:
                db_sess.close()


class EmailChangeService(UpdateUserService):

    @staticmethod
    def handle_email_change():
        error_response = UpdateUserService.validate_request_method("POST")
        if error_response:
            return error_response

        data = request.get_json()
        required_fields = ["user_id", "new_email"]
        error_response = UpdateUserService.validate_required_fields(data, required_fields)
        if error_response:
            return error_response

        db_sess = None

        try:
            db_sess = db_session.create_session()

            user = db_sess.query(User).filter(User.id == data["user_id"]).first()
            if not user:
                db_sess.close()
                return jsonify({"error": "user not found", "success": False}), 404

            existing_user = db_sess.query(User).filter(User.email == data["new_email"]).first()
            if existing_user:
                db_sess.close()
                return jsonify({"error": "email already exists", "success": False}), 400

            # check if new email is the same as the old one
            if user.email == data["new_email"]:
                db_sess.close()
                return jsonify({
                    "error": "new email must be different from current email",
                    "success": False
                }), 400

            user.email = data["new_email"]
            user.status = "unverified"

            # create a verification key
            verification_key = UpdateUserService.create_verification_for_email_change(
                db_sess, user.id, data["new_email"]
            )

            db_sess.commit()
            db_sess.refresh(user)

            # send email
            send_secret_key(user.email, verification_key)

            response_data = UpdateUserService.get_user_response_data(
                user, "Email updated. Please verify your new email."
            )

            return jsonify({
                "data": response_data,
                "success": True,
                "error": None
            }), 200

        except Exception as e:
            if db_sess:
                db_sess.rollback()
            return jsonify({"error": str(e), "success": False}), 500
        finally:
            if db_sess:
                db_sess.close()
