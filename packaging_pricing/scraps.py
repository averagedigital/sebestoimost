from .interfaces import ScrapRateProvider
from .models import BagType

class TableBasedScrapProvider(ScrapRateProvider):
    """
    Стандартная логика расчета отхода на основе табличных данных по тиражу.
    Ссылка: Раздел B технического задания.
    """
    def get_scrap_rate(self, quantity: int, bag_type: BagType) -> float:
        # Строгие правила из ТЗ:
        # 30,001 - 50,000: 15%
        # 50,001 - 100,000: 13%
        # > 100,000: 7%
        # > 300,000: 6% (реализовано дополнительно)
        
        if quantity <= 30000:
            # Не определено в ТЗ для < 30к, берем максимальный процент для безопасности.
            # Учитывая, что таблица начинается с "30,001", используем 15% как базу для малых тиражей.
            return 0.15
        elif quantity <= 50000:
            return 0.15
        elif quantity <= 100000:
            return 0.13
        elif quantity <= 300000:
            return 0.07
        else:
            # > 300,000
            return 0.06

class MLScrapRateProvider(ScrapRateProvider):
    """
    Будущая реализация: загрузка обученной ML модели для прогнозирования отхода
    на основе исторических данных, сложности макета и состояния оборудования.
    """
    def __init__(self, model_path: str = "models/scrap_predictor_v1.pkl"):
        self.model_path = model_path
        # TODO: Загрузка модели через joblib или torch
        # self.model = load_model(model_path)

    def get_scrap_rate(self, quantity: int, bag_type: BagType) -> float:
        # TODO: Подготовка вектора признаков (features vector)
        # prediction = self.model.predict([[quantity, bag_type.value]])
        # return float(prediction[0])
        raise NotImplementedError("ML модель еще не обучена.")
