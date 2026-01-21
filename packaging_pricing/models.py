from enum import Enum
from typing import Optional, Dict
from pydantic import BaseModel, Field, ConfigDict, model_validator

class BagType(str, Enum):
    BOPP = "BOPP"
    CPP = "CPP"

class ProductKind(str, Enum):
    BAG = "bag"

class Features(BaseModel):
    """
    Дополнительные опции заказа (фичи).
    """
    is_wicket: bool = Field(default=False, description="Викет-пакет?")
    glue_tape: bool = Field(default=False, description="Есть клеевой клапан?")
    dead_tape: bool = Field(default=False, description="Есть 'мертвый' скотч (dead_glue)?")
    euroslot: Optional[str] = Field(default=None, description="Тип еврослота: 'pvd', 'bopp' или None")
    clips: bool = Field(default=False, description="Есть клипсы?")

    @model_validator(mode="after")
    def validate_options(self) -> "Features":
        if self.glue_tape and self.dead_tape:
            raise ValueError("glue_tape and dead_tape are mutually exclusive")
        if not self.is_wicket and self.clips:
            self.clips = False
        return self

class OrderInput(BaseModel):
    """
    Входные данные заказа от менеджера.
    Геометрия, тип пленки, количество и опции.
    """
    model_config = ConfigDict(extra='forbid')

    product_kind: ProductKind = Field(default=ProductKind.BAG, description="Вид продукции")
    product_type: BagType
    width: float = Field(..., gt=0, description="Ширина (см)")
    fold: float = Field(default=0.0, ge=0, description="Складка (см)")
    length: float = Field(..., gt=0, description="Длина (см)")
    flap: float = Field(default=0.0, ge=0, description="Клапан (см)")
    thickness: float = Field(..., gt=0, description="Толщина (микрон)")
    quantity: int = Field(..., gt=0, description="Тираж (штук)")
    print_scheme: str = Field(default="б/печати", description="Схема печати")
    features: Features = Field(default_factory=Features)

class PricingConfig(BaseModel):
    """
    Конфигурация ценообразования (переменные экономиста).
    """
    model_config = ConfigDict(extra='ignore')

    density: float = 0.91  # Плотность г/см3
    
    # Split material prices
    material_price_bopp: float
    material_price_cpp: float
    
    k1_salary_coeff: float = 3.6
    box_cost: float
    scrap_return_price: float = 10.0
    k2_margin_divisor: float = 2.3
    k3_margin_multiplier: float = 1.7
    rop_overhead: float = 6.0
    
    # Стоимость фич (руб/см длины или руб/шт)
    feature_rates: Dict[str, float] = Field(default_factory=lambda: {
        "glue": 0.0,
        "dead_glue": 0.0,
        "euroslot_pvd": 0.0,
        "euroslot_bopp": 0.0,
        "clips": 0.0
    })

    # Тарифы на труд и электроэнергию
    electricity_rate: float = 0.0095
    salary_std_small: float = 0.04
    salary_std_large: float = 0.053
    salary_wicket_small: float = 0.075
    salary_wicket_large: float = 0.078

class CalculationResult(BaseModel):
    """
    Детализированный результат расчета себестоимости.
    """
    weight_grams: float
    scrap_rate_percent: float
    material_cost: float
    scrap_cost: float
    labor_cost: float
    overhead_cost: float
    options_cost: float
    variable_cost: float
    final_price: float
    
    # Детали для отладки и визуализации
    details: Dict[str, float] = Field(default_factory=dict)
