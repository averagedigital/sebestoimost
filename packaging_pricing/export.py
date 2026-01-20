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

def generate_row_data(order: OrderInput, result: CalculationResult) -> dict:
    """
    Generates the dictionary representing the single row of Excel data.
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

    # 2. Calculate Totals
    qty = order.quantity
    total_weight_kg = (result.weight_grams * qty) / 1000.0
    
    # Unit/Total Costs
    elec_unit = result.details.get('electricity', 0.0)
    box_unit = result.details.get('box_component', 0.0)
    mat_unit = result.material_cost + result.scrap_cost
    
    total_labor = result.labor_cost * qty
    total_elec = elec_unit * qty
    total_box = box_unit * qty
    total_mat = mat_unit * qty
    total_overhead = result.overhead_cost * qty
    total_cost = (result.variable_cost + result.overhead_cost) * qty

    # 3. Create Row Dict
    return {
        'Номенклатурная группа': 'Пакеты (Расчет)',
        'Родственность': '',
        'Продукция': product_name,
        'Единица хранения остатков': 'шт',
        'Код': '',
        'Схема печати': order.print_scheme,
        'Тираж': qty,
        'Вес': round(total_weight_kg, 3),
        'Краска': 0,
        'Скотч': 0,
        'Расходы на электроэнергию': round(total_elec, 2),
        'Упаковка': round(total_box, 2),
        'Втулка': 0,
        'ЗП ИТОГО': round(total_labor, 2),
        'ЗП выгонка': 0, 
        'ЗП ламинация': 0,
        'ЗП печать': 0,
        'ЗП рубка': round(total_labor, 2),
        'ЗП резка': 0,
        'Сырье': round(total_mat, 2),
        'Постоянные расходы ГУ': round(total_overhead, 2), # ROP
        'Постоянные расходы': round((result.variable_cost * qty) / 2.3, 2), # VC / K2
        'Риски': 0,
        'Общая себестоимость': round(total_cost, 2)
    }

def generate_excel_bytes(order: OrderInput, result: CalculationResult) -> io.BytesIO:
    """
    Generates an Excel file replicating the structure of the source cost data.
    """
    row_data = generate_row_data(order, result)
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
