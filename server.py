import json
from datetime import datetime

import pandas as pd
import requests
from flasgger import Swagger
from flask import Flask, jsonify, request

from data import db_session
from data.users import User

db_session.global_init("db/main.db")

app = Flask(__name__)
swagger = Swagger(app)
API_KEY = "sk-ca488baceb8843069f6c782043f1d54f"
API_URL = "https://api.deepseek.com/v1/chat/completions"
TEXTOMETR_URL = "https://api.textometr.ru/analyze"


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


def deepseekApi(user_prompt: str, system_prompt="You are helpful assistant") -> requests:
    """
    function to get a response from deepseek

    Args:
        user_prompt (str): user prompt content
        system_prompt (str): settings for deepseek

    Returns:
        requests: response from AI
    """
    global API_KEY
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}
    data = {
        "model": "deepseek-chat",
        "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        "temperature": 0.7,
        "max_tokens": 2048,
    }
    response = requests.post(API_URL, json=data, headers=headers)

    if response.status_code == 200:
        result = response.json()
        return {"status": 200, "data": result["choices"][0]["message"]["content"]}
    else:
        return {"status": response.status_code, "reason": response.text}


METRICS = [
    "level_number",
    "level_comment",
    "words",
    "sentences",
    "key_words",
    "reading_for_detail_speed",
    "skim_reading_speed",
    "rki_children_1000",
    "rki_children_5000",
]


def getTextometrAnalysis(text: str) -> dict:
    jsonData = json.dumps({"text": text})
    response = requests.request("POST", TEXTOMETR_URL, data=jsonData)
    responseJson = json.loads(response.text)
    return responseJson


def textAnalysis(text_with_terms: str, text_without_terms: str, level: str) -> None:
    textsData = {}
    levelWithoutTerms = getTextometrAnalysis(text_without_terms)
    resultWithTerms = getTextometrAnalysis(text_with_terms)
    textsData["text_ok"] = bool(resultWithTerms["text_ok"]) and bool(levelWithoutTerms["text_ok"])
    textsData["text_error_message"] = resultWithTerms["text_error_message"] + levelWithoutTerms["text_error_message"]
    for metric in METRICS[:2]:
        textsData[metric] = levelWithoutTerms[metric]
    for metric in METRICS[2:]:
        textsData[metric] = resultWithTerms[metric]
    inLevelName = "in" + level
    not_inLevelName = "not_in" + level
    textsData[inLevelName] = resultWithTerms[inLevelName]
    textsData[not_inLevelName] = resultWithTerms[not_inLevelName]
    return toJson(textsData, level)


def toJson(data: dict, level: str):
    returnedDict = {
        "success": data["text_ok"],
        "data": {
            "text_with_terms": {
                "metrics": {metric: data[metric] for metric in METRICS[2:]},
                "in_level": str(data["in" + level]) + " %",
                "not_in_level": data["not_in" + level],
            },
            "text_without_terms": {
                "level_metrics": {"level_number": data["level_number"], "level_comment": data["level_comment"]}
            },
            "error": data["text_error_message"],
        },
    }
    return json.dumps(returnedDict)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
