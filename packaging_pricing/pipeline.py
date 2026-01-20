from typing import List
from .interfaces import CalculationStep
from .models import OrderInput, PricingConfig, CalculationResult
from .context import PipelineContext

class PricingPipeline:
    """
    Основной класс-оркестратор. Выполняет последовательность шагов расчета.
    """
    def __init__(self, steps: List[CalculationStep], config: PricingConfig):
        self.steps = steps
        self.config = config

    def calculate(self, order: OrderInput) -> CalculationResult:
        context = PipelineContext(
            input_data=order,
            config=self.config
        )

        for step in self.steps:
            step.execute(context)

        if context.final_result is None:
            raise RuntimeError("Пайплайн завершен, но финальный результат не сформирован (final_result is None).")

        return context.final_result
