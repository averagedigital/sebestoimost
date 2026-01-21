"""
Тестовые расчёты с параметрами от экономиста и специалиста ОП.
"""
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

# ============================================================
# Параметры от экономиста
# ============================================================
config = PricingConfig(
    density=0.91,  # г/см3
    material_price_bopp=186.0,  # руб/кг
    material_price_cpp=186.0,   # руб/кг
    k1_salary_coeff=3.6,
    box_cost=23.20,  # руб/шт
    scrap_return_price=10.0,  # руб/кг
    k2_margin_divisor=2.3,
    k3_margin_multiplier=1.7,
    rop_overhead=6.0,  # руб/кг РОП
    feature_rates={
        "glue": 0.003,          # Клеевой слой руб/см
        "dead_glue": 0.0207,    # Клеевой слой мёртвый руб/см
        "euroslot_pvd": 0.0137, # Еврослот пвд руб/см
        "euroslot_bopp": 0.0012, # Еврослот бопп руб/см
        "clips": 0.8            # Клипсы руб/шт
    },
    electricity_rate=0.0095,
    salary_std_small=0.04,
    salary_std_large=0.053,
    salary_wicket_small=0.075,
    salary_wicket_large=0.078
)

# Создаём пайплайн
scrap_provider = TableBasedScrapProvider()
steps = [
    GeometryCalculationStep(),
    ScrapCalculationStep(provider=scrap_provider),
    LaborCostStep(),
    MaterialCostStep(),
    PricingStep()
]
pipeline = PricingPipeline(steps=steps, config=config)


def print_result(result, label: str):
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    print(f"  Вес (г):                    {result.weight_grams:.4f}")
    print(f"  Брак (%):                   {result.scrap_rate_percent:.1f}%")
    print(f"  Стоимость материала:        {result.material_cost:.4f} руб")
    print(f"  Стоимость брака (возврат):  {result.scrap_cost:.4f} руб")
    print(f"  Стоимость труда:            {result.labor_cost:.4f} руб")
    print(f"  Накладные расходы:          {result.overhead_cost:.4f} руб")
    print(f"  Стоимость опций:            {result.options_cost:.4f} руб")
    print(f"  -" * 30)
    print(f"  Переменная себестоимость (VC): {result.variable_cost:.4f} руб")
    print(f"  ИТОГО ЦЕНА:                 {result.final_price:.4f} руб")
    print(f"{'='*60}")
    
    print("\n  ДЕТАЛИ:")
    for key, value in result.details.items():
        print(f"    {key}: {value:.6f}")
    print()


# ============================================================
# ТЕСТ 1: Пакет BOPP
# ============================================================
print("\n" + "#"*60)
print("# ТЕСТ 1: Пакет BOPP")
print("#"*60)
print("""
Параметры от специалиста ОП:
- Схема печати: без печати
- Вид продукции: Пакет BOPP
- ширина: 10 см
- фальц: 0 см
- длина (в том числе дно): 25 см
- клапан: 3 см
- толщина: 25 мкм
- клапан клеевой: да
- клапан клеевой мёртвый: нет
- еврослот: нет
- викет пакет: нет (клипсы 0)
- тираж: 30000 шт
""")

order_bopp = OrderInput(
    product_type=BagType.BOPP,
    width=10,
    fold=0,
    length=25,
    flap=3,
    thickness=25,
    quantity=30000,
    print_scheme="б/печати",
    features=Features(
        glue_tape=True,      # клапан клеевой: да
        dead_tape=False,     # клапан клеевой мёртвый: нет
        euroslot=None,       # еврослот: нет
        is_wicket=False,     # викет пакет: нет
        clips=False          # клипсы: 0
    )
)

result_bopp = pipeline.calculate(order_bopp)
print_result(result_bopp, "Пакет BOPP 10x25+3, 25мкм, тираж 30000")


# ============================================================
# ТЕСТ 2: Пакет CPP
# ============================================================
print("\n" + "#"*60)
print("# ТЕСТ 2: Пакет CPP")
print("#"*60)
print("""
Параметры от специалиста ОП:
- Схема печати: без печати
- Вид продукции: Пакет CPP
- ширина: 20 см
- фальц: 0 см
- длина (в том числе дно): 30 см
- клапан: 4 см
- толщина: 25 мкм
- клапан клеевой: нет
- клапан клеевой мёртвый: нет
- еврослот: нет
- викет пакет: да
- тираж: 30000 шт
""")

order_cpp = OrderInput(
    product_type=BagType.CPP,
    width=20,
    fold=0,
    length=30,
    flap=4,
    thickness=25,
    quantity=30000,
    print_scheme="б/печати",
    features=Features(
        glue_tape=False,     # клапан клеевой: нет
        dead_tape=False,     # клапан клеевой мёртвый: нет
        euroslot=None,       # еврослот: нет
        is_wicket=True,      # викет пакет: да
        clips=False          # клипсы автоматически включаются для викет-пакета
    )
)

result_cpp = pipeline.calculate(order_cpp)
print_result(result_cpp, "Пакет CPP 20x30+4, 25мкм, викет, тираж 30000")


# ============================================================
# Также прогоним pytest тесты
# ============================================================
print("\n" + "#"*60)
print("# Прогон pytest тестов")
print("#"*60)
import subprocess
result = subprocess.run(
    ["python", "-m", "pytest", "tests/test_formulas.py", "-v", "--tb=short"],
    capture_output=True,
    text=True,
    cwd="/Users/average/Desktop/рассчетсебестоимости"
)
print(result.stdout)
if result.stderr:
    print("STDERR:", result.stderr)
