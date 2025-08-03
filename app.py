from flask import Flask, jsonify, request
from utils.market_api import StockDataFetcher

app = Flask(__name__)
fetcher = StockDataFetcher()

@app.route('/api/stock_data', methods=['GET'])
def get_stock_data():
    try:
        symbol = request.args.get('symbol')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        if not all([symbol, start_date, end_date]):
            return jsonify({'error': 'Missing required parameters'}), 400
        
        df = fetcher.fetch_data(symbol, start_date, end_date)

        return jsonify({
            'data': df.to_dict(orient='records'),
            'info': fetcher.get_stock_info(symbol)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)