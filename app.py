from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from datetime import datetime

TAX_RATES = {
    '85171210': {'II': 0.15, 'IPI': 0.10, 'ICMS': 0.18, 'PIS': 0.0165, 'COFINS': 0.076},  # Mobile phones
    '87032310': {'II': 0.35, 'IPI': 0.25, 'ICMS': 0.18, 'PIS': 0.0165, 'COFINS': 0.076},  # Cars
    '62034200': {'II': 0.20, 'IPI': 0.05, 'ICMS': 0.12, 'PIS': 0.0165, 'COFINS': 0.076},  # Cotton trousers
    '08051000': {'II': 0.10, 'IPI': 0.00, 'ICMS': 0.07, 'PIS': 0.0165, 'COFINS': 0.076},  # Oranges
    '84713012': {'II': 0.15, 'IPI': 0.10, 'ICMS': 0.18, 'PIS': 0.0165, 'COFINS': 0.076}   # Laptops
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
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []

    # Header
    elements.append(Paragraph("ComexAI Import Cost Report", styles['Heading1']))
    elements.append(Paragraph(f"NCM Code: {ncm}", styles['Normal']))
    elements.append(Paragraph(f"Date: {datetime.now().strftime('%Y-%m-%d')}", styles['Normal']))
    elements.append(Spacer(1, 12))

    # Input Details
    elements.append(Paragraph("Input Details", styles['Heading2']))
    input_data = [
        ["Quantity", f"{quantity}"],
        ["Product Cost per Unit", f"R$ {product_cost_per_unit:.2f}"],
        ["Freight", f"R$ {freight:.2f}"],
        ["Insurance", f"R$ {insurance:.2f}"]
    ]
    input_table = Table(input_data, colWidths=[200, 200])
    input_table.setStyle([
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT')
    ])
    elements.append(input_table)
    elements.append(Spacer(1, 12))

    # Cost Breakdown
    elements.append(Paragraph("Cost Breakdown", styles['Heading2']))
    cost_data = [
        ["Description", "Amount (BRL)"],
        ["Total Product Cost", f"R$ {total_product_cost:.2f}"],
        ["Freight", f"R$ {freight:.2f}"],
        ["Insurance", f"R$ {insurance:.2f}"],
        ["Import Tax (II)", f"R$ {II:.2f}"],
        ["IPI", f"R$ {IPI:.2f}"],
        ["ICMS", f"R$ {ICMS:.2f}"],
        ["PIS", f"R$ {PIS:.2f}"],
        ["COFINS", f"R$ {COFINS:.2f}"],
        ["Total Import Cost", f"R$ {total_import_cost:.2f}"]
    ]
    cost_table = Table(cost_data, colWidths=[200, 200])
    cost_table.setStyle([
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('FONTWEIGHT', (0, -1), (-1, -1), 'BOLD'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT')
    ])
    elements.append(cost_table)
    elements.append(Spacer(1, 12))

    # Footer
    elements.append(Paragraph("Generated by ComexAI", styles['Italic']))

    doc.build(elements)
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name='import_cost_report.pdf', mimetype='application/pdf')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port, debug=True)