import json
import time
import requests

try:
    import config

    DEEPSEEK_API_KEY = config.DEEPSEEK_API_KEY
    DEEPSEEK_API_URL = config.DEEPSEEK_API_URL
except ImportError:
    raise ImportError(
        "Configuration file 'config.py' not found. Please ensure it exists and contains DEEPSEEK_API_KEY.")
except AttributeError:
    raise AttributeError("DEEPSEEK_API_KEY not defined in the config file.")

if not DEEPSEEK_API_KEY:
    raise ValueError("DEEPSEEK_API_KEY is empty. Please check your config file.")


def deepseek_api(messages: list, initial_timeout=240) -> dict:
    """
    Функция для получения ответа от DeepSeek с использованием механизма (Retry).
    """
    data = {
        "model": "deepseek-chat",
        "messages": messages,
        "max_tokens": 8000,
        "temperature": 0.7,
        "stream": True
    }

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }

    start_time = time.time()

    try:
        response = requests.post(
            DEEPSEEK_API_URL,
            json=data,
            headers=headers,
            timeout=120,
            stream=True
        )

        print(f"[DEBUG] RESPONSE STATE: {response.status_code}")

        if response.status_code != 200:
            error_text = response.text[:200] if hasattr(response, 'text') else "NO ERROR"
            return {"status": response.status_code, "reason": error_text}

        # Collect all content
        full_response = ""
        received_chunks = 0

        for line in response.iter_lines(decode_unicode=True):
            if line:
                # pass keep-alive
                if line.startswith(': '):
                    continue

                if line.startswith('data: '):
                    data_content = line[6:]  # delete "data: "

                    if data_content == '[DONE]':
                        print(f"[DEBUG] STREAM STOP，RECEIVED {received_chunks} CHUNKS")
                        break

                    try:
                        chunk_data = json.loads(data_content)
                        received_chunks += 1

                        if 'choices' in chunk_data and chunk_data['choices']:
                            delta = chunk_data['choices'][0].get('delta', {})
                            content = delta.get('content', '')
                            full_response += content
                    except json.JSONDecodeError:
                        print(f"[WARN] cannot parse chunk: {data_content[:100]}")
                        continue

        elapsed = time.time() - start_time
        print(f"[INFO] Stream request finished: {elapsed:.1f}sec., {len(full_response)} characters")

        if full_response:
            return {"status": 200, "data": full_response}
        else:
            return {"status": 500, "reason": "Empty response"}

    except requests.exceptions.Timeout:
        elapsed = time.time() - start_time
        print(f"[ERROR] Timeout: {elapsed:.1f}sec.")
        return {"status": "TIMEOUT", "reason": f"Timeout ({elapsed:.0f}sec.)"}
    except Exception as e:
        print(f"[ERROR] Request failed: {str(e)}")
        return {"status": "ERROR", "reason": str(e)}
