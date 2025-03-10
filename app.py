from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # This line lets your front end connect

@app.route('/')
def home():
    return "Welcome to ComexAI Backend!"

@app.route('/calculate', methods=['POST'])
def calculate():
    data = request.json
    category = data.get('category')
    quantity = float(data.get('quantity'))
    product_cost = float(data.get('productCost'))
    freight = float(data.get('freight', 0))
    insurance = float(data.get('insurance', 0))
    
    response = {
        "message": f"Received: {category}, {quantity} units, {product_cost} BRL per unit",
        "freight": freight,
        "insurance": insurance
    }
    return jsonify(response)

if __name__ == '__main__':
    app.run(debug=True)