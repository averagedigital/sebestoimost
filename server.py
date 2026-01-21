from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse, RedirectResponse
from packaging_pricing.models import OrderInput, PricingConfig, CalculationResult
from packaging_pricing.pipeline import PricingPipeline
from packaging_pricing.steps import (
    GeometryCalculationStep,
    ScrapCalculationStep,
    LaborCostStep,
    MaterialCostStep,
    PricingStep
)
from packaging_pricing.scraps import TableBasedScrapProvider
from packaging_pricing.export import generate_excel_bytes, generate_row_data
import uvicorn
import os

app = FastAPI(title="Packaging Cost Engine")

# Mount static files (frontend)
app.mount("/ui", StaticFiles(directory="static", html=True), name="static")

@app.get("/")
def read_root():
    return RedirectResponse(url="/ui/index.html")

# Global state for configuration (In-memory storage)
current_config = PricingConfig(
    material_price_bopp=200.0,
    material_price_cpp=220.0, 
    k1_salary_coeff=3.6,
    box_cost=50.0,
    scrap_return_price=10.0,
    k2_margin_divisor=2.3,
    k3_margin_multiplier=1.7,
    rop_overhead=6.0,
    feature_rates={
        "glue": 0.5,
        "dead_glue": 0.3,
        "euroslot_pvd": 1.5,
        "euroslot_bopp": 1.2,
        "clips": 2.0
    },
    electricity_rate=0.0095,
    salary_std_small=0.04,
    salary_std_large=0.053,
    salary_wicket_small=0.075,
    salary_wicket_large=0.078
)

@app.get("/api/config", response_model=PricingConfig)
def get_config():
    """Returns the current pricing configuration."""
    return current_config

@app.post("/api/config", response_model=PricingConfig)
def update_config(config: PricingConfig):
    """Updates the global pricing configuration."""
    global current_config
    current_config = config
    return current_config

@app.post("/api/calculate", response_model=CalculationResult)
def calculate_price(order: OrderInput):
    """Calculates the price for a given order using current config."""
    
    # Build Pipeline
    scrap_provider = TableBasedScrapProvider()
    steps = [
        GeometryCalculationStep(),
        ScrapCalculationStep(provider=scrap_provider),
        LaborCostStep(),
        MaterialCostStep(),
        PricingStep()
    ]
    
    pipeline = PricingPipeline(steps=steps, config=current_config)
    
    try:
        result = pipeline.calculate(order)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/preview_table")
def preview_table(order: OrderInput):
    """Returns the Excel row data as JSON for UI preview."""
    # Perform calculation
    scrap_provider = TableBasedScrapProvider()
    steps = [
        GeometryCalculationStep(),
        ScrapCalculationStep(provider=scrap_provider),
        LaborCostStep(),
        MaterialCostStep(),
        PricingStep()
    ]
    pipeline = PricingPipeline(steps, current_config)
    
    try:
        result = pipeline.calculate(order)
        row_data = generate_row_data(order, result, current_config.k2_margin_divisor, current_config.k3_margin_multiplier)
        return row_data
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/export_excel")
def export_excel(order: OrderInput):
    """Generates Excel export for the order."""
    # Perform calculation first
    scrap_provider = TableBasedScrapProvider()
    steps = [
        GeometryCalculationStep(),
        ScrapCalculationStep(provider=scrap_provider),
        LaborCostStep(),
        MaterialCostStep(),
        PricingStep()
    ]
    pipeline = PricingPipeline(steps, current_config)
    result = pipeline.calculate(order)
    
    # Generate Excel
    excel_file = generate_excel_bytes(order, result, current_config.k2_margin_divisor, current_config.k3_margin_multiplier)
    
    headers = {
        'Content-Disposition': 'attachment; filename="calculation_export.xlsx"'
    }
    return StreamingResponse(
        excel_file, 
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 
        headers=headers
    )

if __name__ == "__main__":
    # Launch server
    print("Starting server on http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
