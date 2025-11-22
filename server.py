from datetime import datetime

from flasgger import Swagger
from flask import Flask, jsonify, request

from data import db_session
from data.users import User

from wordcloud import generate_word_cloud_api

from deepseekApi import adapt_educational_text

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
    return jsonify({"status": 200, "data": "You are in api"})


@app.route("/api/adapt-text", methods=["POST"])
def adapt_text():
    """
    Text adaptation endpoint
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
            return jsonify({"status": 500, "error": "Use other login", "success": False})

        user = User()
        user.username = data["username"]
        user.password = data["password"]
        user.phone_number = data["phone_number"]
        user.native_lang = data["native_lang"]
        user.russian_level = data["russian_level"]
        user.registration_date = datetime.now()
        db_sess.add(user)
        db_sess.commit()

        user = db_sess.query(User).filter(User.username == data["username"]).first()
        db_sess.close()

        return jsonify(
            {
                "status": 200,
                "error": None,
                "success": True,
                "data": {
                    "id": user.id,
                    "username": user.username,
                    "native_language": user.native_lang,
                    "phone_number": user.phone_number,
                    "russian_level": user.russian_level,
                    "registration_date": datetime.now(),
                },
            }
        )

    else:
        return jsonify({"status": 500, "error": "Use the POST method", "success": False})


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
                users = db_sess.query(User).filter(User.phone_number == data["login"]).all()
            if user:
                if user.password == data["password"]:
                    answer = {
                        "status": 200,
                        "data": {
                            "id": user.id,
                            "username": user.username,
                            "native_language": user.native_lang,
                            "phone_number": user.phone_number,
                            "russian_level": user.russian_level,
                            "registration_date": user.registration_date,
                        },
                        "success": True,
                        "error": None,
                    }
                else:
                    answer = {"status": 500, "error": "wrong password", "success": False}
            elif users:
                for user in users:
                    if user.password == data["password"]:
                        answer = {
                            "status": 200,
                            "data": {
                                "id": user.id,
                                "username": user.username,
                                "native_language": user.native_lang,
                                "phone_number": user.phone_number,
                                "russian_level": user.russian_level,
                                "registration_date": user.registration_date,
                            },
                            "success": True,
                            "error": None,
                        }
                        break
            else:
                answer = {"status": 500, "error": "Wrong login", "success": False}
        else:
            answer = {"status": 500, "error": "Give the login param in data", "success": False}
    else:
        answer = {"status": 500, "error": "Use POST method", "success": False}
    db_sess.close()

    return jsonify(answer)


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
        if logs:
            answer = {"status": 200, "data": {"changed_data": logs}}
        else:
            answer = {"status": 500, "data": {"Nothing changed"}}

        return jsonify(answer)




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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
