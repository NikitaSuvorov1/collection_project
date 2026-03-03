"""
Security Middleware - Защита API

Включает:
- Rate Limiting
- Audit Logging
- Request Validation
- Security Headers
"""

import time
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Callable, Dict, Optional
from functools import wraps

from django.http import JsonResponse, HttpRequest
from django.core.cache import cache
from django.conf import settings
from rest_framework import status

from ..models import AuditLog

logger = logging.getLogger(__name__)


class RateLimitMiddleware:
    """
    Rate Limiting Middleware.
    
    Ограничивает количество запросов с одного IP.
    Использует sliding window algorithm.
    """
    
    # Лимиты по умолчанию (requests per window)
    DEFAULT_RATE_LIMITS = {
        'default': (100, 60),      # 100 requests per minute
        'auth': (10, 60),          # 10 auth attempts per minute
        'api_write': (30, 60),     # 30 writes per minute
        'export': (5, 300),        # 5 exports per 5 minutes
    }
    
    # Эндпоинты с особыми лимитами
    ENDPOINT_LIMITS = {
        '/api/auth/': 'auth',
        '/api/token/': 'auth',
        '/api/export/': 'export',
    }
    
    def __init__(self, get_response: Callable):
        self.get_response = get_response
    
    def __call__(self, request: HttpRequest):
        client_ip = self._get_client_ip(request)
        endpoint_type = self._get_endpoint_type(request.path)
        
        if not self._check_rate_limit(client_ip, endpoint_type):
            return JsonResponse(
                {'error': 'Rate limit exceeded. Please try again later.'},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )
        
        response = self.get_response(request)
        return response
    
    def _get_client_ip(self, request: HttpRequest) -> str:
        """Получение IP клиента с учётом прокси"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown')
    
    def _get_endpoint_type(self, path: str) -> str:
        """Определение типа эндпоинта для лимитов"""
        for prefix, limit_type in self.ENDPOINT_LIMITS.items():
            if path.startswith(prefix):
                return limit_type
        
        # Write operations
        if any(method in path for method in ['create', 'update', 'delete']):
            return 'api_write'
        
        return 'default'
    
    def _check_rate_limit(self, client_ip: str, endpoint_type: str) -> bool:
        """
        Проверка rate limit с использованием sliding window.
        
        Returns:
            bool: True если запрос разрешён
        """
        max_requests, window_seconds = self.DEFAULT_RATE_LIMITS.get(
            endpoint_type, self.DEFAULT_RATE_LIMITS['default']
        )
        
        cache_key = f"rate_limit:{client_ip}:{endpoint_type}"
        
        # Получаем текущий счётчик
        current = cache.get(cache_key, {'count': 0, 'reset_at': time.time() + window_seconds})
        
        # Проверяем, не истёк ли window
        if time.time() > current['reset_at']:
            current = {'count': 0, 'reset_at': time.time() + window_seconds}
        
        # Проверяем лимит
        if current['count'] >= max_requests:
            logger.warning(f"Rate limit exceeded for IP {client_ip} on {endpoint_type}")
            return False
        
        # Увеличиваем счётчик
        current['count'] += 1
        cache.set(cache_key, current, window_seconds)
        
        return True


class AuditMiddleware:
    """
    Audit Logging Middleware.
    
    Логирует все действия пользователей для compliance.
    """
    
    # Эндпоинты, требующие аудита
    AUDIT_PATHS = [
        '/api/clients/',
        '/api/credits/',
        '/api/collection-cases/',
        '/api/interventions/',
        '/api/payments/',
        '/api/legal/',
        '/api/restructuring/',
    ]
    
    # Методы, требующие аудита
    AUDIT_METHODS = ['POST', 'PUT', 'PATCH', 'DELETE']
    
    # Чувствительные поля (персональные данные)
    SENSITIVE_FIELDS = [
        'passport', 'inn', 'snils', 'phone', 'email', 'address',
        'birth_date', 'income', 'employer'
    ]
    
    def __init__(self, get_response: Callable):
        self.get_response = get_response
    
    def __call__(self, request: HttpRequest):
        # Сохраняем начальное время
        start_time = time.time()
        
        # Определяем, нужен ли аудит
        should_audit = self._should_audit(request)
        
        # Сохраняем информацию для аудита до выполнения запроса
        if should_audit:
            audit_data = self._prepare_audit_data(request)
        
        # Выполняем запрос
        response = self.get_response(request)
        
        # Логируем после выполнения
        if should_audit:
            self._log_audit(request, response, audit_data, time.time() - start_time)
        
        return response
    
    def _should_audit(self, request: HttpRequest) -> bool:
        """Проверка необходимости аудита"""
        # Всегда логируем изменяющие методы на чувствительных эндпоинтах
        if request.method in self.AUDIT_METHODS:
            for path in self.AUDIT_PATHS:
                if request.path.startswith(path):
                    return True
        
        # Логируем просмотр персональных данных
        if request.method == 'GET' and '/clients/' in request.path:
            return True
        
        return False
    
    def _prepare_audit_data(self, request: HttpRequest) -> Dict:
        """Подготовка данных для аудита"""
        return {
            'path': request.path,
            'method': request.method,
            'ip_address': self._get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', '')[:500],
            'timestamp': datetime.now().isoformat(),
        }
    
    def _log_audit(self, request: HttpRequest, response, audit_data: Dict, 
                   duration: float) -> None:
        """Запись в журнал аудита"""
        try:
            # Определяем действие
            action_map = {
                'POST': 'create',
                'PUT': 'update',
                'PATCH': 'update',
                'DELETE': 'delete',
                'GET': 'read',
            }
            action = action_map.get(request.method, 'read')
            
            # Определяем модель
            model_name = self._extract_model_name(request.path)
            
            # Извлекаем ID объекта из URL
            object_id = self._extract_object_id(request.path)
            
            # Проверяем доступ к персональным данным
            personal_data_accessed = self._check_personal_data_access(request)
            
            # Создаём запись аудита
            AuditLog.objects.create(
                user=request.user if request.user.is_authenticated else None,
                action=action,
                model_name=model_name,
                object_id=object_id,
                ip_address=audit_data['ip_address'],
                user_agent=audit_data['user_agent'],
                personal_data_accessed=personal_data_accessed,
                changes={
                    'status_code': response.status_code,
                    'duration_ms': round(duration * 1000, 2),
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to create audit log: {e}")
    
    def _get_client_ip(self, request: HttpRequest) -> str:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')
    
    def _extract_model_name(self, path: str) -> str:
        """Извлечение имени модели из пути"""
        parts = path.strip('/').split('/')
        if len(parts) >= 2 and parts[0] == 'api':
            return parts[1].replace('-', '_')
        return 'unknown'
    
    def _extract_object_id(self, path: str) -> Optional[int]:
        """Извлечение ID объекта из пути"""
        parts = path.strip('/').split('/')
        for part in parts:
            if part.isdigit():
                return int(part)
        return None
    
    def _check_personal_data_access(self, request: HttpRequest) -> bool:
        """Проверка доступа к персональным данным"""
        # Проверяем путь
        if '/clients/' in request.path:
            return True
        
        # Проверяем query parameters
        for field in self.SENSITIVE_FIELDS:
            if field in request.GET or field in getattr(request, 'data', {}):
                return True
        
        return False


class SecurityHeadersMiddleware:
    """
    Security Headers Middleware.
    
    Добавляет заголовки безопасности к ответам.
    """
    
    def __init__(self, get_response: Callable):
        self.get_response = get_response
    
    def __call__(self, request: HttpRequest):
        response = self.get_response(request)
        
        # Защита от clickjacking
        response['X-Frame-Options'] = 'DENY'
        
        # XSS защита
        response['X-XSS-Protection'] = '1; mode=block'
        
        # Запрет MIME-type sniffing
        response['X-Content-Type-Options'] = 'nosniff'
        
        # Referrer policy
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Content Security Policy (для production)
        if not settings.DEBUG:
            response['Content-Security-Policy'] = (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data:; "
                "font-src 'self'; "
                "connect-src 'self'"
            )
        
        # Strict Transport Security (для HTTPS)
        if request.is_secure():
            response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        return response


class RequestValidationMiddleware:
    """
    Request Validation Middleware.
    
    Валидация и санитизация входящих запросов.
    """
    
    # Максимальный размер запроса (10 MB)
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024
    
    # Запрещённые паттерны (SQL injection, XSS)
    FORBIDDEN_PATTERNS = [
        '<script',
        'javascript:',
        'SELECT * FROM',
        'DROP TABLE',
        'UNION SELECT',
        '--',
        '; DELETE',
    ]
    
    def __init__(self, get_response: Callable):
        self.get_response = get_response
    
    def __call__(self, request: HttpRequest):
        # Проверка размера запроса
        content_length = request.META.get('CONTENT_LENGTH', 0)
        if content_length and int(content_length) > self.MAX_CONTENT_LENGTH:
            return JsonResponse(
                {'error': 'Request too large'},
                status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
            )
        
        # Проверка на вредоносные паттерны
        if self._contains_forbidden_patterns(request):
            logger.warning(f"Potential attack detected from {request.META.get('REMOTE_ADDR')}")
            return JsonResponse(
                {'error': 'Invalid request'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return self.get_response(request)
    
    def _contains_forbidden_patterns(self, request: HttpRequest) -> bool:
        """Проверка на вредоносные паттерны"""
        # Проверяем query string
        query_string = request.META.get('QUERY_STRING', '').upper()
        for pattern in self.FORBIDDEN_PATTERNS:
            if pattern.upper() in query_string:
                return True
        
        # Проверяем тело запроса (для POST/PUT)
        if request.method in ['POST', 'PUT', 'PATCH']:
            try:
                body = request.body.decode('utf-8', errors='ignore').upper()
                for pattern in self.FORBIDDEN_PATTERNS:
                    if pattern.upper() in body:
                        return True
            except:
                pass
        
        return False


# Декоратор для функциональных view
def rate_limit(limit: int, window: int):
    """
    Декоратор rate limiting для view.
    
    Args:
        limit: Максимум запросов
        window: Окно времени в секундах
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                client_ip = x_forwarded_for.split(',')[0].strip()
            else:
                client_ip = request.META.get('REMOTE_ADDR', 'unknown')
            
            cache_key = f"rl:{view_func.__name__}:{client_ip}"
            
            current = cache.get(cache_key, 0)
            if current >= limit:
                return JsonResponse(
                    {'error': 'Rate limit exceeded'},
                    status=429
                )
            
            cache.set(cache_key, current + 1, window)
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def audit_action(action: str, model: str):
    """
    Декоратор для аудита конкретного действия.
    
    Args:
        action: Тип действия
        model: Название модели
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            response = view_func(request, *args, **kwargs)
            
            # Логируем действие
            try:
                AuditLog.objects.create(
                    user=request.user if request.user.is_authenticated else None,
                    action=action,
                    model_name=model,
                    object_id=kwargs.get('pk'),
                    ip_address=request.META.get('REMOTE_ADDR', ''),
                )
            except Exception as e:
                logger.error(f"Audit log failed: {e}")
            
            return response
        return wrapper
    return decorator
