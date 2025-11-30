import smtplib

from random import randint
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
# from email_validator import validate_email

from config import EMAIL_FROM, EMAIL_PASSWORT, SMPT_PORT, SMPT_SERVER

from datetime import datetime

from flasgger import Swagger
from flask import Flask, jsonify, request, json

from data import db_session
from data.users import User

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
    parameters:
      - in: body..
        name: body
        required: true
        schema:
          type: object
          required:
            - text
          properties:
            text:
              type: string
              description: Original text to adapt
              example: "Сложный научный текст для адаптации..."
            target_level:
              type: string
              description: Target complexity level (A1, A2, B1, B2, C1, C2)
              example: "B2"
            max_attempts:
              type: integer
              description: Maximum adaptation attempts
              example: 3
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
    data = request.get_json()

    if not data or 'text' not in data:
        return jsonify({
            "success": False,
            "data": None,
            "error": "Text is required"
        }), 400

    original_text = data['text']
    target_level = data.get('target_level', 'B2')
    max_attempts = data.get('max_attempts', 3)

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
            - phone_number
            - native_lang
            - russian_level
          properties:
            username:
              type: string
              example: "john_doe"
            password:
              type: string
              example: "SecurePass123!"
            phone_number:
              type: string
              example: "+79161234567"
            native_lang:
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
    if request.method == "POST":
        data = request.get_json()
        db_sess = db_session.create_session()
        other = db_sess.query(User).filter(User.username == data["username"]).first()
        if other:
            return jsonify({"error": "Use other login", "success": False}), 500

        user = User()
        user.username = data["username"]
        user.password = data["password"]
        user.email = data["email"]
        user.native_lang = data["native_language"]
        user.russian_level = data["russian_level"]
        user.registration_date = datetime.now()
        db_sess.add(user)
        db_sess.commit()

        user = db_sess.query(User).filter(User.username == data["username"]).first()
        db_sess.close()

        return jsonify(
            {
                "error": None,
                "success": True,
                "data": {
                    "id": user.id,
                    "username": user.username,
                    "native_language": user.native_lang,
                    "email": user.email,
                    "russian_level": user.russian_level,
                    "registration_date": datetime.now(),
                },
            }
        ), 200

    else:
        return jsonify({"error": "Use the POST method", "success": False}), 500


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
               description: Username or phone number
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
                 phone_number:
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
    if request.method == "POST":
        data = request.get_json()
        print(data)
        db_sess = db_session.create_session()
        if "login" in data:
            user = db_sess.query(User).filter(User.username == data["login"]).first()
            if not user:
                users = db_sess.query(User).filter(User.email == data["login"]).all()
            if user:
                if user.password == data["password"]:
                    db_sess.close()
                    return jsonify({
                        "data": {
                            "id": user.id,
                            "username": user.username,
                            "native_language": user.native_lang,
                            "email": user.email,
                            "russian_level": user.russian_level,
                            "registration_date": user.registration_date,
                        },
                        "success": True,
                        "error": None,
                    }), 200
                else:
                    db_sess.close()
                    return jsonify({"error": "wrong password", "success": False}), 500
            elif users:
                for user in users:
                    if user.password == data["password"]:
                        db_sess.close()
                        return jsonify({

                            "data": {
                                "id": user.id,
                                "username": user.username,
                                "native_language": user.native_lang,
                                "email": user.email,
                                "russian_level": user.russian_level,
                                "registration_date": user.registration_date,
                            },
                            "success": True,
                            "error": None,
                        }), 200
            else:
                db_sess.close()
                return jsonify({"error": "Wrong login", "success": False}), 500
        else:
            db_sess.close()
            return jsonify({"error": "Give the login param in data", "success": False}), 500
    else:
        db_sess.close()
        return jsonify({"error": "Use POST method", "success": False}), 500




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
    if request.method == "POST":
        data = request.get_json()
        print(data)
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.id == data["user_id"]).first()
        if not user:
            db_sess.close()
            return jsonify({"error": "user not found", "success": False}), 500
        if "username" in data: 
            existing_user = db_sess.query(User).filter(User.username == data["username"]).first()
            if existing_user:
                db_sess.close()
                return jsonify({"error": "username already exists", "success": False}), 500
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
    else:
        db_sess.close()
        return jsonify({"error": "use POST method", "success": False}), 500
    


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
    if request.method == "POST":
        data = request.get_json()
        if "user_id" not in data or "new_password" not in data or "current_password" not in data:
            return jsonify({"error": "Missing required fields", "success": False}), 500
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.id == data["user_id"]).first()
        if not user:
            db_sess.close()
            return jsonify({"error": "user not found", "success": False}), 500
        if user.password != data["current_password"]:
            db_sess.close()
            return jsonify({"error": "invalid current password", "success": False}), 500
        if data["current_password"]==data["new_password"]:
            db_sess.close()
            return jsonify({"error": "new password must be different from current password", "success": False}), 500
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
    else:
        db_sess.close()
        return jsonify({"error": "use POST method", "success": False}), 500




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
    if request.method == "POST":
        data = request.get_json()
        if "user_id" not in data or "new_email" not in data:
            return jsonify({"error": "Missing required fields", "success": False}), 500
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.id == data["user_id"]).first()
        if not user:
            db_sess.close()
            return jsonify({"error": "user not found", "success": False}), 500 
        existing_user = db_sess.query(User).filter(User.email == data["new_email"]).first()
        if existing_user:
            db_sess.close()
            return jsonify({"error": "email already exists", "success": False}), 500
        if user.email==data["new_email"]:
            db_sess.close()
            return jsonify({"error": "new email must be different from current email", "success": False}), 500
        user.email=data["new_email"]
        db_sess.commit()
        db_sess.refresh(user)
        return jsonify({

            "data": {
                "id": user.id,
                "message": "email changed successfully",
                "updated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            },
            "success": True,
            "error": None,
        }), 200
    else:
        db_sess.close()
        return jsonify({"error": "use POST method", "success": False}), 500




@app.route("/api/editdata/<id>", methods=["PATCH"])
def editData(id: int):
    """
    Edit user data endpoint
    ---
    tags:
      - User Management
    parameters:
      - in: path
        name: id
        type: integer
        required: true
        description: User ID
        example: 1
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            username:
              type: string
            password:
              type: string
            phone_number:
              type: string
            native_lang:
              type: string
            russian_level:
              type: string
    responses:
      200:
        description: Data updated successfully
        schema:
          type: object
          properties:
            status:
              type: integer
              example: 200
            data:
              type: object
              properties:
                changed_data:
                  type: array
                  items:
                    type: string
      500:
        description: Update failed
        schema:
          type: object
          properties:
            status:
              type: integer
              example: 500
            data:
              type: object
    """
    if request.method == "PATCH":
        db_sess = db_session.create_session()
        data = request.json()
        user = (
            db_sess.query(User).filter(User.id == id).first()
            if id
            else db_sess.query(User).filter(User.username == data["name"])
        )

        logs = []
        for value in data:
            try:
                exec(f"user.{value} = data['{value}']")
                logs.append(value)
            except Exception:
                pass
        db_sess.close()
        if logs:
            return jsonify({"data": {"changed_data": logs}}), 200
        else:
            return jsonify({"data": {"Nothing changed"}}), 200

 




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
        

@app.route('/api/sendmail', methods=["POST"])
def send_secret_key() -> None:
    """
    Send verification code to email endpoint 
    --- 
    tags: 
      - Email 
    parameters: 
      - in: body 
        name: body 
        required: true 
        schema: 
          type: object 
          required: 
            - usermail 
          properties: 
            usermail: 
              type: string 
              description: Email address to send verification code to 
              example: "user@example.com" 
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
                key: 
                  type: integer 
                  description: 6-digit verification code 
                  example: 123456 
            error: 
              type: string 
              nullable: true 
      500: 
        description: Failed to send email
    """
    data = request.get_json()

    key = randint(100000, 999999)

    subject = f'Ваш код подтверждения в EduAdapt: {key}'
    body = f"""
    Здравствуйте, ваш секретный код в EduAdapt:
    {key}
    """

    msg = MIMEMultipart()
    msg['From'] = EMAIL_FROM
    msg['To'] = data['usermail']
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP(SMPT_SERVER, SMPT_PORT)
        server.starttls()
        server.login(EMAIL_FROM, EMAIL_PASSWORT)
        server.send_message(msg)
        return jsonify({
          'success': True,
          "data": {"key": key},

        }), 200
    except Exception as e:
        return jsonify({
          'success': False,
          "error": f"Произошла ошибка: {e}",
        })
    finally:
        server.quit()  # close connection


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
              example: Внутренняя ошибка сервера: <error_message>
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
