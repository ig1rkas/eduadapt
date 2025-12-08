import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import re
import base64
import nltk

from typing import Dict, Any
from wordcloud import WordCloud
from io import BytesIO
from pymorphy3 import MorphAnalyzer
from nltk.corpus import stopwords



class WordCloudGenerator:
    def __init__(self, width: int = 800, height: int = 400,
                 background_color: str = 'white',
                 max_words: int = 200):
        self.width = width
        self.height = height
        self.background_color = background_color
        self.max_words = max_words
        self._download_nltk_resources()
        self.morph = MorphAnalyzer()

    def _download_nltk_resources(self):
        try:
            nltk.download('stopwords', quiet=True)
        except:
            print("Failed to download nltk resources")

    def preprocess_text(self, text: str) -> str:
        """Предобработка текста"""
        text = text.lower()

        text = re.sub(r'[^а-яёa-z\s]', ' ', text)

        text = re.sub(r'\s+', ' ', text).strip()

        words = text.split()

        if hasattr(self.morph, 'lemmatize'):
            lemmas = [self.morph.lemmatize(word)[0] for word in words if word.strip()]
        else:
            lemmas = [self.morph.parse(word)[0].normal_form for word in words if word.strip()]

        return ' '.join(lemmas)

    def remove_stopwords(self, text: str, custom_stopwords: list = None) -> str:
        """Удаление стоп-слов"""
        try:
            stopwords_en = set(stopwords.words('english'))
            stopwords_ru = set(stopwords.words('russian'))
        except LookupError:
            self._download_nltk_resources()
            stopwords_en = set(stopwords.words('english'))
            stopwords_ru = set(stopwords.words('russian'))
        additional_words = ['очень', 'которые', 'это', 'ещё', 'также', 'который', 'например']
        combined_stopwords = stopwords_en.union(stopwords_ru).union(additional_words)

        if custom_stopwords:
            combined_stopwords.update(custom_stopwords)

        words = text.split()
        filtered_words = [word for word in words if word not in combined_stopwords and len(word) > 2]

        return ' '.join(filtered_words)

    def generate_wordcloud(self, text: str) -> WordCloud:
        """Генерация облака слов"""
        processed_text = self.preprocess_text(text)
        processed_text = self.remove_stopwords(processed_text)

        wordcloud_params = {
            'width': self.width,
            'height': self.height,
            'background_color': self.background_color,
            'max_words': self.max_words,
            'colormap': 'viridis',
            'relative_scaling': 0.5,
            'random_state': 42
        }

        wordcloud = WordCloud(**wordcloud_params)
        wordcloud.generate(processed_text)

        return wordcloud

    def wordcloud_to_base64(self, wordcloud: WordCloud, format: str = 'png') -> str:
        """Конвертация облака слов в base64"""
        buffer = BytesIO()

        plt.figure(figsize=(self.width / 100, self.height / 100), dpi=100)
        fig = plt.figure(figsize=(self.width / 100, self.height / 100), dpi=100)
        plt.imshow(wordcloud, interpolation='bilinear')
        plt.axis('off')
        plt.tight_layout(pad=0)

        plt.savefig(buffer, format=format, bbox_inches='tight', pad_inches=0,
                    facecolor=self.background_color)
        plt.close(fig)
        plt.close('all')

        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        buffer.close()

        return f"data:image/{format};base64,{image_base64}"


def generate_word_cloud_api(text: str, width: int = 800, height: int = 400) -> Dict[str, Any]:
    try:
        try:
            if not text or not isinstance(text, str):
                raise ValueError("Текст должен быть непустой строкой")

            if len(text.strip()) < 10:
                raise ValueError("Текст слишком короткий (минимум 10 символов)")

            if len(text) > 100000:
                raise ValueError("Текст слишком длинный (максимум 100000 символов)")

            if width < 100 or height < 100:
                raise ValueError(f"Размер изображения слишком мал: минимальный размер 100x100 пикселей")

            if width > 4000 or height > 4000:
                raise ValueError(f"Размер изображения слишком велик: максимальный размер 4000x4000 пикселей")

            generator = WordCloudGenerator(width=width, height=height)
            wordcloud = generator.generate_wordcloud(text)
        except ValueError as e:
            raise RuntimeError(f"Ошибка генерации облака слов: {str(e)}")

        if not hasattr(wordcloud, 'words_') or not wordcloud.words_:
            raise RuntimeError("Не удалось сгенерировать облако слов: текст не содержит значимых слов после обработки")

        try:
            image_base64 = generator.wordcloud_to_base64(wordcloud)
        except Exception as e:
            raise RuntimeError(f"Ошибка конвертации изображения: {str(e)}")

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


    except ValueError as e:
        return {
            "success": False,
            "data": None,
            "error": {
                "type": "VALIDATION_ERROR",
                "message": str(e),
                "details": f"Некорректные входные параметры: {str(e)}"
            }
        }

    except RuntimeError as e:
        return {
            "success": False,
            "data": None,
            "error": {
                "type": "GENERATION_ERROR",
                "message": str(e),
                "details": f"Ошибка при создании облака слов: {str(e)}"
            }
        }

    except ImportError as e:
        return {
            "success": False,
            "data": None,
            "error": {
                "type": "DEPENDENCY_ERROR",
                "message": "Отсутствует необходимая библиотека",
                "details": f"Требуемые библиотеки: wordcloud, matplotlib. Ошибка: {str(e)}"
            }
        }

    except MemoryError as e:
        return {
            "success": False,
            "data": None,
            "error": {
                "type": "MEMORY_ERROR",
                "message": "Недостаточно памяти для обработки",
                "details": "Попробуйте уменьшить размер текста или изображения"
            }
        }


    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        return {
            "success": False,
            "data": None,
            "error": {
                "type": "UNEXPECTED_ERROR",
                "message": "Внутренняя ошибка сервера",
                "details": f"Неизвестная ошибка: {str(e)}",
                "traceback": error_trace[:500]
            }
        }