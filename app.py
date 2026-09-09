from flask import Flask, jsonify, render_template, request
from utils.market_api import StockDataFetcher
from utils.data_processor import forecast_prices, prepare_price_data

app = Flask(__name__, template_folder='template')
fetcher = StockDataFetcher()


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/stock_data', methods=['GET'])
def get_stock_data():
    try:
        symbol = request.args.get('symbol')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        if not all([symbol, start_date, end_date]):
            return jsonify({'error': 'Missing required parameters'}), 400
        
        df = fetcher.fetch_data(symbol, start_date, end_date)
        prices = prepare_price_data(df)
        forecast_days = request.args.get('forecast_days', default=5, type=int)

        return jsonify({
            'data': prices.to_dict(orient='records'),
            'info': fetcher.get_stock_info(symbol),
            'prediction': forecast_prices(df, forecast_days),
            'news': {'status': 'unavailable', 'message': 'News sentiment is not configured yet.'}
        })
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)