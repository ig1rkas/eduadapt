import requests

from flask import Flask, request, jsonify
from datetime import datetime

from data import db_session
from data.users import User

db_session.global_init("db/main.db")

app = Flask(__name__)

API_KEY = "sk-ca488baceb8843069f6c782043f1d54f"
API_URL = "https://api.deepseek.com/v1/chat/completions"


@app.route("/api")
def api():
    return jsonify({"status": 200, "data": "You are in api"})


@app.route("/api/regisration", methods=["POST"])
def registration():
    """
    registration function

    Returns:
        json: answer from server
    """
    if request.method == "POST":
        data = request.json()
        db_sess = db_session.create_session()
        other = db_sess.query(User).filter(
            User.name == data['username']).first()
        curr_id = db_sess.query(User).all()[-1].id + 1
        if other:
            return jsonify({"status": 500, "error": "Use other login", "success": False})

        user = User()
        user.username = data['username']
        user.password = data['password']
        user.phone_number = data['phone_number']
        user.native_lang = data['native_lang']
        user.russian_level = data['russian_level']
        db_sess.add(user)
        db_sess.commit()
        db_sess.close()

        return jsonify({"status": 200, 
                        "error": None, 
                        "success": True, 
                        "data": {"id": user.id, 
                                 "username": user.username, 
                                 "native_language": user.native_lang, 
                                 "phone_number": user.phone_number, 
                                 "russian_level": user.russian_level, 
                                 "registration_date": datetime().date()}
                        })

    else:
        return jsonify({"status": 500, "error": "Use the POST method", "success": False})


@app.route("/api/login", methods=['GET'])
def login():
    """
    login function

    Returns:
        json: answer from server
    """
    if request.method == 'GET':
        data = request.json()
        db_sess = db_session.create_session()
        if "username" in data:
            user = db_sess.query(User).filter(
                User.username == data['username']).first()
            if not user:
                answer = {"status": 500, "error": "Wrong username", "success": False}
            else:
                if data['password'] == user.password:
                    answer = {"status": 200, 
                              "data": {"id": user.id, 
                                 "username": user.username, 
                                 "native_language": user.native_lang, 
                                 "phone_number": user.phone_number, 
                                 "russian_level": user.russian_level, 
                                 },
                              "success": True,
                              "error": None
                              }
                else:
                    answer = {"status": 500, 'error': "wrong password", "success": False}
        elif 'phone_number' in data:
            user = db_sess.query(User).filter(
                User.phone_number == data['phone_number']).first()
            if not user:
                answer = {"status": 500, "error": "Wrong phone number", "success": False}
            else:
                if data['password'] == user.password:
                    answer = {"status": 200, 
                              "data": {"id": user.id, 
                                 "username": user.username, 
                                 "native_language": user.native_lang, 
                                 "phone_number": user.phone_number, 
                                 "russian_level": user.russian_level, 
                                 },
                              "success": True,
                              "error": None
                              }
                else:
                    answer = {"status": 500, 'error': "wrong password", "success": False}
        else:
            answer = {"status": 500,
                      "error": "Give the phone number or username in data",
                      "success": False}
    else:
        answer = {"status": 500, 'error': 'Use GET method', "success": False}
    db_sess.close()

    return jsonify(answer)


@app.route("/api/editdata/<id>", methods=["PATCH"])
def editData(id: int):
    """
    function for edit database

    Args:
        id (int): user id

    Returns:
        json: answer
    """
    if request.method == "PATCH":
        db_sess = db_session.create_session()
        data = request.json()
        user = db_sess.query(User).filter(User.id == id).first(
        ) if id else db_sess.query(User).filter(User.name == data['name'])

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
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    data = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 2048
    }
    response = requests.post(API_URL, json=data, headers=headers)

    if response.status_code == 200:
        result = response.json()
        return {"status": 200, "data": result['choices'][0]['message']['content']}
    else:
        return {"status": response.status_code, "reason": response.text}


app.run(debug=True)
