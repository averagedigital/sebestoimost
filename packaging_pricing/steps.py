from .interfaces import CalculationStep, ScrapRateProvider
from .context import PipelineContext
from .models import BagType, CalculationResult

class GeometryCalculationStep(CalculationStep):
    """
    Формула A: Вес пакета (в граммах)
    weight = ((width + fold) * (length + flap / 2) * thickness * 2 * density) / 10000
    """
    def execute(self, context: PipelineContext) -> None:
        i = context.input_data
        c = context.config
        
        # Расчет веса.
        # density в г/см3 (строго 0.91 по ТЗ)
        # размеры в см, толщина в микронах.
        # Делитель 10000 используется согласно формуле ТЗ для приведения размерностей.
        # Множитель 2 учитывает двойной слой пленки (рукав/полурукав -> пакет).
        
        weight = ((i.width + i.fold) * (i.length + i.flap / 2) * i.thickness * 2 * c.density) / 10000
        context.set_intermediate('weight', weight)


class ScrapCalculationStep(CalculationStep):
    """
    Формула B: Процент отхода (брак).
    Использует внедренный провайдер (таблица или ML).
    """
    def __init__(self, provider: ScrapRateProvider):
        self.provider = provider

    def execute(self, context: PipelineContext) -> None:
        rate = self.provider.get_scrap_rate(context.input_data.quantity, context.input_data.product_type)
        context.set_intermediate('scrap_rate', rate)


class LaborCostStep(CalculationStep):
    """
    Формула C: Затраты на труд и электроэнергию.
    Выбор тарифа в зависимости от типа пакета (стандарт/викет) и ширины.
    """
    def execute(self, context: PipelineContext) -> None:
        i = context.input_data
        c = context.config

        # Электроэнергия (константа)
        electricity = c.electricity_rate

        # Расчет зарплатной ставки
        width = i.width
        is_wicket = i.features.is_wicket

        salary_rate = 0.0
        
        if is_wicket:
            if width <= 25:
                salary_rate = c.salary_wicket_small
            else:
                salary_rate = c.salary_wicket_large
        else:
            # Стандартный пакет
            if width <= 25:
                salary_rate = c.salary_std_small
            else:
                salary_rate = c.salary_std_large

        context.set_intermediate('electricity', electricity)
        context.set_intermediate('salary_rate', salary_rate)


class MaterialCostStep(CalculationStep):
    """
    Формула D: Переменные затраты (Variable Cost - VC).
    VC включает: сырье, отходы, электроэнергию, ЗП, коробки и опции (клей, клипсы и т.д.).
    """
    def execute(self, context: PipelineContext) -> None:
        # Получаем промежуточные данные
        weight = context.get_intermediate('weight')
        scrap_rate = context.get_intermediate('scrap_rate')
        electricity = context.get_intermediate('electricity')
        salary_rate = context.get_intermediate('salary_rate')

        c = context.config
        i = context.input_data

        # 1. Базовая стоимость материала
        # Выбираем цену в зависимости от типа пленки
        price_per_kg = c.material_price_bopp if i.product_type == BagType.BOPP else c.material_price_cpp
        
        # weight в граммах, цена за кг.
        material_base_cost = (weight * price_per_kg) / 1000.0

        # 2. Стоимость отходов (Scrap Cost)
        # Формула: (вес / 1000 * %отхода * (цена_сырья - цена_возврата_вторсырья))
        scrap_cost = (weight / 1000.0) * scrap_rate * (price_per_kg - c.scrap_return_price)

        # 3. Расходы на зарплату (ставка * коэффициент K1)
        labor_cost = salary_rate * c.k1_salary_coeff

        # 4. Стоимость коробки (упаковки)
        # Согласно обновленному требованию: box_cost / 2000. В коробке 2000 шт.
        box_unit_cost = c.box_cost / 2000.0

        # 5. Стоимость опций (glue, clips, euroslot)
        # feature_rates содержит цену за см (для клея/слота) или за штуку (клипсы).
        options_cost = 0.0
        
        if i.features.glue_tape:
            options_cost += c.feature_rates["glue"] * i.width
        
        if i.features.dead_tape:
            options_cost += c.feature_rates["dead_glue"] * i.width

        if i.features.euroslot:
            if i.features.euroslot.lower() == "pvd":
                options_cost += c.feature_rates["euroslot_pvd"] * i.width
            elif i.features.euroslot.lower() == "bopp":
                options_cost += c.feature_rates["euroslot_bopp"] * i.width
        
        if i.features.is_wicket:
            # ТЗ: Клипсы * 2 / 200 (автоматически для викет-пакетов)
            options_cost += (c.feature_rates["clips"] * 2) / 200.0

        # Итого Variable Cost
        vc = material_base_cost + scrap_cost + electricity + labor_cost + box_unit_cost + options_cost

        context.set_intermediate('variable_cost', vc)
        context.set_intermediate('material_base_cost', material_base_cost)
        context.set_intermediate('scrap_cost', scrap_cost)
        context.set_intermediate('labor_cost', labor_cost)
        context.set_intermediate('options_cost', options_cost)


class PricingStep(CalculationStep):
    """
    Формула E: Финальная цена (Final Price).
    Price = ((VC / k2) + VC) * k3 + (rop * weight / 1000)
    """
    def execute(self, context: PipelineContext) -> None:
        vc = context.get_intermediate('variable_cost')
        weight = context.get_intermediate('weight')
        c = context.config

        # Расчет маржинальности
        # 1. Базовая цена с учетом делителя K2.
        # ТЗ: (VC / k2) + VC.
        base_price = (vc / c.k2_margin_divisor) + vc
        
        # 2. Применение множителя K3
        base_price_adjusted = base_price * c.k3_margin_multiplier

        # 3. Добавление накладных расходов (ROP)
        # rop задан в руб/кг.
        overhead_cost = (c.rop_overhead * weight) / 1000.0
        
        # Исправленная формула:
        # Price = ((VC / k2) + VC + (rop * weight / 1000)) * k3
        price_before_k3 = base_price + overhead_cost
        final_price = price_before_k3 * c.k3_margin_multiplier

        # Формирование финального результата
        context.final_result = CalculationResult(
            weight_grams=round(weight, 4),
            scrap_rate_percent=round(context.get_intermediate('scrap_rate') * 100, 2),
            material_cost=round(context.get_intermediate('material_base_cost'), 4),
            scrap_cost=round(context.get_intermediate('scrap_cost'), 4),
            labor_cost=round(context.get_intermediate('labor_cost'), 4),
            overhead_cost=round(overhead_cost, 4),
            options_cost=round(context.get_intermediate('options_cost'), 4),
            variable_cost=round(vc, 4),
            final_price=round(final_price, 2),
            
            details={
                "electricity": context.get_intermediate('electricity'),
                "salary_rate": context.get_intermediate('salary_rate'),
                "box_component": c.box_cost / 2000.0
            }
        )
