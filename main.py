import json
from packaging_pricing.models import OrderInput, PricingConfig, BagType, Features
from packaging_pricing.pipeline import PricingPipeline
from packaging_pricing.scraps import TableBasedScrapProvider
from packaging_pricing.steps import (
    GeometryCalculationStep,
    ScrapCalculationStep,
    LaborCostStep,
    MaterialCostStep,
    PricingStep
)

def run_demo():
    # 1. Настройка конфигурации (Роль "Экономист")
    config = PricingConfig(
        material_price_per_kg=200.0,
        box_cost=50.0,
        feature_rates={
            "glue": 0.5,           # руб/см
            "dead_glue": 0.3,      # руб/см
            "euroslot_pvd": 1.5,   # руб/см
            "euroslot_bopp": 1.2,  # руб/см
            "clips": 2.0           # руб/шт
        }
    )

    # 2. Сборка пайплайна (Роль "Архитектор")
    # Здесь мы внедряем конкретный провайдер расчета отходов.
    scrap_provider = TableBasedScrapProvider()
    
    steps = [
        GeometryCalculationStep(),
        ScrapCalculationStep(provider=scrap_provider),
        LaborCostStep(),
        MaterialCostStep(),
        PricingStep()
    ]
    
    pipeline = PricingPipeline(steps=steps, config=config)

    # 3. Входные данные (Роль "Менеджер")
    
    # Сценарий A: Стандартный маленький пакет BOPP
    # 20x30, 30мкм, 40к тираж (должен сработать порог 15% брака)
    order_a = OrderInput(
        product_type=BagType.BOPP,
        width=20.0,
        length=30.0,
        thickness=30.0,
        quantity=40000,
        features=Features()
    )

    # Сценарий B: Большой Викет-пакет с клеем
    # 30x50, 40мкм, 150к тираж (должен сработать порог 7% брака)
    order_b = OrderInput(
        product_type=BagType.CPP,
        width=30.0, # > 25см -> повышенная ставка ЗП
        length=50.0,
        thickness=40.0,
        quantity=150000,
        features=Features(
            is_wicket=True,
            glue_tape=True
        )
    )

    print("--- Сценарий A: Стандартный пакет BOPP ---")
    result_a = pipeline.calculate(order_a)
    print(json.dumps(result_a.model_dump(), indent=2, ensure_ascii=False))

    print("\n--- Сценарий B: Большой Викет-пакет CPP с клеем ---")
    result_b = pipeline.calculate(order_b)
    print(json.dumps(result_b.model_dump(), indent=2, ensure_ascii=False))

if __name__ == "__main__":
    run_demo()
