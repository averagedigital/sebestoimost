import pandas as pd
import io
from .models import OrderInput, CalculationResult, BagType

COLUMNS = [
    'Номенклатурная группа',
    'Родственность',
    'Продукция',
    'Единица хранения остатков',
    'Код',
    'Схема печати',
    'Тираж',
    'Вес',
    'Краска',
    'Скотч',
    'Расходы на электроэнергию',
    'Упаковка',
    'Втулка',
    'ЗП ИТОГО',
    'ЗП выгонка',
    'ЗП ламинация',
    'ЗП печать',
    'ЗП рубка',
    'ЗП резка',
    'Сырье',
    'Постоянные расходы ГУ',
    'Постоянные расходы',
    'Риски',
    'Общая себестоимость'
]

def generate_row_data(order: OrderInput, result: CalculationResult, k2: float = 2.3, k3: float = 1.7) -> dict:
    """
    Generates the dictionary representing the single row of Excel data.
    k2, k3 - margin coefficients from config
    """
    # 1. Format Product Name
    feat_str = []
    if order.features.is_wicket: feat_str.append("викет")
    if order.features.glue_tape: feat_str.append("кл.клапан")
    
    dims = f"{order.width}x{order.length}"
    if order.flap > 0:
        dims += f"+{order.flap}"
    if order.fold > 0:
        dims += f"(ф{order.fold})"
        
    product_name = f"Пакет {order.product_type.value} {' '.join(feat_str)} {dims} {order.thickness}мкм"

    # 2. Calculate Values (PER UNIT, not per batch!)
    qty = order.quantity
    total_weight_kg = (result.weight_grams * qty) / 1000.0
    
    # Unit Costs (already per unit from result)
    elec_unit = result.details.get('electricity', 0.0)
    box_unit = result.details.get('box_component', 0.0)
    mat_unit = result.material_cost + result.scrap_cost
    labor_unit = result.labor_cost
    overhead_unit = result.overhead_cost # ROP part
    
    # Variable cost per unit
    vc_unit = result.variable_cost
    # Margin component per unit: VC / K2
    # "Постоянные расходы" по логике Price = (VC/K2 + VC)...
    fixed_costs_unit = vc_unit / k2
    
    # Margin multiplier component: (VC/K2 + VC) * (K3 - 1)
    # "Риски" (Profit/Margin)
    base_for_k3 = fixed_costs_unit + vc_unit
    risks_unit = base_for_k3 * (k3 - 1.0)

    # Total Cost per unit (Final Price)
    total_cost_unit = result.final_price

    # 3. Create Row Dict (all values per UNIT, matching Excel format)
    # ZERO out fields that user asked not to fill (Electricity, Box, etc are inside VC/Total but not in cols)
    return {
        'Номенклатурная группа': 'Пакеты (Расчет)',
        'Родственность': 'ГУ пакеты',
        'Продукция': product_name,
        'Единица хранения остатков': 'шт',
        'Код': '',
        'Схема печати': order.print_scheme,
        'Тираж': qty,
        'Вес': round(total_weight_kg, 3),
        'Краска': 0,
        'Скотч': 0,
        'Расходы на электроэнергию': 0, # Included in VC/Total but invalid for column
        'Упаковка': 0, # Included in VC/Total but invalid for column
        'Втулка': 0,
        'ЗП ИТОГО': round(labor_unit, 4),
        'ЗП выгонка': 0, 
        'ЗП ламинация': 0,
        'ЗП печать': 0,
        'ЗП рубка': 0, # User said only 'ЗП ИТОГО'
        'ЗП резка': 0,
        'Сырье': round(mat_unit, 4),
        'Постоянные расходы ГУ': round(overhead_unit, 4),
        'Постоянные расходы': round(fixed_costs_unit, 4),
        'Риски': round(risks_unit, 4),
        'Общая себестоимость': round(total_cost_unit, 4)
    }

def generate_excel_bytes(order: OrderInput, result: CalculationResult, k2: float = 2.3, k3: float = 1.7) -> io.BytesIO:
    """
    Generates an Excel file replicating the structure of the source cost data.
    """
    row_data = generate_row_data(order, result, k2, k3)
    df = pd.DataFrame([row_data], columns=COLUMNS)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Расчет')
        
        # Auto-size columns
        worksheet = writer.sheets['Расчет']
        for idx, col in enumerate(worksheet.columns):
            max_length = 0
            # Get header length
            column = col[0].column_letter # Get the column name
            header_val = col[0].value
            if header_val:
                max_length = len(str(header_val))
            
            # Check data length
            for cell in col:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            
            # Set width (approximate factor)
            adjusted_width = (max_length + 2) * 1.2
            worksheet.column_dimensions[col[0].column_letter].width = adjusted_width
        
    output.seek(0)
    return output
