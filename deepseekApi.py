import requests

from config import DEEPSEEK_API_KEY, DEEPSEEK_API_URL


def deepseekApi(user_prompt: str, system_prompt="You are helpful assistant") -> requests:
    """
    function to get a response from deepseek

    Args:
        user_prompt (str): user prompt content
        system_prompt (str): settings for deepseek

    Returns:
        requests: response from AI
    """
    global DEEPSEEK_API_KEY
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {DEEPSEEK_API_KEY}"}
    data = {
        "model": "deepseek-chat",
        "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        "temperature": 0.7,
        # "max_tokens": 2048,
    }
    response = requests.post(DEEPSEEK_API_URL, json=data, headers=headers)

    if response.status_code == 200:
        result = response.json()
        return {"status": 200, "data": result["choices"][0]["message"]["content"]}
    else:
        return {"status": response.status_code, "reason": response.text}