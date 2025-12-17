"""Speech recognition service using various APIs."""
import io
import aiohttp
import logging
from typing import Optional
from src.config import settings

logger = logging.getLogger(__name__)


class SpeechRecognitionService:
    """Сервис для распознавания речи из голосовых сообщений."""
    
    @staticmethod
    async def recognize_voice_openai(voice_file: bytes, language: str = "ru") -> Optional[str]:
        """
        Распознавание речи через OpenAI Whisper API.
        
        Args:
            voice_file: Байты аудиофайла
            language: Язык распознавания (ru, en, etc.)
            
        Returns:
            Распознанный текст или None при ошибке
        """
        if not hasattr(settings, 'OPENAI_API_KEY') or not settings.OPENAI_API_KEY:
            logger.warning("OpenAI API key not configured")
            return None
        
        try:
            url = "https://api.openai.com/v1/audio/transcriptions"
            headers = {
                "Authorization": f"Bearer {settings.OPENAI_API_KEY}"
            }
            
            data = aiohttp.FormData()
            # Передаем bytes напрямую, оборачивая в BytesIO для FormData
            data.add_field('file', 
                          io.BytesIO(voice_file) if isinstance(voice_file, bytes) else voice_file,
                          filename='voice.ogg',
                          content_type='audio/ogg')
            data.add_field('model', 'whisper-1')
            data.add_field('language', language)
            
            logger.info(f"Sending voice file to OpenAI, size: {len(voice_file)} bytes")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, data=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get('text', '')
                    else:
                        error_text = await response.text()
                        logger.error(f"OpenAI API error: {response.status} - {error_text}")
                        return None
        except Exception as e:
            logger.error(f"Error recognizing speech with OpenAI: {e}")
            return None
    
    @staticmethod
    async def recognize_voice_yandex(voice_file: bytes, language: str = "ru-RU") -> Optional[str]:
        """
        Распознавание речи через Yandex SpeechKit.
        
        Args:
            voice_file: Байты аудиофайла
            language: Язык распознавания (ru-RU, en-US, etc.)
            
        Returns:
            Распознанный текст или None при ошибке
        """
        if not hasattr(settings, 'YANDEX_API_KEY') or not settings.YANDEX_API_KEY:
            logger.warning("Yandex API key not configured")
            return None
        
        try:
            # Сначала получаем IAM токен (если используется API ключ)
            # Или используем готовый IAM токен
            iam_token = getattr(settings, 'YANDEX_IAM_TOKEN', None)
            if not iam_token and hasattr(settings, 'YANDEX_API_KEY'):
                # Можно получить IAM токен из API ключа, но проще использовать готовый
                iam_token = settings.YANDEX_API_KEY
            
            url = "https://stt.api.cloud.yandex.net/speech/v1/stt:recognize"
            headers = {
                "Authorization": f"Api-Key {iam_token}"
            }
            
            params = {
                "lang": language,
                "format": "oggopus",
                "sampleRateHertz": 48000
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, params=params, data=voice_file) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get('result', '')
                    else:
                        error_text = await response.text()
                        logger.error(f"Yandex API error: {response.status} - {error_text}")
                        return None
        except Exception as e:
            logger.error(f"Error recognizing speech with Yandex: {e}")
            return None
    
    @staticmethod
    async def recognize_voice(voice_file: bytes, language: str = "ru") -> Optional[str]:
        """
        Универсальный метод распознавания речи.
        Пробует использовать доступные API по приоритету.
        
        Args:
            voice_file: Байты аудиофайла
            language: Язык распознавания
            
        Returns:
            Распознанный текст или None
        """
        # Приоритет: OpenAI > Yandex
        providers = getattr(settings, 'SPEECH_PROVIDER', 'openai').lower()
        
        if providers == 'openai' or (providers == 'auto' and hasattr(settings, 'OPENAI_API_KEY') and settings.OPENAI_API_KEY):
            result = await SpeechRecognitionService.recognize_voice_openai(voice_file, language)
            if result:
                return result
        
        if providers == 'yandex' or (providers == 'auto' and hasattr(settings, 'YANDEX_API_KEY') and settings.YANDEX_API_KEY):
            result = await SpeechRecognitionService.recognize_voice_yandex(voice_file, language)
            if result:
                return result
        
        logger.warning("No speech recognition provider available")
        return None

