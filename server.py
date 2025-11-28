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

from deepseekApi import deepseekApi

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
      """methods
      {
        usermail: string,
      }

      reterns: secret key

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
              example: error occurred
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
                "error": response["reason"]
            }), response["status"]
    except Exception as e:
        return jsonify({
            "success": False,
            "data": None,
            "error": f"Внутренняя ошибка сервера: {str(e)}"
        }), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
