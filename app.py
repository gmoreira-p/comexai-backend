from flask import Flask, request, jsonify
from flask_cors import CORS
import os

TAX_RATES = {
    'electronics': {
        'II': 0.10,  # 10% Import Tax
        'IPI': 0.05,  # 5% IPI
        'ICMS': 0.18,  # 18% ICMS
        'PIS': 0.0165,  # 1.65% PIS
        'COFINS': 0.076  # 7.6% COFINS
    },
    'agriculture': {
        'II': 0.05,  # 5% Import Tax
        'IPI': 0.02,  # 2% IPI
        'ICMS': 0.12,  # 12% ICMS
        'PIS': 0.0165,  # 1.65% PIS
        'COFINS': 0.076  # 7.6% COFINS
    }
    # Add more categories as needed
}

app = Flask(__name__)
CORS(app)  # Allows your front end to connect

@app.route('/')
def home():
    return "Welcome to ComexAI Backend!"

@app.route('/calculate', methods=['POST'])
def calculate():
    data = request.json
    category = data.get('category')
    quantity = float(data.get('quantity'))
    product_cost_per_unit = float(data.get('productCost'))
    freight = float(data.get('freight', 0))
    insurance = float(data.get('insurance', 0))

    if category not in TAX_RATES:
        return jsonify({"error": "Invalid category"}), 400

    rates = TAX_RATES[category]

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

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))  # Use Render's port or default to 10000
    app.run(host='0.0.0.0', port=port, debug=True)