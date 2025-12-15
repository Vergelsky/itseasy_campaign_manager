"""
Клиент для работы с Keitaro API
"""
import requests
from typing import Dict, List, Any
from config.exceptions import KeitaroAPIException, KeitaroAuthException, KeitaroConnectionException


class KeitaroClient:
    """Клиент для работы с Keitaro API"""
    
    def __init__(self, base_url: str, api_key: str):
        """
        Инициализация клиента
        
        Args:
            base_url: URL Keitaro инстанса
            api_key: API ключ для аутентификации
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.api_base = f"{self.base_url}/admin_api/v1"
        self.headers = {
            'Api-Key': self.api_key,
            'Content-Type': 'application/json',
        }
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Any:
        """
        Выполнение HTTP запроса к API
        
        Args:
            method: HTTP метод (GET, POST, PUT, DELETE)
            endpoint: API endpoint (без /admin_api/v1)
            **kwargs: Дополнительные параметры для requests
        
        Returns:
            JSON ответ от API
        
        Raises:
            KeitaroAPIException: При ошибках API
        """
        url = f"{self.api_base}/{endpoint.lstrip('/')}"
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                timeout=30,
                **kwargs
            )
            
            # Обработка ошибок
            if response.status_code == 401:
                raise KeitaroAuthException('Неверный API ключ или доступ запрещён')
            elif response.status_code == 404:
                raise KeitaroAPIException(f'Ресурс не найден: {endpoint}')
            elif response.status_code >= 500:
                raise KeitaroConnectionException(f'Ошибка сервера Keitaro: {response.status_code}')
            elif response.status_code >= 400:
                raise KeitaroAPIException(f'Ошибка запроса: {response.status_code} - {response.text}')
            
            response.raise_for_status()
            
            # Некоторые endpoints возвращают пустой ответ
            if not response.content:
                return {}
            
            return response.json()
            
        except requests.exceptions.Timeout:
            raise KeitaroConnectionException('Превышено время ожидания ответа от Keitaro')
        except requests.exceptions.ConnectionError:
            raise KeitaroConnectionException('Не удалось подключиться к Keitaro')
        except requests.exceptions.RequestException as e:
            raise KeitaroConnectionException(f'Ошибка при запросе к Keitaro: {str(e)}')
    
    def get_campaigns(self, offset: int = 0, limit: int = 100) -> List[Dict]:
        """
        Получение списка кампаний
        
        Args:
            offset: Смещение для пагинации
            limit: Количество записей
        
        Returns:
            Список кампаний
        """
        params = {}
        if offset:
            params['offset'] = offset
        if limit:
            params['limit'] = limit
        
        return self._make_request('GET', 'campaigns', params=params)
    
    def get_campaign(self, campaign_id: int) -> Dict:
        """
        Получение деталей кампании
        
        Args:
            campaign_id: ID кампании в Keitaro
        
        Returns:
            Данные кампании
        """
        return self._make_request('GET', f'campaigns/{campaign_id}')
    
    def get_offer(self, offer_id: int) -> Dict:
        """
        Получение деталей оффера
        
        Args:
            offer_id: ID оффера в Keitaro
        
        Returns:
            Данные оффера
        """
        return self._make_request('GET', f'offers/{offer_id}')
    
    def get_streams(self, campaign_id: int) -> List[Dict]:
        """
        Получение потоков (streams) кампании
        
        Args:
            campaign_id: ID кампании в Keitaro
        
        Returns:
            Список потоков с офферами
        """
        return self._make_request('GET', f'campaigns/{campaign_id}/streams')
    
    def get_stream(self, stream_id: int) -> Dict:
        """
        Получение деталей потока
        
        Args:
            stream_id: ID потока в Keitaro
        
        Returns:
            Данные потока
        """
        return self._make_request('GET', f'streams/{stream_id}')
    
    def update_stream(self, stream_id: int, data: Dict) -> Dict:
        """
        Обновление потока (включая offers)
        
        Args:
            stream_id: ID потока в Keitaro
            data: Данные для обновления
        
        Returns:
            Обновлённые данные потока
        """
        return self._make_request('PUT', f'streams/{stream_id}', json=data)
    
    def create_campaign(self, name: str, alias: str = None) -> Dict:
        """
        Создание кампании в Keitaro
        
        Args:
            name: Название кампании
            alias: Алиас кампании (если не указан, генерируется из названия)
        
        Returns:
            Данные созданной кампании
        """
        if not alias:
            # Генерируем alias из названия (латиница, нижний регистр, без пробелов)
            alias = ''.join(c.lower() if c.isalnum() else '_' for c in name)[:50]
        
        data = {
            'name': name,
            'alias': alias,
            'state': 'active',
            'type': 'position'
        }
        
        return self._make_request('POST', 'campaigns', json=data)
    
    def create_stream(self, campaign_id: int, name: str, action_type: str, 
                     schema: str = 'redirect', stream_type: str = 'regular',
                     action_payload: str = '', action_options: Dict = None,
                     filters: List[Dict] = None, offers: List[Dict] = None,
                     position: int = 0) -> Dict:
        """
        Создание потока в Keitaro
        
        Args:
            campaign_id: ID кампании
            name: Название потока
            action_type: Тип действия ('http', 'campaign', и т.д.)
            schema: Схема потока ('redirect', 'landings')
            stream_type: Тип потока ('regular', 'forced', 'default')
            action_payload: Payload действия (обычно пустая строка для redirect)
            action_options: Опции действия (например, {"url": "https://google.com"})
            filters: Список фильтров (для гео-таргетинга и т.д.)
            offers: Список офферов (для schema='landings')
            position: Позиция потока
        
        Returns:
            Данные созданного потока
        """
        data = {
            'campaign_id': campaign_id,
            'name': name,
            'type': stream_type,
            'schema': schema,
            'action_type': action_type,
            'action_payload': action_payload,
            'state': 'active',
            'position': position,
            'collect_clicks': True,
            'filter_or': False
        }
        
        if action_options:
            data['action_options'] = action_options
        
        if filters:
            data['filters'] = filters
        
        if offers:
            data['offers'] = offers
        
        return self._make_request('POST', 'streams', json=data)
    
    def get_offers(self) -> List[Dict]:
        """
        Получение списка всех офферов
        
        Returns:
            Список офферов
        """
        return self._make_request('GET', 'offers')
    
    def get_report(self, params: Dict) -> Dict:
        """
        Построение отчёта (для статистики)
        
        Args:
            params: Параметры отчёта (columns, metrics, filters, range)
        
        Returns:
            Данные отчёта
        """
        return self._make_request('POST', 'report/build', json=params)
    
    def validate_api_key(self) -> bool:
        """
        Проверка валидности API ключа
        
        Returns:
            True если ключ валиден, False иначе
        
        Raises:
            KeitaroAuthException: Если API ключ неверный
            KeitaroConnectionException: Если сервис Keitaro недоступен
        """
        try:
            self.get_campaigns(limit=1)
            return True
        except KeitaroAuthException:
            # Неверный API ключ - возвращаем False
            return False
        except KeitaroConnectionException:
            # Проблемы с подключением - пробрасываем исключение дальше
            raise
        except KeitaroAPIException:
            # Другие ошибки API - пробрасываем как проблемы подключения
            raise KeitaroConnectionException('Не удалось проверить API ключ из-за ошибки сервиса')

