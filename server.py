import smtplib

from random import randint
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email_validator import validate_email

from config import EMAIL_FROM, EMAIL_PASSWORT, SMPT_PORT, SMPT_SERVER

from datetime import datetime

from flasgger import Swagger
from flask import Flask, jsonify, request

from data import db_session
from data.users import User

from wordcloud_generate import generate_word_cloud_api

db_session.global_init("db/main.db")

app = Flask(__name__)
swagger = Swagger(app)
auth_keys = {}

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
            - email
            - native_lang
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
        try:
          user = User()
          user.username = data["username"]
          user.password = data["password"]
          user.email = data["email"]
          user.native_lang = data["native_lang"]
          user.russian_level = data["russian_level"]
          user.status = "unverified"
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
                      "status": user.status,
                      "registration_date": datetime.now(),
                  },
              }
          ), 200
        except Exception as error:
          return jsonify(
              {
                  "error": error,
                  "success": False,
              }
          ), 500
          
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
                if user.status == "unverified": return jsonify({"success": False, "error": "verify email"})
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
        

@app.route('/api/auth/sendmail', methods=["POST"])
def send_secret_key():
  """methods
  {
    user_id: int,
    email: string,
  }

  reterns: secret key
  
  """
  global auth_keys
  
  data = request.get_json()
  
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
        'success': True,
        "data": {"key": key},
        
      }), 200
  except Exception as e:
      return jsonify({
        'success': False,
        "error": f"Произошла ошибка: {e}",
      }), 500
  finally:
      server.quit() 
      
@app.route("/api/auth/verify-mail", methods=["POST"])
def verify_mail():
  data = request.get_json()
  if auth_keys[data['user_id']] == data['verification_code']:
    db_sess = db_session.create_session()
    user = db_sess.query(User).filter(User.id == data["user_id"]).first()
    user.status = "active"
    db_sess.commit()
    db_sess.close()
    del auth_keys[data['user_id']]
    return jsonify({

        "data": {
            "id": user.id,
            "username": user.username,
            "native_language": user.native_lang,
            "email": user.email,
            "russian_level": user.russian_level,
            "status": user.status,
            "registration_date": user.registration_date,
            "verify_date": datetime.now()
        },
        "success": True,
        "error": None,
    }), 200
    
  return jsonify({
    "success": False,
    "error": 'uncorrect key',
  }), 500
  
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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
