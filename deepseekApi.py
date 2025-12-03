import json
import re

import requests

from config import DEEPSEEK_API_KEY, DEEPSEEK_API_URL

from textAnalysis import get_textometr_analysis


def deepseek_api(user_prompt: str, system_prompt="You are helpful assistant") -> requests:
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
        "temperature": 0.7
        # "max_tokens": 2048,
    }
    response = requests.post(DEEPSEEK_API_URL, json=data, headers=headers)

    if response.status_code == 200:
        result = response.json()
        return {"status": 200, "data": result["choices"][0]["message"]["content"]}
    else:
        return {"status": response.status_code, "reason": response.text}


def adapt_educational_text(original_text: str, target_level: str = "B2", native_language: str = "en") :
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
            "Используй только простые союзы: и, а, но, или, потому что, чтобы",
            "один абзац = одна мысль, четкая последовательность: сначала → потом → затем"
        ],
        "B2": [
            "Используй простые и сложносочиненные предложения",
            "Допустимы предложения с союзами, например, поскольку, однако, в то время как",
            "Ограниченно используй причастные обороты (1-2 на абзац)",
            "Сохраняй причинно-следственные связи между предложениями",
            "Абзац содержит не больше 3 связанных мыслей"
        ]
    }

    level_rules = adaptation_rules.get(target_level, adaptation_rules["B2"])

    base_prompt = {
        "role": "Ты - помощник для адаптации учебных текстов для иностранных студентов. ",
        "task": [
            "Выделить важные профессиональные термины для обучения",
            "Вернуть такой же исходный текст, заменяя все выделенные термины на '…'",
            "Упрощай текст на целевой уровень сложности. Вернуть адаптированный текст, сохраняя выделенные термины",
            "Вернуть такой же адаптированный текст, заменяя все выделенные термины на '…'",
            "Твой ответ должен быть валидным JSON, который можно парсить сразу с помощью json.loads()"
        ],
        "level_of_original_text": "Выше C2",
        "target_level": target_level,
        "adaptation_rules": {
            f"for_{target_level}": level_rules
        },
        "output_format": {
            "professional_terms": [
                {
                    "term": "термин в тексте в первоначальной форме, включая аббревиатуры",
                    "translation": f"перевод на родной язык студентов - {native_language}",
                    "definition": "объяснение в стиле целевого уровня на русском языке",
                    "definition_native": f"объяснение в стиле целевого уровня на родном языке студентов - {native_language}",
                    "examples": ["пример 1 на русском языке", "пример 2 на русском языке"]
                }
            ],
            "original_text_without_terms": "исходный текст без терминов",
            "adapted_text": "адаптированный текст с терминами. СОХРАНИТЕ ТЕРМИНЫ!",
            "adapted_text_without_terms": "адаптированный текст без терминов",
            "key_sentences": [
                "выделить несколько (не все) ключевые предложения из адаптированного текста С ТЕРМИНАМИ (adapted_text). НЕ ПЕРЕФОРМУЛИРУЙТЕ ИХ!"]
        },
        "original_text": original_text
    }

    in_level_key = f"in{target_level}"
    prompt_text = json.dumps(base_prompt, ensure_ascii=False, indent=2)
    response = deepseek_api(prompt_text, "You are an educational text adaptation expert")

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
        analysis_without_terms = get_textometr_analysis(adapted_data['adapted_text_without_terms'])

        if analysis_with_terms and analysis_without_terms:
            return {
                "success": True,
                "data": {
                    "target_level": target_level,
                    "adapted_text": adapted_data['adapted_text'],
                    "key_elements": {
                        "key_sentences": adapted_data.get('key_sentences', []),
                        "professional_terms": adapted_data.get('professional_terms', [])
                    },
                    "statistics": {
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
                            "in_level": f"{analysis_with_terms.get(in_level_key, 0)}%",
                            "not_in_level": analysis_with_terms.get(f'not_in{target_level}', [])
                        },
                        "text_without_terms": {
                            "level_metrics": {
                                "level_number": analysis_without_terms.get('level_number', 0),
                                "level_comment": analysis_without_terms.get('level_comment', '')
                            }
                        }
                    }
                },
                "error": None
            }
        else:
            return {
                "success": False,
                "data": {
                    "target_level": target_level,
                    "adapted_text": adapted_data['adapted_text'],
                    "key_elements": {
                        "key_sentences": adapted_data.get('key_sentences', []),
                        "professional_terms": adapted_data.get('professional_terms', [])
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
