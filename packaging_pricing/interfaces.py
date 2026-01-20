from abc import ABC, abstractmethod
from typing import Any
from .context import PipelineContext
from .models import BagType

class ScrapRateProvider(ABC):
    """
    Интерфейс для определения процента отхода (брака).
    """
    
    @abstractmethod
    def get_scrap_rate(self, quantity: int, bag_type: BagType) -> float:
        """
        Возвращает норму отхода в виде десятичной дроби (например, 0.15 для 15%).
        """
        pass

class CalculationStep(ABC):
    """
    Интерфейс для одного шага в конвейере расчета цены (Pipeline).
    """

    @abstractmethod
    def execute(self, context: PipelineContext) -> None:
        """
        Выполнить расчет и обновить контекст.
        Бросает ValueError, если отсутствуют необходимые данные.
        """
        pass
