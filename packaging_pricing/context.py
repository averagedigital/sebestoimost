from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from .models import OrderInput, PricingConfig, CalculationResult

@dataclass
class PipelineContext:
    """
    Контекст пайплайна. Хранит состояние во время выполнения расчетов.
    Содержит входные данные, конфиг и промежуточные результаты.
    """
    input_data: OrderInput
    config: PricingConfig
    
    # Аккумулятор промежуточных результатов.
    # Ключи могут быть: 'weight', 'scrap_rate', 'salary_base' и т.д.
    intermediates: Dict[str, Any] = field(default_factory=dict)

    final_result: Optional[CalculationResult] = None

    def get_intermediate(self, key: str) -> Any:
        """Получить значение промежуточного результата по ключу."""
        if key not in self.intermediates:
            raise KeyError(f"Зависимость шага не найдена: {key}")
        return self.intermediates[key]

    def set_intermediate(self, key: str, value: Any) -> None:
        """Сохранить промежуточный результат."""
        self.intermediates[key] = value
