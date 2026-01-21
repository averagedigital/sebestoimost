"""
Тестовый скрипт для проверки расчёта с реальными параметрами экономиста
"""
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

config = PricingConfig(
    density=0.91,
    material_price_bopp=186.0,
    material_price_cpp=186.0,
    k1_salary_coeff=3.6,
    box_cost=23.20,
    scrap_return_price=10.0,
    k2_margin_divisor=2.3,
    k3_margin_multiplier=1.7,
    rop_overhead=6.0,
    feature_rates={
        "glue": 0.003,
        "dead_glue": 0.0207,
        "euroslot_pvd": 0.0137,
        "euroslot_bopp": 0.0012,
        "clips": 0.8
    },
    electricity_rate=0.0095,
    salary_std_small=0.04,
    salary_std_large=0.053,
    salary_wicket_small=0.075,
    salary_wicket_large=0.078
)

# Сборка pipeline
scrap_provider = TableBasedScrapProvider()
steps = [
    GeometryCalculationStep(),
    ScrapCalculationStep(provider=scrap_provider),
    LaborCostStep(),
    MaterialCostStep(),
    PricingStep()
]
pipeline = PricingPipeline(steps=steps, config=config)

print("=" * 60)
print("ТЕСТ 1: Пакет BOPP с клеевым клапаном")
print("=" * 60)

order1 = OrderInput(
    product_type=BagType.BOPP,
    width=10.0,
    length=25.0,
    fold=0.0,
    flap=3.0,
    thickness=25.0,
    quantity=30000,
    print_scheme="б/печати",
    features=Features(
        is_wicket=False,
        glue_tape=True,
        dead_tape=False,
        euroslot=None,
        clips=False
    )
)

result1 = pipeline.calculate(order1)
print(f"""
Входные данные:
  - Ширина: {order1.width} см
  - Длина: {order1.length} см
  - Клапан: {order1.flap} см
  - Толщина: {order1.thickness} мкм
  - Тираж: {order1.quantity} шт
  - Клеевой клапан: Да
  - Викет: Нет

Результаты расчёта:
  - Вес пакета: {result1.weight_grams:.4f} г
  - Процент брака: {result1.scrap_rate_percent}%
  - Стоимость материала: {result1.material_cost:.4f} руб
  - Стоимость отходов: {result1.scrap_cost:.4f} руб
  - Затраты на труд: {result1.labor_cost:.4f} руб
  - Накладные (ROP): {result1.overhead_cost:.4f} руб
  - Опции (клей): {result1.options_cost:.4f} руб
  - Электроэнергия: {result1.details.get('electricity', 0):.4f} руб
  - Коробка: {result1.details.get('box_component', 0):.4f} руб
  
  → Переменная себестоимость (VC): {result1.variable_cost:.4f} руб
  → ИТОГО ЦЕНА: {result1.final_price:.4f} руб
""")

print("=" * 60)
print("ТЕСТ 2: Пакет CPP Викет")
print("=" * 60)

order2 = OrderInput(
    product_type=BagType.CPP,
    width=20.0,
    length=30.0,
    fold=0.0,
    flap=4.0,
    thickness=25.0,
    quantity=30000,
    print_scheme="б/печати",
    features=Features(
        is_wicket=True,
        glue_tape=False,
        dead_tape=False,
        euroslot=None
        # Клипсы добавляются автоматически для викета в steps.py
    )
)

result2 = pipeline.calculate(order2)
print(f"""
Входные данные:
  - Ширина: {order2.width} см
  - Длина: {order2.length} см
  - Клапан: {order2.flap} см
  - Толщина: {order2.thickness} мкм
  - Тираж: {order2.quantity} шт
  - Клеевой клапан: Нет
  - Викет: Да

Результаты расчёта:
  - Вес пакета: {result2.weight_grams:.4f} г
  - Процент брака: {result2.scrap_rate_percent}%
  - Стоимость материала: {result2.material_cost:.4f} руб
  - Стоимость отходов: {result2.scrap_cost:.4f} руб
  - Затраты на труд: {result2.labor_cost:.4f} руб
  - Накладные (ROP): {result2.overhead_cost:.4f} руб
  - Опции: {result2.options_cost:.4f} руб
  - Электроэнергия: {result2.details.get('electricity', 0):.4f} руб
  - Коробка: {result2.details.get('box_component', 0):.4f} руб
  
  → Переменная себестоимость (VC): {result2.variable_cost:.4f} руб
  → ИТОГО ЦЕНА: {result2.final_price:.4f} руб
""")

# Проверка формул вручную для теста 1
print("=" * 60)
print("РУЧНАЯ ПРОВЕРКА ФОРМУЛ (Тест 1)")
print("=" * 60)

w, l, fl, th, dens = 10, 25, 3, 25, 0.91
weight_manual = ((w + 0) * (l + fl/2) * th * 2 * dens) / 10000
print(f"Вес = (({w}+0)*({l}+{fl}/2)*{th}*2*{dens})/10000 = {weight_manual:.4f} г")

price_kg = 186
mat_cost = (weight_manual * price_kg) / 1000
print(f"Материал = {weight_manual:.4f} * {price_kg} / 1000 = {mat_cost:.4f} руб")

scrap_rate = 0.15  # 30000 = 15%
scrap_return = 10
scrap_cost = (weight_manual / 1000) * scrap_rate * (price_kg - scrap_return)
print(f"Отходы = ({weight_manual:.4f}/1000) * {scrap_rate} * ({price_kg}-{scrap_return}) = {scrap_cost:.4f} руб")

elec = 0.0095
salary = 0.04  # width <= 25, не викет
k1 = 3.6
labor = salary * k1
print(f"Труд = {salary} * {k1} = {labor:.4f} руб")

box = 23.20 / 2000
print(f"Коробка = 23.20 / 2000 = {box:.4f} руб")

glue_rate = 0.003
options = glue_rate * w
print(f"Опции (клей) = {glue_rate} * {w} = {options:.4f} руб")

vc = mat_cost + scrap_cost + elec + labor + box + options
print(f"VC = {mat_cost:.4f} + {scrap_cost:.4f} + {elec} + {labor:.4f} + {box:.4f} + {options:.4f} = {vc:.4f} руб")

k2, k3, rop = 2.3, 1.7, 6
base = (vc / k2) + vc
price = base * k3 + (rop * weight_manual / 1000)
print(f"Цена = (({vc:.4f}/{k2}) + {vc:.4f}) * {k3} + ({rop}*{weight_manual:.4f}/1000) = {price:.4f} руб")
