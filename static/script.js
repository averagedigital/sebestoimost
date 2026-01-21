const API_CALC = "/api/calculate";
const API_CONFIG = "/api/config";
const API_EXPORT = "/api/export_excel";

document.addEventListener("DOMContentLoaded", () => {
    // 1. Initial Load
    fetchConfig();

    // 2. Tab Logic
    document.querySelectorAll(".tab-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
            document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));

            btn.classList.add("active");
            document.getElementById(btn.dataset.tab).classList.add("active");
        });
    });

    // 3. Calculator Submit
    document.getElementById("calcForm").addEventListener("submit", async (e) => {
        e.preventDefault();
        await calculate();
    });

    // 4. Config Save
    document.getElementById("configForm").addEventListener("submit", async (e) => {
        e.preventDefault();
        await saveConfig();
    });

    // 5. Export Excel
    const exportBtn = document.getElementById("exportBtn");
    if (exportBtn) {
        exportBtn.addEventListener("click", async (e) => {
            e.preventDefault();
            await exportExcel();
        });
    }

    // 6. Mutually exclusive glue options
    const glueInput = document.querySelector('input[name="glue_tape"]');
    const deadGlueInput = document.querySelector('input[name="dead_tape"]');
    if (glueInput && deadGlueInput) {
        glueInput.addEventListener("change", () => {
            if (glueInput.checked) {
                deadGlueInput.checked = false;
            }
        });
        deadGlueInput.addEventListener("change", () => {
            if (deadGlueInput.checked) {
                glueInput.checked = false;
            }
        });
    }

    // 7. Wicket toggle logic: disable glue/dead tape, restrict euroslot
    const wicketToggle = document.getElementById('wicketToggle');
    const euroslotSelect = document.querySelector('select[name="euroslot"]');

    function handleWicketChange() {
        const isWicket = wicketToggle.checked;

        // Disable glue and dead tape for wicket
        glueInput.disabled = isWicket;
        deadGlueInput.disabled = isWicket;

        if (isWicket) {
            glueInput.checked = false;
            deadGlueInput.checked = false;
        }

        // Apply visual styling to parent labels
        const glueRow = glueInput.closest('.toggle-row');
        const deadRow = deadGlueInput.closest('.toggle-row');
        if (glueRow) glueRow.classList.toggle('disabled', isWicket);
        if (deadRow) deadRow.classList.toggle('disabled', isWicket);

        // Restrict euroslot to "Нет" for wicket
        if (euroslotSelect) {
            if (isWicket) {
                euroslotSelect.value = '';
                euroslotSelect.disabled = true;
            } else {
                euroslotSelect.disabled = false;
            }
        }
    }

    if (wicketToggle) {
        wicketToggle.addEventListener('change', handleWicketChange);
        // Initialize state on page load
        handleWicketChange();
    }

    // 8. Dynamic batch weight calculation
    const widthInput = document.querySelector('input[name="width"]');
    const lengthInput = document.querySelector('input[name="length"]');
    const foldInput = document.querySelector('input[name="fold"]');
    const flapInput = document.querySelector('input[name="flap"]');
    const thicknessInput = document.querySelector('input[name="thickness"]');
    const quantityInput = document.querySelector('input[name="quantity"]');

    function calculateBatchWeight() {
        const density = 0.91; // g/cm³ constant
        const width = parseFloat(widthInput.value) || 0;
        const length = parseFloat(lengthInput.value) || 0;
        const fold = parseFloat(foldInput.value) || 0;
        const flap = parseFloat(flapInput.value) || 0;
        const thickness = parseFloat(thicknessInput.value) || 0;
        const quantity = parseInt(quantityInput.value) || 0;

        // Weight formula (g) = ((width + fold) * (length + flap/2) * thickness * 2 * density) / 10000
        const weightGrams = ((width + fold) * (length + flap / 2) * thickness * 2 * density) / 10000;
        const batchWeightKg = (weightGrams * quantity) / 1000;

        // Update display element
        const batchWeightDisplay = document.getElementById('batchWeightDisplay');
        if (batchWeightDisplay) {
            batchWeightDisplay.textContent = batchWeightKg.toFixed(2) + ' кг';
        }
    }

    // Attach listeners to all dimension/quantity inputs
    [widthInput, lengthInput, foldInput, flapInput, thicknessInput, quantityInput].forEach(input => {
        if (input) {
            input.addEventListener('input', calculateBatchWeight);
        }
    });

    // Initial calculation
    calculateBatchWeight();
});


async function fetchConfig() {
    try {
        const res = await fetch(API_CONFIG);
        const config = await res.json();
        populateSettingsForm(config);
    } catch (e) {
        console.error("Failed to load config", e);
    }
}

function populateSettingsForm(config) {
    const form = document.getElementById("configForm");

    // Core (Monthly/Yearly)
    setVal(form, "density", config.density);
    setVal(form, "material_price_bopp", config.material_price_bopp);
    setVal(form, "material_price_cpp", config.material_price_cpp);
    setVal(form, "scrap_return_price", config.scrap_return_price);
    setVal(form, "rop_overhead", config.rop_overhead);
    setVal(form, "box_cost", config.box_cost);
    setVal(form, "k1_salary_coeff", config.k1_salary_coeff);
    setVal(form, "k2_margin_divisor", config.k2_margin_divisor);
    setVal(form, "k3_margin_multiplier", config.k3_margin_multiplier);

    // Electricity & Labor
    setVal(form, "electricity_rate", config.electricity_rate);
    setVal(form, "salary_std_small", config.salary_std_small);
    setVal(form, "salary_std_large", config.salary_std_large);
    setVal(form, "salary_wicket_small", config.salary_wicket_small);
    setVal(form, "salary_wicket_large", config.salary_wicket_large);

    // Feature Rates
    setVal(form, "rate_glue", config.feature_rates.glue);
    setVal(form, "rate_dead_glue", config.feature_rates.dead_glue);
    setVal(form, "rate_clips", config.feature_rates.clips);
    setVal(form, "rate_euroslot_pvd", config.feature_rates.euroslot_pvd);
    setVal(form, "rate_euroslot_bopp", config.feature_rates.euroslot_bopp);
}

function setVal(form, name, val) {
    const input = form.querySelector(`[name="${name}"]`);
    if (input) input.value = val;
}

async function saveConfig() {
    const formData = new FormData(document.getElementById("configForm"));
    const config = {
        density: parseFloat(formData.get("density")),
        material_price_bopp: parseFloat(formData.get("material_price_bopp")),
        material_price_cpp: parseFloat(formData.get("material_price_cpp")),
        scrap_return_price: parseFloat(formData.get("scrap_return_price")),
        rop_overhead: parseFloat(formData.get("rop_overhead")),
        box_cost: parseFloat(formData.get("box_cost")),
        k1_salary_coeff: parseFloat(formData.get("k1_salary_coeff")),
        k2_margin_divisor: parseFloat(formData.get("k2_margin_divisor")),
        k3_margin_multiplier: parseFloat(formData.get("k3_margin_multiplier")),

        electricity_rate: parseFloat(formData.get("electricity_rate")),
        salary_std_small: parseFloat(formData.get("salary_std_small")),
        salary_std_large: parseFloat(formData.get("salary_std_large")),
        salary_wicket_small: parseFloat(formData.get("salary_wicket_small")),
        salary_wicket_large: parseFloat(formData.get("salary_wicket_large")),

        feature_rates: {
            glue: parseFloat(formData.get("rate_glue")),
            dead_glue: parseFloat(formData.get("rate_dead_glue")),
            clips: parseFloat(formData.get("rate_clips")),
            euroslot_pvd: parseFloat(formData.get("rate_euroslot_pvd")),
            euroslot_bopp: parseFloat(formData.get("rate_euroslot_bopp"))
        }
    };

    try {
        const res = await fetch(API_CONFIG, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(config)
        });
        if (res.ok) {
            document.getElementById("saveStatus").textContent = "Сохранено!";
            setTimeout(() => document.getElementById("saveStatus").textContent = "", 2000);
        }
    } catch (e) {
        alert("Ошибка сохранения");
    }
}

function getPayloadFromForm() {
    const formData = new FormData(document.getElementById("calcForm"));
    return {
        product_kind: formData.get("product_kind") || "bag",
        product_type: formData.get("product_type"),
        width: parseFloat(formData.get("width")),
        length: parseFloat(formData.get("length")),
        fold: parseFloat(formData.get("fold")) || 0,
        flap: parseFloat(formData.get("flap")) || 0,
        thickness: parseFloat(formData.get("thickness")),
        quantity: parseInt(formData.get("quantity")),
        print_scheme: formData.get("print_scheme") || "б/печати",
        features: {
            is_wicket: formData.get("is_wicket") === "on",
            glue_tape: formData.get("glue_tape") === "on",
            dead_tape: formData.get("dead_tape") === "on",
            clips: formData.get("clips") === "on",
            euroslot: formData.get("euroslot") || null
        }
    };
}

async function calculate() {
    const payload = getPayloadFromForm();
    try {
        // Parallel requests: Calc + Preview
        const [resCalc, resPreview] = await Promise.all([
            fetch(API_CALC, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            }),
            fetch("/api/preview_table", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            })
        ]);

        if (!resCalc.ok) {
            alert("Ошибка расчета");
            return;
        }

        const data = await resCalc.json();
        renderResult(data);

        if (resPreview.ok) {
            const previewData = await resPreview.json();
            renderPreviewTable(previewData);
        }

    } catch (e) {
        console.error(e);
    }
}

function renderPreviewTable(row) {
    const container = document.getElementById("previewContainer");
    if (container) {
        container.classList.remove("hidden");

        const thead = document.getElementById("previewHeader");
        const tbody = document.getElementById("previewBody");

        thead.innerHTML = "";
        tbody.innerHTML = "";

        Object.keys(row).forEach(key => {
            const th = document.createElement("th");
            th.textContent = key;
            thead.appendChild(th);

            const td = document.createElement("td");
            td.textContent = row[key];
            tbody.appendChild(td);
        });
    }
}

async function exportExcel() {
    const payload = getPayloadFromForm();
    try {
        const res = await fetch(API_EXPORT, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        if (!res.ok) {
            alert("Ошибка экспорта");
            return;
        }

        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `calculation_${new Date().toISOString().slice(0, 10)}.xlsx`;
        document.body.appendChild(a);
        a.click();
        a.remove();

    } catch (e) {
        console.error("Export error:", e);
        alert("Не удалось скачать Excel");
    }
}

function renderResult(data) {
    document.getElementById("emptyState").classList.add("hidden");
    document.getElementById("resultContent").classList.remove("hidden");

    document.getElementById("finalPrice").textContent = data.final_price.toFixed(2) + " ₽";
    document.getElementById("weightVal").textContent = data.weight_grams.toFixed(2) + " г";
    document.getElementById("scrapVal").textContent = data.scrap_rate_percent + "%";

    // Formula results
    document.getElementById("formulaWeight").textContent = data.weight_grams.toFixed(4);
    document.getElementById("formulaVC").textContent = data.variable_cost.toFixed(4);
    document.getElementById("formulaPrice").textContent = data.final_price.toFixed(4);

    const metrics = {
        material: data.material_cost,
        scrap: data.scrap_cost,
        labor: data.labor_cost + data.details.electricity + (data.details.box_component || 0),
        options: data.options_cost,
        overhead: data.overhead_cost
    };

    const max = Math.max(...Object.values(metrics)) * 1.2; // 20% buffer

    updateBar("Material", metrics.material, max);
    updateBar("Scrap", metrics.scrap, max);
    updateBar("Labor", metrics.labor, max);
    updateBar("Options", metrics.options, max);
    updateBar("Overhead", metrics.overhead, max);

    document.getElementById("valVC").textContent = data.variable_cost.toFixed(2);
}

function updateBar(key, val, max) {
    document.getElementById(`val${key}`).textContent = val.toFixed(2);
    document.getElementById(`bar${key}`).style.width = ((val / max) * 100) + "%";
}
