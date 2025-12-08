import json
from modules.deepseek_api import deepseek_api
import re

from modules.text_analysis import get_textometr_analysis


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
