"""
Services Layer - Бизнес-логика приложения

Разделение ответственности:
- distribution.py: Распределение работы по операторам
- collection_service.py: Управление процессом взыскания
- workflow_service.py: Автоматизация бизнес-процессов (Rules Engine)
"""

from .distribution import DistributionService
from .collection_service import CollectionService
from .workflow_service import WorkflowEngine, RulesBuilder

__all__ = [
    'DistributionService',
    'CollectionService', 
    'WorkflowEngine',
    'RulesBuilder',
]