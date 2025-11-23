import matplotlib.pyplot as plt
import re
import base64

from typing import Dict, Any
from wordcloud import WordCloud
from io import BytesIO


class WordCloudGenerator:
    def __init__(self, width: int = 800, height: int = 400,
                 background_color: str = 'white',
                 max_words: int = 200):
        self.width = width
        self.height = height
        self.background_color = background_color
        self.max_words = max_words

    def preprocess_text(self, text: str) -> str:
        """Предобработка текста"""
        # Приведение к нижнему регистру
        text = text.lower()

        # Удаление специальных символов, оставляем только буквы и пробелы
        text = re.sub(r'[^а-яёa-z\s]', ' ', text)

        # Удаление лишних пробелов
        text = re.sub(r'\s+', ' ', text).strip()

        return text

    def remove_stopwords(self, text: str, custom_stopwords: list = None) -> str:
        """Удаление стоп-слов"""
        # Базовые русские стоп-слова
        russian_stopwords = {
            'и', 'в', 'во', 'не', 'что', 'он', 'на', 'я', 'с', 'со', 'как', 'а',
            'то', 'все', 'она', 'так', 'его', 'но', 'да', 'ты', 'к', 'у', 'же',
            'вы', 'за', 'бы', 'по', 'только', 'ее', 'мне', 'было', 'вот', 'от',
            'меня', 'еще', 'нет', 'о', 'из', 'ему', 'теперь', 'когда', 'даже',
            'ну', 'вдруг', 'ли', 'если', 'уже', 'или', 'ни', 'быть', 'был',
            'него', 'до', 'вас', 'нибудь', 'опять', 'уж', 'вам', 'ведь', 'там',
            'потом', 'себя', 'ничего', 'ей', 'может', 'они', 'тут', 'где', 'есть',
            'надо', 'ней', 'для', 'мы', 'тебя', 'их', 'чем', 'была', 'сам', 'чтоб',
            'без', 'будто', 'чего', 'раз', 'тоже', 'себе', 'под', 'будет', 'ж',
            'тогда', 'кто', 'этот', 'того', 'потому', 'этого', 'какой', 'совсем',
            'ним', 'здесь', 'этом', 'один', 'почти', 'мой', 'тем', 'чтобы', 'нее',
            'сейчас', 'были', 'куда', 'зачем', 'всех', 'никогда', 'можно', 'при',
            'наконец', 'два', 'об', 'другой', 'хоть', 'после', 'над', 'больше',
            'тот', 'через', 'эти', 'нас', 'про', 'всего', 'них', 'какая', 'много',
            'разве', 'три', 'эту', 'моя', 'впрочем', 'хорошо', 'свою', 'этой',
            'перед', 'иногда', 'лучше', 'чуть', 'том', 'нельзя', 'такой', 'им',
            'более', 'всегда', 'конечно', 'всю', 'между'
        }

        if custom_stopwords:
            russian_stopwords.update(custom_stopwords)

        words = text.split()
        filtered_words = [word for word in words if word not in russian_stopwords and len(word) > 2]

        return ' '.join(filtered_words)

    def generate_wordcloud(self, text: str) -> WordCloud:
        """Генерация облака слов"""
        # Предобработка текста
        processed_text = self.preprocess_text(text)
        processed_text = self.remove_stopwords(processed_text)

        # Настройки для WordCloud
        wordcloud_params = {
            'width': self.width,
            'height': self.height,
            'background_color': self.background_color,
            'max_words': self.max_words,
            'colormap': 'viridis',
            'relative_scaling': 0.5,
            'random_state': 42
        }

        # Создание облака слов
        wordcloud = WordCloud(**wordcloud_params)
        wordcloud.generate(processed_text)

        return wordcloud

    def wordcloud_to_base64(self, wordcloud: WordCloud, format: str = 'png') -> str:
        """Конвертация облака слов в base64"""
        # Создание изображения в памяти
        buffer = BytesIO()

        # Сохранение в буфер
        plt.figure(figsize=(self.width / 100, self.height / 100), dpi=100)
        plt.imshow(wordcloud, interpolation='bilinear')
        plt.axis('off')
        plt.tight_layout(pad=0)

        plt.savefig(buffer, format=format, bbox_inches='tight', pad_inches=0,
                    facecolor=self.background_color)
        plt.close()

        # Конвертация в base64
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

        return f"data:image/{format};base64,{image_base64}"


def generate_word_cloud_api(text: str, width: int = 800, height: int = 400) -> Dict[str, Any]:
    try:
        # Инициализация генератора
        generator = WordCloudGenerator(width=width, height=height)

        # Генерация облака слов
        wordcloud = generator.generate_wordcloud(text)

        # Конвертация в base64
        image_base64 = generator.wordcloud_to_base64(wordcloud)

        # Формирование ответа согласно спецификации
        response = {
            "success": True,
            "data": {
                "image_base64": image_base64,
                "image_format": "png",
                "width": width,
                "height": height
            },
            "error": None
        }

        return response

    except Exception as e:
        # Обработка ошибок
        return {
            "success": False,
            "data": None,
            "error": str(e)
        }