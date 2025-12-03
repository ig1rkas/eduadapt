import json
import re
import time

import requests

from config import DEEPSEEK_API_URL
from textAnalysis import get_textometr_analysis

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

def get_adaptation_system_prompt(native_language: str) -> str:
    """
    Создает системный Prompt, определяющий роль и строгий формат вывода JSON.
    """

    return f"""
Ты - помощник для адаптации учебных текстов для иностранных студентов. 
Твоя задача - выделить важные профессиональные термины для обучения, упрощай текст на целевой уровень сложности. 

Формат ответа (строго JSON):
{{
    "professional_terms": [
        {{
            "term": "термин в тексте в первоначальной форме, включая аббревиатуры",
            "translation": "перевод на {native_language}",
            "definition": "объяснение на русском",
            "examples": ["пример 1 на русском", "пример 2 на русском"]
        }}
    ],
    "adapted_text": "адаптированный текст с терминами.",
    "key_sentences": [
        "выделить несколько ключевые предложения из adapted_text. Каждое предложение в key_sentences ДОЛЖНО существовать
         в adapted_text. Совпадение должно быть 100% точным (регистр, пробелы, пунктуация)"
    ]
}}
"""


def adapt_educational_text(original_text: str, target_level: str = "B2", native_language: str = "en"):
    """
    Функция для адаптации учебных текстов с проверкой уровня сложности

    Args:
        original_text (str): Исходный текст для адаптации
        target_level (str): Целевой уровень сложности (B1, B2)
        native_language (str): Родной язык пользователя ("en", "zh", "ko" и т.д.)

    Returns:
        dict: Результат адаптации в формате JSON
    """

    adaptation_rules = {
        "B1": [
            "Используй только короткие и простые предложения",
            "Заменяй пассивные конструкции на активные",
            "Преобразуй причастные обороты в отдельные предложения",
            "один абзац = одна мысль, четкая последовательность"
        ],
        "B2": [
            "Используй простые и сложносочиненные предложения",
            "Допустимы предложения с союзами",
            "Ограниченно используй причастные обороты",
            "Абзац содержит не больше 3 связанных мыслей"
        ]
    }

    level_rules = adaptation_rules.get(target_level, adaptation_rules["B2"])

    user_prompt = f"""
        Адаптируй текст до уровня сложности: {target_level}.
        Правила: {level_rules}.
        Когда получишь текст, верни результат в указанном JSON формате.
        Текст для адаптации:\n\n{original_text}
    """

    system_prompt = get_adaptation_system_prompt(native_language)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    response = deepseek_api(messages)

    if response['status'] != 200:
        return {
            "success": False,
            "data": None,
            "error": f"DeepSeek API error: {response.get('reason', 'Unknown error')}"
        }

    try:
        response['data'] = re.sub(r'^```json\s*|\s*```$', '', response['data'], flags=re.MULTILINE)
        adapted_data = json.loads(response['data'])

        if 'adapted_text' not in adapted_data:
            return {
                "success": False,
                "data": None,
                "error": "Invalid response format: missing adapted_text"
            }

        analysis_with_terms = get_textometr_analysis(adapted_data['adapted_text'])

        if analysis_with_terms:
            return {
                "success": True,
                "data": {
                    "adapted_text": adapted_data['adapted_text'],
                    "key_elements": {
                        "key_sentences": adapted_data.get('key_sentences', []),
                        "professional_terms": adapted_data.get('professional_terms', [])
                    },
                    "statistics": {
                        "target_level": target_level,
                        "text_with_terms": {
                            "level_metrics": {
                                "level_number": analysis_with_terms.get('level_number', 0),
                                "level_comment": analysis_with_terms.get('level_comment', '')
                            },
                            "keywords": analysis_with_terms.get('key_words', []),
                            "basic_metrics": {
                                "word_count": analysis_with_terms.get('words', 0),
                                "sentence_count": analysis_with_terms.get('sentences', 0),
                                "reading_for_detail_speed": analysis_with_terms.get('reading_for_detail_speed', ''),
                                "skim_reading_speed": analysis_with_terms.get('skim_reading_speed', '')
                            },
                            "in_level": f"{analysis_with_terms.get(f'in{target_level}', 0)}%",
                            "not_in_level": analysis_with_terms.get(f'not_in{target_level}', [])
                        }
                    }
                },
                "error": None
            }
        else:
            return {
                "success": False,
                "data": {
                    "adapted_text": adapted_data['adapted_text'],
                    "key_elements": {
                        "key_sentences": adapted_data.get('key_sentences', []),
                        "professional_terms": adapted_data.get('professional_terms', [])
                    },
                    "statistics": {
                        "target_level": target_level
                    }
                },
                "error": "Fail to fetch text statistics"
            }

    except json.JSONDecodeError:
        return {
            "success": False,
            "data": None,
            "error": "Invalid JSON response from DeepSeek"
        }
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "error": f"Unexpected error: {str(e)}"
        }
