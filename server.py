import smtplib

from random import randint
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
# from email_validator import validate_email

from config import EMAIL_FROM, EMAIL_PASSWORT, SMPT_PORT, SMPT_SERVER, EXPIRY_MINUTES

from datetime import datetime, timedelta

from flasgger import Swagger
from flask import Flask, jsonify, request, json

from data import db_session
from data.users import User
from data.verification_code import VerificationCode

from wordcloud_generate import generate_word_cloud_api

from deepseekApi import deepseekApi, adapt_educational_text

db_session.global_init("db/main.db")

app = Flask(__name__)
swagger = Swagger(app)

@app.route("/api")
def api():
    """
    Health check endpoint
    ---
    tags:
      - Health
    responses:
      200:
        description: API is running
        schema:
          type: object
          properties:
            status:
              type: integer
              example: 200
            data:
              type: string
              example: "You are in api"
    """
    return jsonify({"data": "You are in api"}), 200


@app.route("/api/adapt-text", methods=["POST"])
def adapt_text():
    """
    Text adaptation endpoint
    ---
    tags:
      - Text Processing
    summary: Adapt text complexity using either direct input or an uploaded file.
    description: This endpoint accepts text content either as a plain form field or as an uploaded file.

    parameters:
      # 1. 普通表单字段
      - name: adaptation_level
        in: formData # 表明它是表单数据
        type: string
        description: Target complexity level (e.g., A1, A2, B1, B2, C1, C2).
        required: false
        default: "B2"

      - name: text_input
        in: formData # 表明它是表单数据
        type: string
        description: Optional raw text input.
        required: false
        example: "Сложный научный текст..."

      - name: textFile
        in: formData # 在 OAI 2.0 中，文件也放在 formData
        type: file   # type 必须是 file
        description: Optional text file to upload.
        required: false

    consumes:
      - multipart/form-data
    responses:
      200:
        description: Text adapted successfully
        schema:
          type: object
          properties:
            success:
              type: boolean
            data:
              type: object
            text_with_terms:
              type: object
            text_without_terms:
              type: object
            error:
              type: string
              nullable: true
      400:
        description: Bad request
    """

    if 'multipart/form-data' not in request.content_type:
        return jsonify({
            "success": False,
            "data": None,
            "error": "Content-Type must be multipart/form-data"
        }), 415  # 415 UNSUPPORTED MEDIA TYPE

    target_level = request.form.get('adaptation_level', 'B2')
    original_text = request.form.get('text_input')
    file_part = request.files.get('textFile')

    try:
        result = adapt_educational_text(original_text, target_level)
        return jsonify(result)
    except Exception as e:
        return jsonify({
            "success": False,
            "data": None,
            "error": f"Adaptation failed: {str(e)}"
        }), 500

@app.route("/api/auth/registration", methods=["POST"])
def registration():
    """
    User registration endpoint
    ---
    tags:
      - Authentication
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - username
            - password
            - email
            - native_language
            - russian_level
          properties:
            username:
              type: string
              example: "john_doe"
            password:
              type: string
              example: "SecurePass123!"
            email:
              type: string
              example: "example@mail.ru"
            native_language:
              type: string
              example: "en"
            russian_level:
              type: string
              example: "B1"
    responses:
      200:
        description: User registered successfully
        schema:
          type: object
          properties:
            status:
              type: integer
              example: 200
            success:
              type: boolean
              example: true
            error:
              type: string
              nullable: true
            data:
              type: object
      500:
        description: Registration failed
        schema:
          type: object
          properties:
            status:
              type: integer
              example: 500
            error:
              type: string
            success:
              type: boolean
              example: false
    """

    if request.method != "POST":
        return jsonify({"error": "Use", "success": False}), 500

    data = request.get_json()
    required_fields = ["username", "password", "email", "native_language", "russian_level"]
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Не хватает данных", "success": False}), 400

    db_sess = None

    try:
        db_sess = db_session.create_session()

        # 检查用户是否已存在
        existing_user = db_sess.query(User).filter(
            (User.username == data["username"]) | (User.email == data["email"])
        ).first()

        if existing_user:
            db_sess.close()
            return jsonify({
                "error": "Логин или почта уже зарегистрирован",
                "success": False
            }), 409

        # 创建新用户
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

        key = str(randint(100000, 999999))

        # если есть старый код подтверждения, то удалить его
        old_codes = db_sess.query(VerificationCode).filter(
            VerificationCode.user_id == user_id
        ).all()

        for old_code in old_codes:
            db_sess.delete(old_code)

        # создать новый код подтверждения
        verification = VerificationCode(
            user_id=user_id,
            code=key,
            expiry_minutes=2
        )

        db_sess.add(verification)
        db_sess.commit()

        # отправить код на почту
        if not send_secret_key(email, key):
            # если код не отправлен на почту, то нужно удалить пользователя и сохраненный код
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
                return jsonify({
                    "error": "Регистрация не прошла. Не удалось отправить код на почту.",
                    "success": False
                }), 500
            finally:
                cleanup_session.close()

        response_data = {
            "id": user.id,
            "username": user.username,
            "native_language": user.native_lang,
            "email": user.email,
            "russian_level": user.russian_level,
            "status": user.status,
            "registration_date": user.registration_date.isoformat() if user.registration_date else None,
        }

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


@app.route("/api/auth/verify-mail", methods=["POST"])
def verify_mail():
    """
        Verify user email with verification code
        ---
        tags:
          - Authentication
        summary: Verify user email with verification code
        description: Verify user's email address using the verification code sent to their email. The verification code is valid for 2 minutes.
        parameters:
          - in: body
            name: body
            required: true
            schema:
              type: object
              required:
                - user_id
                - verification_code
              properties:
                user_id:
                  type: string
                  description: ID of the user to verify
                  example: "102"
                verification_code:
                  type: string
                  description: Verification code sent to user's email
                  example: "123456"
        responses:
          200:
            description: Email successfully verified
            schema:
              type: object
              properties:
                success:
                  type: boolean
                  example: true
                error:
                  type: string
                  example: null
                data:
                  type: object
                  properties:
                    id:
                      type: string
                      description: User ID
                      example: "123e4567-e89b-12d3-a456-426614174000"
                    username:
                      type: string
                      example: "john_doe"
                    native_language:
                      type: string
                      example: "en"
                    email:
                      type: string
                      format: email
                      example: "john@example.com"
                    russian_level:
                      type: string
                      enum: [beginner, intermediate, advanced, fluent]
                      example: "beginner"
                    status:
                      type: string
                      example: "active"
                    registration_date:
                      type: string
                      format: date-time
                      example: "2024-01-15T10:30:00Z"
                    verified_at:
                      type: string
                      format: date-time
                      example: "2024-01-15T10:32:00Z"
              400:
                description: Missing required parameters
                schema:
                  type: object
                  properties:
                    success:
                      type: boolean
                      example: false
                    error:
                      type: string
                      example: "Missing user_id or verification_code"
              401:
                description: Incorrect verification code
                schema:
                  type: object
                  properties:
                    success:
                      type: boolean
                      example: false
                    error:
                      type: string
                      example: "Incorrect verification code"
              404:
                description: User not found or verification code not found
                schema:
                  type: object
                  properties:
                    success:
                      type: boolean
                      example: false
                    error:
                      type: string
                      example: "No verification code found for this user_id or code has expired/already used"
              410:
                description: Verification code has expired
                schema:
                  type: object
                  properties:
                    success:
                      type: boolean
                      example: false
                    error:
                      type: string
                      example: "Verification code has expired"
              500:
                description: Wrong HTTP method used
                schema:
                  type: object
                  properties:
                    success:
                      type: boolean
                      example: false
                    error:
                      type: string
                      example: "Use the POST method"
        """
    if request.method != "POST":
        return jsonify({"error": "Use POST Method", "success": False}), 405

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

        user = db_sess.query(User).filter(User.id == user_id).first()
        if not user:
            return jsonify({
                "success": False,
                "error": "Пользователя отсутствует"
            }), 404

        if user.status == "active":
            return jsonify({
                "success": True,
                "error": None,
                "message": "Данная почта уже была подтверждена"
            }), 200

        # поиск кода подтверждения в бд
        verification = db_sess.query(VerificationCode).filter(
            VerificationCode.user_id == user_id
        ).first()

        if not verification:
            return jsonify({
                "success": False,
                "error": "Код подтверждения отсутствует или уже не действует"
            }), 404

        if verification.is_expired():
            db_sess.delete(verification)
            db_sess.commit()
            return jsonify({
                "success": False,
                "error": "Код подтверждения отсутствует уже не действует"
            }), 410

        if verification.code != str(verification_code):
            return jsonify({
                "success": False,
                "error": "Код подтверждения неверный"
            }), 401

        # Верификация прошла, удалить данные в бд verification_codes
        db_sess.delete(verification)
        user.status = "active"
        user.verified_at = datetime.now()
        db_sess.commit()

        response_data = {
            "id": user.id,
            "username": user.username,
            "native_language": user.native_lang,
            "email": user.email,
            "russian_level": user.russian_level,
            "status": user.status,
            "registration_date": user.registration_date.isoformat() if user.registration_date else None,
            "verified_at": user.verified_at.isoformat() if user.verified_at else None
        }

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

@app.route("/api/auth/login", methods=["POST"])
def login():
    """
    User login endpoint
     ---
     tags:
       - Authentication
     parameters:
       - in: body
         name: body
         required: true
         schema:
           type: object
           required:
             - login
             - password
           properties:
             login:
               type: string
               description: Username or email
               example: "john_doe"
             password:
               type: string
               example: "SecurePass123!"
     responses:
       200:
         description: Login successful
         schema:
           type: object
           properties:
             status:
               type: integer
               example: 200
             success:
               type: boolean
               example: true
             error:
               type: string
               nullable: true
             data:
               type: object
               properties:
                 id:
                   type: integer
                 username:
                   type: string
                 native_language:
                   type: string
                 email:
                   type: string
                 russian_level:
                   type: string
                 registration_date:
                   type: string
       500:
         description: Login failed
         schema:
           type: object
           properties:
             status:
               type: integer
               example: 500
             error:
               type: string
             success:
               type: boolean
               example: false
    """
    if request.method != "POST":
        return jsonify({"error": "Use POST method", "success": False}), 405

    data = request.get_json()

    if not data or "login" not in data or "password" not in data:
        return jsonify({"error": "Missing login or password", "success": False}), 400

    db_sess = None

    try:
        db_sess = db_session.create_session()

        login_input = data["login"]
        password_input = data["password"]

        user = db_sess.query(User).filter(User.username == login_input).first()

        if not user:
            user = db_sess.query(User).filter(User.email == login_input).first()

        if not user:
            return jsonify({
                "error": "Wrong login or password",
                "success": False
            }), 401

        if user.password != password_input:
            return jsonify({
                "error": "Wrong login or password",
                "success": False
            }), 401

        if user.status != "active":
            return jsonify({
                "error": "Account not verified. Please verify your email first.",
                "success": False
            }), 403

        response_data = {
            "id": user.id,
            "username": user.username,
            "native_language": user.native_lang,
            "email": user.email,
            "russian_level": user.russian_level,
            "status": user.status,
            "registration_date": user.registration_date.isoformat() if user.registration_date else None,
            "verified_at": user.verified_at.isoformat() if user.verified_at else None,
        }

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


@app.route("/api/user/profile", methods=["POST"])
def profile(): 
    """
    Update user profile endpoint 
    --- 
    tags: 
      - User Management 
    parameters: 
      - in: body 
        name: body 
        required: true 
        schema: 
          type: object 
          required: 
            - user_id 
          properties: 
            user_id: 
              type: integer 
              description: User ID to update 
              example: 102 
            username: 
              type: string 
              example: "ivanov_new" 
            native_language: 
              type: string 
              example: "ru" 
            russian_level: 
              type: string 
              example: "B2" 
    responses: 
      200: 
        description: Profile updated successfully 
        schema: 
          type: object 
          properties: 
            success: 
              type: boolean 
              example: true 
            data: 
              type: object 
              properties: 
                id: 
                  type: integer 
                username: 
                  type: string 
                native_language: 
                  type: string 
                email: 
                  type: string 
                russian_level: 
                  type: string 
                updated_at: 
                  type: string 
            error: 
              type: string 
              nullable: true 
      500: 
        description: Update failed
    """
    if request.method != "POST":
        return jsonify({"error": "Use POST method", "success": False}), 405

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
        if "username" in data:
            existing_user = db_sess.query(User).filter(User.username == data["username"]).first()
            if existing_user:
                db_sess.close()
                return jsonify({"error": "username already exists", "success": False}), 409
            user.username=data["username"]
        if "native_language" in data:
            user.native_lang=data["native_language"]
        if "russian_level" in data:
            user.russian_level=data["russian_level"]
        db_sess.commit()
        db_sess.refresh(user)
        return jsonify({

        "data": {
            "id": user.id,
            "username": user.username,
            "native_language": user.native_lang,
            "email": user.email,
            "russian_level": user.russian_level,
            "updated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
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

@app.route("/api/user/change-password", methods=["POST"])
def change_password(): 
    """
    Change user password endpoint 
    --- 
    tags: 
      - User Management 
    parameters: 
      - in: body 
        name: body 
        required: true 
        schema: 
          type: object 
          required: 
            - user_id 
            - current_password 
            - new_password 
          properties: 
            user_id: 
              type: integer 
              description: User ID 
              example: 102 
            current_password: 
              type: string 
              description: Current password 
              example: "OldPass123!" 
            new_password: 
              type: string 
              description: New password 
              example: "NewSecurePass456!" 
    responses: 
      200: 
        description: Password changed successfully 
        schema: 
          type: object 
          properties: 
            success: 
              type: boolean 
              example: true 
            data: 
              type: object 
              properties: 
                message: 
                  type: string 
                user_id: 
                  type: integer 
                updated_at: 
                  type: string 
            error: 
              type: string 
              nullable: true 
      500: 
        description: Password change failed
    """
    if request.method != "POST":
        return jsonify({"error": "Use POST method", "success": False}), 405

    data = request.get_json()
    if "user_id" not in data or "new_password" not in data or "current_password" not in data:
        return jsonify({"error": "Missing required fields", "success": False}), 400
    db_sess = None
    try:
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.id == data["user_id"]).first()
        if not user:
            db_sess.close()
            return jsonify({"error": "user not found", "success": False}), 404
        if user.password != data["current_password"]:
            db_sess.close()
            return jsonify({"error": "invalid current password", "success": False}), 400
        if data["current_password"]==data["new_password"]:
            db_sess.close()
            return jsonify({"error": "new password must be different from current password", "success": False}), 400
        user.password=data["new_password"]
        db_sess.commit()
        db_sess.refresh(user)
        return jsonify({
            "data": {
                "id": user.id,
                "message": "password changed successfully",
                "updated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            },
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


@app.route("/api/user/change-email", methods=["POST"])
def change_email(): 
    """
    Change user email endpoint 
    --- 
    tags: 
      - User Management 
    parameters: 
      - in: body 
        name: body 
        required: true 
        schema: 
          type: object 
          required: 
            - user_id 
            - new_email 
          properties: 
            user_id: 
              type: integer 
              description: User ID 
              example: 102 
            new_email: 
              type: string 
              description: New email address 
              example: "new_email@mail.ru" 
    responses: 
      200: 
        description: Verification code sent successfully 
        schema: 
          type: object 
          properties: 
            success: 
              type: boolean 
              example: true 
            data: 
              type: object 
              properties: 
                message: 
                  type: string 
                email: 
                  type: string 
                expires_in: 
                  type: integer 
            error: 
              type: string 
              nullable: true 
      500: 
        description: Bad request
    """
    if request.method != "POST":
        return jsonify({"error": "Use POST method", "success": False}), 405

    data = request.get_json()

    if "user_id" not in data or "new_email" not in data:
        return jsonify({"error": "Missing required fields", "success": False}), 400

    db_sess = db_session.create_session()
    try:
        user = db_sess.query(User).filter(User.id == data["user_id"]).first()

        if not user:
            db_sess.close()
            return jsonify({"error": "user not found", "success": False}), 404

        existing_user = db_sess.query(User).filter(User.email == data["new_email"]).first()
        if existing_user:
            db_sess.close()
            return jsonify({"error": "email already exists", "success": False}), 400
        if user.email==data["new_email"]:
            db_sess.close()
            return jsonify({"error": "new email must be different from current email", "success": False}), 400

        user.email=data["new_email"]

        user.status = "unverified"
        verification_key = str(randint(100000, 999999))

        # удалить старый код подтверждения
        db_sess.query(VerificationCode).filter(
            VerificationCode.user_id == user.id
        ).delete()

        verification = VerificationCode(user_id=user.id, code=verification_key)
        db_sess.add(verification)
        db_sess.commit()
        db_sess.refresh(user)

        send_secret_key(user.email, verification_key)

        return jsonify({
            "data": {
                "id": user.id,
                "message": "Email updated. Please verify your new email.",
                "updated_at": datetime.now().isoformat()
            },
            "success": True,
            "error": None
        }), 200

    except Exception as e:
        return jsonify({"error": str(e), "success": False}), 500
    finally:
        db_sess.close()


@app.route('/api/word-cloud', methods=['POST'])
def word_cloud_endpoint():
    """
    Generate word cloud from text endpoint 
    --- 
    tags: 
      - Text Processing 
    parameters: 
      - in: body 
        name: body 
        required: true 
        schema: 
          type: object 
          required: 
            - text 
          properties: 
            text: 
              type: string 
              description: Text to generate word cloud from 
              example: "Это пример текста для генерации облака слов. Текст должен содержать достаточно слов для создания визуализации." 
            width: 
              type: integer 
              description: Width of the word cloud image in pixels 
              default: 800 
              example: 800 
            height: 
              type: integer 
              description: Height of the word cloud image in pixels 
              default: 400 
              example: 400 
    responses: 
      200: 
        description: Word cloud generated successfully 
        schema: 
          type: object 
          properties: 
            success: 
              type: boolean 
              example: true 
            data: 
              type: object 
              properties: 
                image_base64: 
                  type: string 
                  description: Base64 encoded PNG image of the word cloud 
                  example: "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA..." 
                image_format: 
                  type: string 
                  example: "png" 
                width: 
                  type: integer 
                  example: 800 
                height: 
                  type: integer 
                  example: 400 
            error: 
              type: string 
              nullable: true 
      500: 
        description: Internal server error
    """
    try:
        # Получение данных из запроса
        data = request.get_json()

        if not data or 'text' not in data:
            return jsonify({
                "success": False,
                "data": None,
                "error": "Текст обязателен для генерации облака слов"
            }), 400

        text = data['text']
        width = data.get('width', 800)
        height = data.get('height', 400)

        # Генерация облака слов
        result = generate_word_cloud_api(text, width, height)

        return jsonify(result)

    except Exception as e:
        return jsonify({
            "success": False,
            "data": None,
            "error": f"Внутренняя ошибка сервера: {str(e)}"
        }), 500

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
  
@app.route("/api/auth/recover-password", methods=["POST"])
def recover_password():
  global auth_keys
  data = request.get_json()
  if "verification_code" not in data:
    if "email" in data and "user_id" in data:
      key = randint(100000, 999999)
      subject = f'Ваш код подтверждения в EduAdapt: {key}'
      body = f"""
      Здравствуйте, ваш секретный код в EduAdapt:
      {key}
      """

      msg = MIMEMultipart()
      msg['From'] = EMAIL_FROM
      msg['To'] = data['email']
      msg['Subject'] = subject
      msg.attach(MIMEText(body, 'plain'))

      try:
          server = smtplib.SMTP(SMPT_SERVER, SMPT_PORT)
          server.starttls()  
          server.login(EMAIL_FROM, EMAIL_PASSWORT)  
          server.send_message(msg) 
          auth_keys[data['user_id']] = key
          return jsonify({
            "success": True,
            "data": {
              "message": "Password reset code has been sent to your email",
              "email": data['email'],
              "expires_in": 600
            },
            "error": None
          }), 200
      except Exception as e:
          return jsonify({
            'success': False,
            "error": f"Произошла ошибка: {e}",
          }), 500
      finally:
          server.quit() 
    else:
      return jsonify({
        "success": False,
        "error": "You should give email or user_id in params"
      }), 500
  else:
    if auth_keys[data['user_id']] == data['verification_code']:
      db_sess = db_session.create_session()
      user = db_sess.query(User).filter(User.id == data["user_id"]).first()
      user.password = data['new_password']
      db_sess.commit()
      db_sess.close()
      return jsonify({
        "success": True,
        "data": {
          "message": "Password has been reset successfully",
          "user_id": user.id
        },
        "error": None
      })
    else:
      return jsonify({
        "success": False,
        "error": "Uncorrect verification code"
      })

@app.route("/api/generate-test", methods=["POST"])
def get_summarising_test():
    """
    Generates a test based on source text
    ---
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            text:
              type: string
    responses:
      200:
        description: Text generated successfully
        schema:
          type: object
          properties:
            success:
              type: bool
              example: true
            data:
              type: object
              properties:
                questions:
                  type: list
                  properties:
                    type: object
                    properties:
                      id:
                        type: integer
                      question:
                        type: string
                      type:
                        type: string
                        default: one_choice
                      options:
                        type: list
                        properties:
                          type: string
                      correct_answer:
                        type: string
                      explanation:
                        type: string
                test_config:
                  type: object
                  properties:
                    total_questions:
                      type: integer
            error:
              type: string
              default: null
      500:
        schema:
          type: object
          properties:
            success:
              type: bool
              default: false
            data:
              type: null
            error:
              type: string
              example: "Внутренняя ошибка сервера: <error_message>"
    """
    data = request.get_json()

    if not data or not data["text"]:
        return jsonify({
            "success": False,
            "data": None,
            "error": "Текст обязателен для генерации теста"
        }), 500

    source_text = data["text"]
    prompt = f"""
ЗАДАЧА:
Составь на основе приведенного ниже текста тест из нескольких вопросов, чтобы проверить, как читатель понял его содержание. Для каждого вопроса сделай несколько вариантов ответа, из которых верным будет только один. Количество вопросов и вариантов ответов определи сам, исходя из длины текста и количества важной информации в нем. При генерации ответа не используй разметку, отправь чистый текст, как указано в шаблоне ниже.

ИСХОДНЫЙ ТЕКСТ: 
{source_text}

ФОРМАТ ОТВЕТА (JSON):
{{
"success": true,
"data": {{
    "questions": [
      {{
        "id": <порядковый номер вопроса, начиная с 1>,
        "question": "<вопрос>",
        "type": "one_choice",
        "options": [
          "<вариант 1>",
          "<вариант 2>", 
          …
        ],
        "correct_answer": <номер правильного ответа>,
        "explanation": "<цитата из текста, по которой можно определить, что данный ответ является правильным>"
      }}
    ],
    "test_config": {{
      "total_questions": <количество вопросов>
    }}
  }},
"error": null
}}
    """

    try:
        response = deepseekApi(prompt)
        if response["status"] == 200:
            json_data = json.loads(response["data"])
            return jsonify(json_data), 200
        else:
            return jsonify({
                "success": False,
                "data": None,
                "error": "Внутренняя ошибка сервера " + response["reason"]
            }), response["status"]
    except Exception as e:
        return jsonify({
            "success": False,
            "data": None,
            "error": f"Внутренняя ошибка сервера: {str(e)}"
        }), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
