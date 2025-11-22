import json
import requests

from config import TEXTOMETR_URL, METRICS



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
