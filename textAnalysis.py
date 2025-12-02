import json
import requests

from config import TEXTOMETR_URL, METRICS

def get_textometr_analysis(text: str) -> dict:
    """Sends text and gets response from textometr"""

    json_data = json.dumps({"text": text})
    response = requests.request("POST", TEXTOMETR_URL, data=json_data)
    response_json = json.loads(response.text)
    return response_json
