from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
from io import BytesIO
from reportlab.pdfgen import canvas
from datetime import datetime

TAX_RATES = {
    '85171210': {  # Mobile phones
        'II': 0.15,     # 15% Import Tax
        'IPI': 0.10,    # 10% IPI
        'ICMS': 0.18,   # 18% ICMS
        'PIS': 0.0165,  # 1.65% PIS
        'COFINS': 0.076 # 7.6% COFINS
    },
    '87032310': {  # Cars
        'II': 0.35,     # 35% Import Tax
        'IPI': 0.25,    # 25% IPI
        'ICMS': 0.18,   # 18% ICMS
        'PIS': 0.0165,  # 1.65% PIS
        'COFINS': 0.076 # 7.6% COFINS
    },
    '62034200': {  # Cotton trousers
        'II': 0.20,     # 20% Import Tax
        'IPI': 0.05,    # 5% IPI
        'ICMS': 0.12,   # 12% ICMS
        'PIS': 0.0165,  # 1.65% PIS
        'COFINS': 0.076 # 7.6% COFINS
    },
    '08051000': {  # Oranges
        'II': 0.10,     # 10% Import Tax
        'IPI': 0.00,    # 0% IPI
        'ICMS': 0.07,   # 7% ICMS
        'PIS': 0.0165,  # 1.65% PIS
        'COFINS': 0.076 # 7.6% COFINS
    },
    '84713012': {  # Laptops
        'II': 0.15,     # 15% Import Tax
        'IPI': 0.10,    # 10% IPI
        'ICMS': 0.18,   # 18% ICMS
        'PIS': 0.0165,  # 1.65% PIS
        'COFINS': 0.076 # 7.6% COFINS
    }
}

app = Flask(__name__)
CORS(app)

@app.route('/')
def home():
    return "Welcome to ComexAI Backend!"

@app.route('/calculate', methods=['POST'])
def calculate():
    data = request.json
    ncm = data.get('ncm')
    if not ncm or ncm not in TAX_RATES:
        return jsonify({"error": "Invalid or unsupported NCM code"}), 400

    try:
        quantity = float(data.get('quantity'))
        product_cost_per_unit = float(data.get('productCost'))
        freight = float(data.get('freight', 0))
        insurance = float(data.get('insurance', 0))
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid numeric input"}), 400

    rates = TAX_RATES[ncm]

    total_product_cost = quantity * product_cost_per_unit
    customs_value = total_product_cost + freight + insurance

    II = customs_value * rates['II']
    IPI = customs_value * rates['IPI']
    PIS = customs_value * rates['PIS']
    COFINS = customs_value * rates['COFINS']
    ICMS = (customs_value + II + IPI + PIS + COFINS) * rates['ICMS']

    total_import_cost = total_product_cost + freight + insurance + II + IPI + ICMS + PIS + COFINS

    response = {
        "total_product_cost": total_product_cost,
        "freight": freight,
        "insurance": insurance,
        "II": II,
        "IPI": IPI,
        "ICMS": ICMS,
        "PIS": PIS,
        "COFINS": COFINS,
        "total_import_cost": total_import_cost
    }
    return jsonify(response)

@app.route('/generate_pdf', methods=['POST'])
def generate_pdf():
    data = request.json
    ncm = data.get('ncm')
    if not ncm or ncm not in TAX_RATES:
        return jsonify({"error": "Invalid or unsupported NCM code"}), 400

    try:
        quantity = float(data.get('quantity'))
        product_cost_per_unit = float(data.get('productCost'))
        freight = float(data.get('freight', 0))
        insurance = float(data.get('insurance', 0))
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid numeric input"}), 400

    rates = TAX_RATES[ncm]

    total_product_cost = quantity * product_cost_per_unit
    customs_value = total_product_cost + freight + insurance
    II = customs_value * rates['II']
    IPI = customs_value * rates['IPI']
    PIS = customs_value * rates['PIS']
    COFINS = customs_value * rates['COFINS']
    ICMS = (customs_value + II + IPI + PIS + COFINS) * rates['ICMS']
    total_import_cost = total_product_cost + freight + insurance + II + IPI + ICMS + PIS + COFINS

    buffer = BytesIO()
    p = canvas.Canvas(buffer)

    # Header
    p.setFont("Helvetica-Bold", 16)
    p.drawString(100, 750, "ComexAI Import Cost Report")
    p.setFont("Helvetica", 12)
    p.drawString(100, 730, f"NCM Code: {ncm}")
    p.drawString(100, 710, f"Date: {datetime.now().strftime('%Y-%m-%d')}")

    # Input Details
    p.drawString(100, 680, "Input Details")
    p.line(100, 675, 500, 675)
    p.drawString(100, 660, f"Quantity: {quantity}")
    p.drawString(100, 640, f"Product Cost per Unit: R$ {product_cost_per_unit:.2f}")
    p.drawString(100, 620, f"Freight: R$ {freight:.2f}")
    p.drawString(100, 600, f"Insurance: R$ {insurance:.2f}")

    # Cost Breakdown
    p.drawString(100, 570, "Cost Breakdown")
    p.line(100, 565, 500, 565)
    y = 550
    costs = {
        "Total Product Cost": total_product_cost,
        "Freight": freight,
        "Insurance": insurance,
        "Import Tax (II)": II,
        "IPI": IPI,
        "ICMS": ICMS,
        "PIS": PIS,
        "COFINS": COFINS,
        "Total Import Cost": total_import_cost
    }
    for label, value in costs.items():
        p.drawString(100, y, f"{label}: R$ {value:.2f}")
        y -= 20

    # Footer
    p.setFont("Helvetica-Oblique", 10)
    p.drawString(100, 50, "Generated by ComexAI")

    p.showPage()
    p.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name='report.pdf', mimetype='application/pdf')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port, debug=True)