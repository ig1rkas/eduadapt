from flasgger import Swagger
from flask import Flask, jsonify, request, json

from modules import register_and_auth as auth
from data import db_session
from modules.deepseek_api import deepseek_api
from modules.test_generate import get_test_generate_user_prompt
from modules.text_adaptation import adapt_educational_text
from modules.update_user import ProfileUpdateService, PasswordChangeService, EmailChangeService
from modules.wordcloud_generate import generate_word_cloud_api

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

    Parameters:
      - name: adaptation_level
        in: formData
        type: string
        description: Target complexity level (e.g., B1, B2).
        required: false
        default: "B2"

      - name: text_input
        in: formData
        type: string
        description: Optional raw text input.
        required: false
        example: "Сложный научный текст..."

      - name: textFile
        in: formData
        type: file
        description: Optional text file to upload.
        required: false

      - name: native_language
        in: formData
        type: string
        description: Native language.
        required: true
        example: "en"

    Consumes:
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
    native_language = request.form.get('native_language')

    try:
        result = adapt_educational_text(original_text, target_level, native_language)
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
    return auth.RegistrationService.handle_registration()


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
    return auth.VerificationService.handle_verification()


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
    return auth.LoginService.handle_login()


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
    return ProfileUpdateService.handle_profile_update()


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
    return PasswordChangeService.handle_password_change()


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
    return EmailChangeService.handle_email_change()


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
                  example: "data:image/png;base64,iVBORw0KGgoUhEUgAA..."
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


# Это api опционально, еще не до конца сделано, поэтому не добавляете docstring для него
# @app.route("/api/auth/recover-password", methods=["POST"])
# def recover_password():
#     global auth_keys
#     data = request.get_json()
#     if "verification_code" not in data:
#         if "email" in data and "user_id" in data:
#             key = randint(100000, 999999)
#             subject = f'Ваш код подтверждения в EduAdapt: {key}'
#             body = f"""
#       Здравствуйте, ваш секретный код в EduAdapt:
#       {key}
#       """
#
#             msg = MIMEMultipart()
#             msg['From'] = EMAIL_FROM
#             msg['To'] = data['email']
#             msg['Subject'] = subject
#             msg.attach(MIMEText(body, 'plain'))
#
#             try:
#                 server = smtplib.SMTP(SMPT_SERVER, SMPT_PORT)
#                 server.starttls()
#                 server.login(EMAIL_FROM, EMAIL_PASSWORT)
#                 server.send_message(msg)
#                 auth_keys[data['user_id']] = key
#                 return jsonify({
#                     "success": True,
#                     "data": {
#                         "message": "Password reset code has been sent to your email",
#                         "email": data['email'],
#                         "expires_in": 600
#                     },
#                     "error": None
#                 }), 200
#             except Exception as e:
#                 return jsonify({
#                     'success': False,
#                     "error": f"Произошла ошибка: {e}",
#                 }), 500
#             finally:
#                 server.quit()
#         else:
#             return jsonify({
#                 "success": False,
#                 "error": "You should give email or user_id in params"
#             }), 500
#     else:
#         if auth_keys[data['user_id']] == data['verification_code']:
#             db_sess = db_session.create_session()
#             user = db_sess.query(User).filter(User.id == data["user_id"]).first()
#             user.password = data['new_password']
#             db_sess.commit()
#             db_sess.close()
#             return jsonify({
#                 "success": True,
#                 "data": {
#                     "message": "Password has been reset successfully",
#                     "user_id": user.id
#                 },
#                 "error": None
#             })
#         else:
#             return jsonify({
#                 "success": False,
#                 "error": "Uncorrect verification code"
#             })


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
      400:
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
              example: "Текст обязателен для генерации теста"
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
        }), 400

    source_text = data["text"]
    prompt = get_test_generate_user_prompt(source_text)

    messages = [
        {"role": "system", "content": "Ты - помощник для генерации теста по учебному тексту"},
        {"role": "user", "content": prompt}
    ]

    try:
        response = deepseek_api(messages)

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
