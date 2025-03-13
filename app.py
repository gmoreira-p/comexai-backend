from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from datetime import datetime

app = Flask(__name__)
CORS(app)

TAX_RATES = {
    '85171210': {'II': 0.15, 'IPI': 0.10, 'PIS': 0.0165, 'COFINS': 0.076},  # Mobile phones
    '87032310': {'II': 0.35, 'IPI': 0.25, 'PIS': 0.0165, 'COFINS': 0.076},  # Cars
    '62034200': {'II': 0.20, 'IPI': 0.05, 'PIS': 0.0165, 'COFINS': 0.076},  # Cotton trousers
    '08051000': {'II': 0.10, 'IPI': 0.00, 'PIS': 0.0165, 'COFINS': 0.076},  # Oranges
    '84713012': {'II': 0.15, 'IPI': 0.10, 'PIS': 0.0165, 'COFINS': 0.076}   # Laptops
}

STATE_ICMS_RATES = {
    'São Paulo': 0.18,
    'Rio de Janeiro': 0.20,
    'Paraná': 0.18,
    'Santa Catarina': 0.17,
    'Espírito Santo': 0.17
}

@app.route('/calculate', methods=['POST'])
def calculate():
    data = request.json
    ncm = data.get('ncm')
    state = data.get('state')
    if not ncm or ncm not in TAX_RATES:
        return jsonify({"error": "Invalid or unsupported NCM code"}), 400
    if not state:
        return jsonify({"error": "Invalid or unsupported state"}), 400

    try:
        quantity = float(data.get('quantity'))
        product_cost_usd = float(data.get('productCostUsd'))
        exchange_rate = float(data.get('exchangeRate'))
        # CHANGE START: Freight now in USD, Insurance now a percentage
        freight_usd = float(data.get('freightUsd', 0))
        insurance_rate = float(data.get('insuranceRate', 0))
        # CHANGE END
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid numeric input"}), 400

    rates = TAX_RATES[ncm]
    icms_rate = data.get('icmsRate') if state == 'Custom' else STATE_ICMS_RATES.get(state)
    if icms_rate is None:
        return jsonify({"error": "Invalid or unsupported state"}), 400

    # CHANGE START: Updated calculations for freight, insurance, and nationalization costs
    total_product_cost = quantity * product_cost_usd * exchange_rate  # FOB in BRL
    freight_brl = freight_usd * exchange_rate
    insurance_brl = (quantity * product_cost_usd) * insurance_rate * exchange_rate  # Insurance as % of FOB in BRL
    valor_aduaneiro = total_product_cost + freight_brl + insurance_brl  # CIF value
    II = valor_aduaneiro * rates['II']
    IPI = (valor_aduaneiro + II) * rates['IPI']
    PIS = valor_aduaneiro * rates['PIS']
    COFINS = valor_aduaneiro * rates['COFINS']
    base_icms = valor_aduaneiro + II + IPI + PIS + COFINS
    ICMS = (icms_rate * base_icms) / (1 - icms_rate)
    total_tributos = II + IPI + PIS + COFINS + ICMS
    # Despesa de Nacionalização
    afrmm = 0.25 * freight_brl  # 25% of freight in BRL
    other_nat_costs = 0.10 * total_product_cost  # 10% of FOB in BRL
    total_despesa_nacionalizacao = afrmm + other_nat_costs
    custo_liquido = valor_aduaneiro + total_tributos + total_despesa_nacionalizacao
    cost_per_unit = custo_liquido / quantity if quantity > 0 else 0
    # CHANGE END

    return jsonify({
        "total_product_cost": total_product_cost,
        # CHANGE START: Added freightBr and insuranceBr for clarity
        "freightBr": freight_brl,
        "insuranceBr": insurance_brl,
        # CHANGE END
        "valor_aduaneiro": valor_aduaneiro,
        "II": II,
        "IPI": IPI,
        "PIS": PIS,
        "COFINS": COFINS,
        "ICMS": ICMS,
        "total_tributos": total_tributos,
        # CHANGE START: Added Despesa de Nacionalização fields
        "afrmm": afrmm,
        "otherNatCosts": other_nat_costs,
        "total_despesa_nacionalizacao": total_despesa_nacionalizacao,
        # CHANGE END
        "custo_liquido": custo_liquido,
        "cost_per_unit": cost_per_unit
    })

@app.route('/generate_pdf', methods=['POST'])
def generate_pdf():
    data = request.json
    ncm = data.get('ncm')
    state = data.get('state')
    if not ncm or ncm not in TAX_RATES:
        return jsonify({"error": "Invalid or unsupported NCM code"}), 400
    if not state:
        return jsonify({"error": "Invalid or unsupported state"}), 400

    try:
        quantity = float(data.get('quantity'))
        product_cost_usd = float(data.get('productCostUsd'))
        exchange_rate = float(data.get('exchangeRate'))
        # CHANGE START: Freight now in USD, Insurance now a percentage
        freight_usd = float(data.get('freightUsd', 0))
        insurance_rate = float(data.get('insuranceRate', 0))
        # CHANGE END
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid numeric input"}), 400

    rates = TAX_RATES[ncm]
    icms_rate = data.get('icmsRate') if state == 'Custom' else STATE_ICMS_RATES.get(state)
    if icms_rate is None:
        return jsonify({"error": "Invalid or unsupported state"}), 400

    # CHANGE START: Updated calculations for freight, insurance, and nationalization costs
    total_product_cost = quantity * product_cost_usd * exchange_rate
    freight_brl = freight_usd * exchange_rate
    insurance_brl = (quantity * product_cost_usd) * insurance_rate * exchange_rate  # Insurance as % of FOB
    valor_aduaneiro = total_product_cost + freight_brl + insurance_brl
    II = valor_aduaneiro * rates['II']
    IPI = (valor_aduaneiro + II) * rates['IPI']
    PIS = valor_aduaneiro * rates['PIS']
    COFINS = valor_aduaneiro * rates['COFINS']
    base_icms = valor_aduaneiro + II + IPI + PIS + COFINS
    ICMS = (icms_rate * base_icms) / (1 - icms_rate)
    total_tributos = II + IPI + PIS + COFINS + ICMS
    afrmm = 0.25 * freight_brl
    other_nat_costs = 0.10 * total_product_cost
    total_despesa_nacionalizacao = afrmm + other_nat_costs
    custo_liquido = valor_aduaneiro + total_tributos + total_despesa_nacionalizacao
    cost_per_unit = custo_liquido / quantity if quantity > 0 else 0
    # CHANGE END

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("ComexAI Import Cost Report", styles['Heading1']))
    elements.append(Paragraph(f"NCM Code: {ncm}", styles['Normal']))
    elements.append(Paragraph(f"State: {state}", styles['Normal']))
    elements.append(Paragraph(f"Date: {datetime.now().strftime('%Y-%m-%d')}", styles['Normal']))
    elements.append(Spacer(1, 20))

    elements.append(Paragraph("Input Details", styles['Heading3']))
    # CHANGE START: Updated input details to reflect new fields
    input_data = [
        ["Quantity", f"{quantity}"],
        ["Product Cost per Unit", f"${product_cost_usd:.2f} USD"],
        ["Exchange Rate (USD to BRL)", f"{exchange_rate:.2f}"],
        ["Total Product Cost", f"R$ {total_product_cost:.2f} BRL"],
        ["Freight", f"${freight_usd:.2f} USD (R$ {freight_brl:.2f} BRL)"],
        ["Insurance Rate", f"{(insurance_rate * 100):.2f}%"],
        ["Insurance", f"R$ {insurance_brl:.2f} BRL"],
        ["State", state],
        ["ICMS Rate", f"{(icms_rate * 100):.2f}%" if state == 'Custom' else f"{(icms_rate * 100):.2f}% (Predefined)"]
    ]
    # CHANGE END
    input_table = Table(input_data, colWidths=[250, 150])
    input_table.setStyle([('GRID', (0, 0), (-1, -1), 0.5, colors.grey)])
    elements.append(input_table)
    elements.append(Spacer(1, 20))

    elements.append(Paragraph("Cost Breakdown (BRL)", styles['Heading3']))
    # CHANGE START: Updated Valor Aduaneiro section
    valor_aduaneiro_data = [
        ["Total Product Cost", f"R$ {total_product_cost:.2f}"],
        ["Freight", f"R$ {freight_brl:.2f}"],
        ["Insurance", f"R$ {insurance_brl:.2f}"],
        ["Total Valor Aduaneiro", f"R$ {valor_aduaneiro:.2f}"]
    ]
    # CHANGE END
    valor_aduaneiro_table = Table(valor_aduaneiro_data, colWidths=[250, 150])
    valor_aduaneiro_table.setStyle([('GRID', (0, 0), (-1, -1), 0.5, colors.grey), ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold')])
    elements.append(Paragraph("Valor Aduaneiro", styles['Heading4']))
    elements.append(valor_aduaneiro_table)
    elements.append(Spacer(1, 12))

    tributos_data = [
        ["II", f"R$ {II:.2f}"],
        ["IPI", f"R$ {IPI:.2f}"],
        ["PIS", f"R$ {PIS:.2f}"],
        ["COFINS", f"R$ {COFINS:.2f}"],
        ["ICMS", f"R$ {ICMS:.2f}"],
        ["Total de Tributos", f"R$ {total_tributos:.2f}"]
    ]
    tributos_table = Table(tributos_data, colWidths=[250, 150])
    tributos_table.setStyle([('GRID', (0, 0), (-1, -1), 0.5, colors.grey), ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold')])
    elements.append(Paragraph("Tributos Devidos no Desembaraço", styles['Heading4']))
    elements.append(tributos_table)
    elements.append(Spacer(1, 12))

    # CHANGE START: Added Despesa de Nacionalização section
    despesa_nacionalizacao_data = [
        ["AFRMM (25% of Freight)", f"R$ {afrmm:.2f}"],
        ["Other Nationalization Costs (10% of FOB)", f"R$ {other_nat_costs:.2f}"],
        ["Total Despesa de Nacionalização", f"R$ {total_despesa_nacionalizacao:.2f}"]
    ]
    despesa_nacionalizacao_table = Table(despesa_nacionalizacao_data, colWidths=[250, 150])
    despesa_nacionalizacao_table.setStyle([('GRID', (0, 0), (-1, -1), 0.5, colors.grey), ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold')])
    elements.append(Paragraph("Despesa de Nacionalização", styles['Heading4']))
    elements.append(despesa_nacionalizacao_table)
    elements.append(Spacer(1, 12))
    # CHANGE END

    custo_liquido_data = [
        ["Custo Líquido da Importação", f"R$ {custo_liquido:.2f}"],
        ["Cost Per Unit", f"R$ {cost_per_unit:.2f}"]
    ]
    custo_liquido_table = Table(custo_liquido_data, colWidths=[250, 150])
    custo_liquido_table.setStyle([('GRID', (0, 0), (-1, -1), 0.5, colors.grey), ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold')])
    elements.append(Paragraph("Custo Líquido da Importação", styles['Heading4']))
    elements.append(custo_liquido_table)

    doc.build(elements)
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name='import_cost_report.pdf', mimetype='application/pdf')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port, debug=True)