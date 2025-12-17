"""Telethon client manager for dispatcher sessions."""
import os
import io
import asyncio
from typing import Optional, Dict, Tuple, Callable
from telethon import TelegramClient
from telethon.errors import FloodWaitError, SessionPasswordNeededError
from telethon.tl.types import User
from src.config import settings
import logging
import qrcode

logger = logging.getLogger(__name__)


class TelethonClientManager:
    """Менеджер для управления Telethon клиентами диспетчеров."""
    
    def __init__(self):
        self.clients: Dict[int, TelegramClient] = {}  # dispatcher_id -> client
        self._ensure_sessions_dir()
    
    def _ensure_sessions_dir(self):
        """Создание директории для сессий, если не существует."""
        os.makedirs(settings.SESSIONS_DIR, exist_ok=True)
    
    def get_session_path(self, dispatcher_id: int) -> str:
        """Получение пути к файлу сессии."""
        return os.path.join(settings.SESSIONS_DIR, f"dispatcher_{dispatcher_id}.session")
    
    async def create_client(self, dispatcher_id: int) -> TelegramClient:
        """
        Создание Telethon клиента для диспетчера.
        
        Args:
            dispatcher_id: Telegram ID диспетчера
            
        Returns:
            TelegramClient
        """
        session_path = self.get_session_path(dispatcher_id)
        
        client = TelegramClient(
            session_path,
            settings.API_ID,
            settings.API_HASH
        )
        
        self.clients[dispatcher_id] = client
        return client
    
    async def start_client(self, dispatcher_id: int) -> bool:
        """
        Запуск клиента (подключение к Telegram).
        
        Args:
            dispatcher_id: Telegram ID диспетчера
            
        Returns:
            True если успешно, False иначе
        """
        try:
            client = await self.get_client(dispatcher_id)
            if not client.is_connected():
                await client.connect()
            
            if not await client.is_user_authorized():
                return False
            
            return True
        except Exception as e:
            logger.error(f"Error starting client for dispatcher {dispatcher_id}: {e}")
            return False
    
    async def get_client(self, dispatcher_id: int) -> Optional[TelegramClient]:
        """
        Получение клиента диспетчера.
        
        Args:
            dispatcher_id: Telegram ID диспетчера
            
        Returns:
            TelegramClient или None
        """
        if dispatcher_id in self.clients:
            return self.clients[dispatcher_id]
        
        # Создание нового клиента
        return await self.create_client(dispatcher_id)
    
    async def send_message(
        self,
        dispatcher_id: int,
        chat_id: int,
        message: str
    ) -> Optional[int]:
        """
        Отправка сообщения от имени диспетчера.
        
        Args:
            dispatcher_id: Telegram ID диспетчера
            chat_id: ID чата (группы)
            message: Текст сообщения
            
        Returns:
            ID отправленного сообщения или None при ошибке
        """
        try:
            client = await self.get_client(dispatcher_id)
            
            if not client.is_connected():
                await client.connect()
            
            if not await client.is_user_authorized():
                logger.warning(f"Client {dispatcher_id} not authorized")
                return None
            
            sent_message = await client.send_message(chat_id, message)
            return sent_message.id
            
        except FloodWaitError as e:
            logger.warning(f"FloodWait for dispatcher {dispatcher_id}: {e.seconds} seconds")
            raise
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return None
    
    async def edit_message(
        self,
        dispatcher_id: int,
        chat_id: int,
        message_id: int,
        new_text: str
    ) -> bool:
        """
        Редактирование сообщения.
        
        Args:
            dispatcher_id: Telegram ID диспетчера
            chat_id: ID чата
            message_id: ID сообщения
            new_text: Новый текст
            
        Returns:
            True если успешно
        """
        try:
            client = await self.get_client(dispatcher_id)
            
            if not client.is_connected():
                await client.connect()
            
            await client.edit_message(chat_id, message_id, new_text)
            return True
            
        except Exception as e:
            logger.error(f"Error editing message: {e}")
            return False
    
    async def get_me(self, dispatcher_id: int) -> Optional[User]:
        """
        Получение информации о пользователе диспетчера.
        
        Args:
            dispatcher_id: Telegram ID диспетчера
            
        Returns:
            User объект или None
        """
        try:
            client = await self.get_client(dispatcher_id)
            
            if not client.is_connected():
                await client.connect()
            
            return await client.get_me()
        except Exception as e:
            logger.error(f"Error getting user info: {e}")
            return None
    
    async def disconnect(self, dispatcher_id: int):
        """Отключение клиента."""
        if dispatcher_id in self.clients:
            await self.clients[dispatcher_id].disconnect()
            del self.clients[dispatcher_id]
    
    async def get_chat_info(self, dispatcher_id: int, chat_id: int) -> Optional[Dict]:
        """
        Получение информации о чате/группе.
        
        Args:
            dispatcher_id: Telegram ID диспетчера
            chat_id: ID чата/группы
            
        Returns:
            Dict с информацией о чате или None
        """
        try:
            client = await self.get_client(dispatcher_id)
            
            if not client.is_connected():
                await client.connect()
            
            if not await client.is_user_authorized():
                return None
            
            entity = await client.get_entity(chat_id)
            
            return {
                'id': entity.id,
                'title': getattr(entity, 'title', None) or f"Chat {entity.id}",
                'username': getattr(entity, 'username', None),
                'is_group': hasattr(entity, 'megagroup') or hasattr(entity, 'broadcast'),
                'is_channel': getattr(entity, 'broadcast', False),
                'is_supergroup': getattr(entity, 'megagroup', False)
            }
        except Exception as e:
            logger.error(f"Error getting chat info: {e}")
            return None
    
    async def get_user_groups(self, dispatcher_id: int) -> list[Dict]:
        """
        Получение списка всех групп пользователя.
        
        Args:
            dispatcher_id: Telegram ID диспетчера
            
        Returns:
            List[Dict] со списком групп
        """
        try:
            client = await self.get_client(dispatcher_id)
            
            if not client.is_connected():
                await client.connect()
            
            if not await client.is_user_authorized():
                return []
            
            groups = []
            async for dialog in client.iter_dialogs():
                # Фильтруем только группы и супергруппы (не каналы и не личные чаты)
                if dialog.is_group or (hasattr(dialog.entity, 'megagroup') and dialog.entity.megagroup):
                    groups.append({
                        'id': dialog.id,
                        'title': dialog.name,
                        'username': getattr(dialog.entity, 'username', None),
                        'is_group': True,
                        'member_count': getattr(dialog.entity, 'participants_count', 0)
                    })
            
            return groups
        except Exception as e:
            logger.error(f"Error getting user groups: {e}")
            return []
    
    async def start_qr_login(self, dispatcher_id: int) -> Optional[Tuple[object, bytes]]:
        """
        Начало авторизации через QR-код.
        
        Args:
            dispatcher_id: Telegram ID диспетчера
            
        Returns:
            Tuple (qr_login_object, qr_image_bytes) или None при ошибке
        """
        try:
            client = await self.get_client(dispatcher_id)
            
            # Подключаемся, если не подключены
            if not client.is_connected():
                await client.connect()
            
            # Проверяем, не авторизован ли уже
            if await client.is_user_authorized():
                logger.info(f"Client {dispatcher_id} already authorized")
                return None
            
            # Получаем QR-код для авторизации
            qr_login = await client.qr_login()
            
            # Генерируем QR-код как изображение из URL
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(qr_login.url)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Конвертируем в bytes
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='PNG')
            img_bytes.seek(0)
            
            return (qr_login, img_bytes.getvalue())
            
        except Exception as e:
            logger.error(f"Error starting QR login for dispatcher {dispatcher_id}: {e}")
            return None
    
    async def check_qr_login_status(self, dispatcher_id: int) -> Tuple[bool, Optional[str]]:
        """
        Проверка статуса QR-авторизации.
        
        Args:
            dispatcher_id: Telegram ID диспетчера
            
        Returns:
            Tuple (is_authorized, error_message)
        """
        try:
            client = await self.get_client(dispatcher_id)
            
            if not client.is_connected():
                await client.connect()
            
            is_authorized = await client.is_user_authorized()
            return (is_authorized, None)
            
        except SessionPasswordNeededError:
            return (False, "Требуется пароль двухфакторной аутентификации")
        except Exception as e:
            logger.error(f"Error checking QR login status for dispatcher {dispatcher_id}: {e}")
            return (False, str(e))
    
    async def finish_qr_login(self, dispatcher_id: int, password: Optional[str] = None) -> bool:
        """
        Завершение авторизации (если требуется пароль 2FA).
        
        Args:
            dispatcher_id: Telegram ID диспетчера
            password: Пароль 2FA (если требуется)
            
        Returns:
            True если успешно
        """
        try:
            client = await self.get_client(dispatcher_id)
            
            if not client.is_connected():
                await client.connect()
            
            if await client.is_user_authorized():
                return True
            
            # Если требуется пароль
            if password:
                await client.sign_in(password=password)
                return await client.is_user_authorized()
            
            return False
            
        except Exception as e:
            logger.error(f"Error finishing QR login for dispatcher {dispatcher_id}: {e}")
            return False


# Глобальный экземпляр менеджера
client_manager = TelethonClientManager()

