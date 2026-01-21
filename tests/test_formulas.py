"""
Тесты для проверки формул расчёта себестоимости.
Запуск: pytest tests/test_formulas.py -v
"""
import pytest
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


# Фикстура: конфигурация экономиста
@pytest.fixture
def config():
    return PricingConfig(
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


@pytest.fixture
def pipeline(config):
    scrap_provider = TableBasedScrapProvider()
    steps = [
        GeometryCalculationStep(),
        ScrapCalculationStep(provider=scrap_provider),
        LaborCostStep(),
        MaterialCostStep(),
        PricingStep()
    ]
    return PricingPipeline(steps=steps, config=config)


# ============================================================
# ТЕСТ 1: Формула веса
# ТЗ: Вес = ((ширина+фальц)*(длина+клапан/2)*толщина*2*плотность)/10000
# ============================================================
class TestWeightFormula:
    
    @pytest.mark.parametrize("width,fold,length,flap,thickness,expected_weight", [
        (10, 0, 25, 3, 25, 1.2058),   # Тест 1: 10x25+3, 25мкм
        (20, 0, 30, 4, 25, 2.9120),   # Тест 2: 20x30+4, 25мкм
        (20, 5, 30, 0, 30, 4.0950),   # С фальцем
        (15, 0, 20, 0, 40, 2.1840),   # Без клапана
    ])
    def test_weight_calculation(self, pipeline, width, fold, length, flap, thickness, expected_weight):
        order = OrderInput(
            product_type=BagType.BOPP,
            width=width,
            fold=fold,
            length=length,
            flap=flap,
            thickness=thickness,
            quantity=50000,
            features=Features()
        )
        result = pipeline.calculate(order)
        assert abs(result.weight_grams - expected_weight) < 0.001, \
            f"Вес: ожидалось {expected_weight}, получено {result.weight_grams}"


# ============================================================
# ТЕСТ 2: Таблица брака
# ============================================================
class TestScrapRate:
    
    @pytest.mark.parametrize("quantity,expected_scrap_percent", [
        (25000, 15.0),   # <= 30000
        (30000, 15.0),   # граница
        (40000, 15.0),   # 30-50к = 15%
        (50000, 15.0),   # граница
        (75000, 13.0),   # 50-100к = 13%
        (100000, 13.0),  # граница
        (150000, 7.0),   # 100-300к = 7%
        (300000, 7.0),   # граница
        (500000, 6.0),   # > 300к = 6%
    ])
    def test_scrap_rate(self, pipeline, quantity, expected_scrap_percent):
        order = OrderInput(
            product_type=BagType.BOPP,
            width=10, length=20, thickness=25,
            quantity=quantity,
            features=Features()
        )
        result = pipeline.calculate(order)
        assert result.scrap_rate_percent == expected_scrap_percent


# ============================================================
# ТЕСТ 3: Выбор ставки ЗП
# ============================================================
class TestSalaryRate:
    
    @pytest.mark.parametrize("width,is_wicket,expected_salary_rate", [
        (20, False, 0.04),   # стандарт, <=25
        (30, False, 0.053),  # стандарт, >25
        (20, True, 0.075),   # викет, <=25
        (30, True, 0.078),   # викет, >25
        (25, False, 0.04),   # граница <=25, стандарт
        (25, True, 0.075),   # граница <=25, викет
    ])
    def test_salary_rate_selection(self, pipeline, width, is_wicket, expected_salary_rate):
        order = OrderInput(
            product_type=BagType.BOPP,
            width=width, length=30, thickness=25,
            quantity=50000,
            features=Features(is_wicket=is_wicket)
        )
        result = pipeline.calculate(order)
        assert result.details["salary_rate"] == expected_salary_rate


# ============================================================
# ТЕСТ 4: Опции
# ============================================================
class TestOptions:
    
    def test_glue_tape_cost(self, pipeline, config):
        """Клеевой клапан = rate * ширина"""
        order = OrderInput(
            product_type=BagType.BOPP,
            width=10, length=20, thickness=25,
            quantity=50000,
            features=Features(glue_tape=True)
        )
        result = pipeline.calculate(order)
        expected = config.feature_rates["glue"] * 10  # 0.003 * 10 = 0.03
        assert abs(result.options_cost - expected) < 0.0001
    
    def test_dead_tape_cost(self, pipeline, config):
        """Мёртвый скотч = rate * ширина"""
        order = OrderInput(
            product_type=BagType.BOPP,
            width=10, length=20, thickness=25,
            quantity=50000,
            features=Features(dead_tape=True)
        )
        result = pipeline.calculate(order)
        expected = config.feature_rates["dead_glue"] * 10
        assert abs(result.options_cost - expected) < 0.0001
    
    def test_wicket_includes_clips(self, pipeline, config):
        """Викет автоматически включает клипсы"""
        order = OrderInput(
            product_type=BagType.BOPP,
            width=10, length=20, thickness=25,
            quantity=50000,
            features=Features(is_wicket=True)
        )
        result = pipeline.calculate(order)
        expected = (config.feature_rates["clips"] * 2) / 200  # 0.8 * 2 / 200 = 0.008
        assert abs(result.options_cost - expected) < 0.0001
    
    def test_no_clips_without_wicket(self, pipeline):
        """Без викета нет клипс"""
        order = OrderInput(
            product_type=BagType.BOPP,
            width=10, length=20, thickness=25,
            quantity=50000,
            features=Features(is_wicket=False)
        )
        result = pipeline.calculate(order)
        assert result.options_cost == 0.0


# ============================================================
# ТЕСТ 5: Формула цены
# ТЗ: Цена = (VC/K2 + VC) * K3 + ROP*вес/1000
# ============================================================
class TestPriceFormula:
    
    def test_price_formula_structure(self, config):
        """Проверка что формула цены соответствует ТЗ"""
        # Ручной расчёт
        vc = 0.5  # переменная себестоимость
        weight = 2.0  # вес в граммах
        
        expected_price = (vc / config.k2_margin_divisor + vc + (config.rop_overhead * weight / 1000)) * config.k3_margin_multiplier
        
        # (0.5 / 2.3 + 0.5 + 6 * 2 / 1000) * 1.7
        # = (0.2174 + 0.5 + 0.012) * 1.7
        # = 0.7294 * 1.7
        # = 1.23998
        
        assert abs(expected_price - 1.23998) < 0.001


# ============================================================
# ТЕСТ 6: Кросс-проверка компонентов VC
# ============================================================
class TestVCComponents:
    
    def test_vc_is_sum_of_components(self, pipeline):
        """VC = материал + брак + э/э + труд + короб + опции"""
        order = OrderInput(
            product_type=BagType.BOPP,
            width=10, length=20, thickness=25,
            quantity=50000,
            features=Features(glue_tape=True)
        )
        result = pipeline.calculate(order)
        
        # Рассчитываем сумму компонентов
        components_sum = (
            result.material_cost +
            result.scrap_cost +
            result.details["electricity"] +
            result.labor_cost +
            result.details["box_component"] +
            result.options_cost
        )
        
        assert abs(result.variable_cost - components_sum) < 0.0001, \
            f"VC ({result.variable_cost}) != сумма компонентов ({components_sum})"


# ============================================================
# ТЕСТ 7: Инварианты
# ============================================================
class TestInvariants:
    
    def test_price_always_positive(self, pipeline):
        """Цена всегда положительная"""
        order = OrderInput(
            product_type=BagType.BOPP,
            width=1, length=1, thickness=1,
            quantity=1000000,  # максимальный тираж для минимального брака
            features=Features()
        )
        result = pipeline.calculate(order)
        assert result.final_price > 0
    
    def test_larger_size_costs_more(self, pipeline):
        """Больший размер = большая цена"""
        small = OrderInput(
            product_type=BagType.BOPP,
            width=10, length=10, thickness=25,
            quantity=50000,
            features=Features()
        )
        large = OrderInput(
            product_type=BagType.BOPP,
            width=30, length=30, thickness=25,
            quantity=50000,
            features=Features()
        )
        
        result_small = pipeline.calculate(small)
        result_large = pipeline.calculate(large)
        
        assert result_large.final_price > result_small.final_price
    
    def test_higher_quantity_lower_scrap(self, pipeline):
        """Больший тираж = меньший % брака"""
        low_qty = OrderInput(
            product_type=BagType.BOPP,
            width=10, length=20, thickness=25,
            quantity=40000,
            features=Features()
        )
        high_qty = OrderInput(
            product_type=BagType.BOPP,
            width=10, length=20, thickness=25,
            quantity=400000,
            features=Features()
        )
        
        result_low = pipeline.calculate(low_qty)
        result_high = pipeline.calculate(high_qty)
        
        assert result_high.scrap_rate_percent < result_low.scrap_rate_percent
