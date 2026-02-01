from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import time
import threading
import json
import re
import os
from datetime import datetime
from dotenv import load_dotenv
from trading_engine import TradingEngine
from market_data import MarketDataFetcher
from ai_trader import AITrader
from portfolio_advisor import PortfolioAdvisor
from database import Database

# Load environment variables from .env file
load_dotenv()

# Version information
__version__ = '1.0.0'
__github_owner__ = 'beastdzns'
__repo__ = 'TeamXion_risk_aware_trading'
GITHUB_REPO_URL = f'https://github.com/{__github_owner__}/{__repo__}'
LATEST_RELEASE_URL = f'{GITHUB_REPO_URL}/releases/latest'

app = Flask(__name__)

# CORS Configuration - Allow requests from any origin (for Railway deployment)
# This allows the frontend (deployed separately or locally) to access the backend API
CORS(app, resources={
    r"/api/*": {
        "origins": "*",  # Allow all origins - you can restrict this to specific domains in production
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True
    }
})

# Load configuration from environment variables
DATABASE_PATH = os.getenv('DATABASE_PATH', 'Xion.db')
TRADE_FEE_RATE = float(os.getenv('TRADE_FEE_RATE', '0.001'))
AUTO_TRADING = os.getenv('AUTO_TRADING', 'True').lower() == 'true'

db = Database(DATABASE_PATH)
market_fetcher = MarketDataFetcher()
trading_engines = {}
auto_trading = AUTO_TRADING

# Helper function to infer provider type from provider name
def infer_provider_type(provider_name: str, api_url: str = '') -> str:
    """Infer provider type from provider name or API URL"""
    name_lower = provider_name.lower()
    url_lower = api_url.lower()
    
    if 'openai' in name_lower or 'openai' in url_lower:
        return 'openai'
    elif 'anthropic' in name_lower or 'claude' in name_lower or 'anthropic' in url_lower:
        return 'anthropic'
    elif 'google' in name_lower or 'gemini' in name_lower or 'google' in url_lower:
        return 'google'
    elif 'deepseek' in name_lower or 'deepseek' in url_lower:
        return 'openai' 
    else:
        return 'openai'  # Default to OpenAI-compatible

# Initialize WebSocket for real-time prices
from websocket_prices import PriceWebSocket

price_websocket = PriceWebSocket()
realtime_prices = {}  # Global cache for real-time prices

def on_price_update(data):
    """Callback for WebSocket price updates"""
    realtime_prices[data['coin']] = data
    # You can add Socket.IO emit here if you want to push to frontend

# Start WebSocket in background
price_websocket.add_callback(on_price_update)
price_websocket.start(['BTC', 'ETH', 'SOL', 'BNB', 'XRP', 'DOGE'])  

@app.route('/')
def index():
    return render_template('index.html')

# ============ Provider API Endpoints ============

@app.route('/api/providers', methods=['GET'])
def get_providers():
    """Get all API providers"""
    providers = db.get_all_providers()
    return jsonify(providers)

@app.route('/api/providers', methods=['POST'])
def add_provider():
    """Add new API provider"""
    data = request.json
    try:
        provider_id = db.add_provider(
            name=data['name'],
            api_url=data['api_url'],
            api_key=data['api_key'],
            models=data.get('models', '')
        )
        return jsonify({'id': provider_id, 'message': 'Provider added successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/providers/<int:provider_id>', methods=['DELETE'])
def delete_provider(provider_id):
    """Delete API provider"""
    try:
        db.delete_provider(provider_id)
        return jsonify({'message': 'Provider deleted successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/providers/models', methods=['POST'])
def fetch_provider_models():
    """Fetch available models from provider's API"""
    data = request.json
    api_url = data.get('api_url')
    api_key = data.get('api_key')

    if not api_url or not api_key:
        return jsonify({'error': 'API URL and key are required'}), 400

    try:
        # This is a placeholder - implement actual API call based on provider
        # For now, return empty list or common models
        models = []

        # Try to detect provider type and call appropriate API
        if 'openai.com' in api_url.lower():
            # OpenAI API call
            import requests
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            response = requests.get(f'{api_url}/models', headers=headers, timeout=10)
            if response.status_code == 200:
                result = response.json()
                models = [m['id'] for m in result.get('data', []) if 'gpt' in m['id'].lower()]
        elif 'deepseek' in api_url.lower():
            # DeepSeek API
            import requests
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            response = requests.get(f'{api_url}/models', headers=headers, timeout=10)
            if response.status_code == 200:
                result = response.json()
                models = [m['id'] for m in result.get('data', [])]
        else:
            # Default: return common model names
            models = ['gpt-3.5-turbo', 'gpt-4', 'gpt-4-turbo']

        return jsonify({'models': models})
    except Exception as e:
        print(f"[ERROR] Fetch models failed: {e}")
        return jsonify({'error': f'Failed to fetch models: {str(e)}'}), 500

# ============ Model API Endpoints ============

@app.route('/api/models', methods=['GET'])
def get_models():
    models = db.get_all_models()
    return jsonify(models)

@app.route('/api/models', methods=['POST'])
def add_model():
    data = request.json
    try:
        # Get provider info
        provider = db.get_provider(data['provider_id'])
        if not provider:
            return jsonify({'error': 'Provider not found'}), 404

        model_id = db.add_model(
            name=data['name'],
            provider_id=data['provider_id'],
            model_name=data['model_name'],
            initial_capital=float(data.get('initial_capital', 100000))
        )

        model = db.get_model(model_id)
        
        # Get provider info
        provider = db.get_provider(model['provider_id'])
        if not provider:
            return jsonify({'error': 'Provider not found'}), 404
        
        # Infer provider type from provider name
        provider_type = infer_provider_type(provider['name'], provider['api_url'])
        
        trading_engines[model_id] = TradingEngine(
            model_id=model_id,
            db=db,
            market_fetcher=market_fetcher,
            ai_trader=AITrader(
                provider_type=provider_type,
                api_key=provider['api_key'],
                api_url=provider['api_url'],
                model_name=model['model_name']
            ),
            trade_fee_rate=TRADE_FEE_RATE
        )
        print(f"[INFO] Model {model_id} ({data['name']}) initialized")

        return jsonify({'id': model_id, 'message': 'Model added successfully'})

    except Exception as e:
        print(f"[ERROR] Failed to add model: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/models/<int:model_id>', methods=['DELETE'])
def delete_model(model_id):
    try:
        model = db.get_model(model_id)
        model_name = model['name'] if model else f"ID-{model_id}"
        
        db.delete_model(model_id)
        if model_id in trading_engines:
            del trading_engines[model_id]
        
        print(f"[INFO] Model {model_id} ({model_name}) deleted")
        return jsonify({'message': 'Model deleted successfully'})
    except Exception as e:
        print(f"[ERROR] Delete model {model_id} failed: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/models/<int:model_id>/portfolio', methods=['GET'])
def get_portfolio(model_id):
    prices_data = market_fetcher.get_current_prices(['BTC', 'ETH', 'SOL', 'BNB', 'XRP', 'DOGE'])
    current_prices = {coin: prices_data[coin]['price'] for coin in prices_data}
    
    portfolio = db.get_portfolio(model_id, current_prices)
    account_value = db.get_account_value_history(model_id, limit=100)
    
    return jsonify({
        'portfolio': portfolio,
        'account_value_history': account_value
    })

@app.route('/api/models/<int:model_id>/trades', methods=['GET'])
def get_trades(model_id):
    limit = request.args.get('limit', 50, type=int)
    trades = db.get_trades(model_id, limit=limit)
    return jsonify(trades)

@app.route('/api/models/<int:model_id>/conversations', methods=['GET'])
def get_conversations(model_id):
    limit = request.args.get('limit', 20, type=int)
    conversations = db.get_conversations(model_id, limit=limit)
    return jsonify(conversations)

@app.route('/api/aggregated/portfolio', methods=['GET'])
def get_aggregated_portfolio():
    """Get aggregated portfolio data across all models"""
    prices_data = market_fetcher.get_current_prices(['BTC', 'ETH', 'SOL', 'BNB', 'XRP', 'DOGE'])
    current_prices = {coin: prices_data[coin]['price'] for coin in prices_data}

    # Get aggregated data
    models = db.get_all_models()
    total_portfolio = {
        'total_value': 0,
        'cash': 0,
        'positions_value': 0,
        'realized_pnl': 0,
        'unrealized_pnl': 0,
        'initial_capital': 0,
        'positions': []
    }

    all_positions = {}

    for model in models:
        portfolio = db.get_portfolio(model['id'], current_prices)
        if portfolio:
            total_portfolio['total_value'] += portfolio.get('total_value', 0)
            total_portfolio['cash'] += portfolio.get('cash', 0)
            total_portfolio['positions_value'] += portfolio.get('positions_value', 0)
            total_portfolio['realized_pnl'] += portfolio.get('realized_pnl', 0)
            total_portfolio['unrealized_pnl'] += portfolio.get('unrealized_pnl', 0)
            total_portfolio['initial_capital'] += portfolio.get('initial_capital', 0)

            # Aggregate positions by coin and side
            for pos in portfolio.get('positions', []):
                key = f"{pos['coin']}_{pos['side']}"
                if key not in all_positions:
                    all_positions[key] = {
                        'coin': pos['coin'],
                        'side': pos['side'],
                        'quantity': 0,
                        'avg_price': 0,
                        'total_cost': 0,
                        'leverage': pos['leverage'],
                        'current_price': pos['current_price'],
                        'pnl': 0
                    }

                # Weighted average calculation
                current_pos = all_positions[key]
                current_cost = current_pos['quantity'] * current_pos['avg_price']
                new_cost = pos['quantity'] * pos['avg_price']
                total_quantity = current_pos['quantity'] + pos['quantity']

                if total_quantity > 0:
                    current_pos['avg_price'] = (current_cost + new_cost) / total_quantity
                    current_pos['quantity'] = total_quantity
                    current_pos['total_cost'] = current_cost + new_cost
                    current_pos['pnl'] = (pos['current_price'] - current_pos['avg_price']) * total_quantity

    total_portfolio['positions'] = list(all_positions.values())

    # Get multi-model chart data
    chart_data = db.get_multi_model_chart_data(limit=100)

    return jsonify({
        'portfolio': total_portfolio,
        'chart_data': chart_data,
        'model_count': len(models)
    })

@app.route('/api/models/chart-data', methods=['GET'])
def get_models_chart_data():
    """Get chart data for all models"""
    limit = request.args.get('limit', 100, type=int)
    chart_data = db.get_multi_model_chart_data(limit=limit)
    return jsonify(chart_data)

@app.route('/api/market/prices', methods=['GET'])
def get_market_prices():
    coins = ['BTC', 'ETH', 'SOL', 'BNB', 'XRP', 'DOGE']
    prices = market_fetcher.get_current_prices(coins)
    return jsonify(prices)

@app.route('/api/market/prices/realtime', methods=['GET'])
def get_realtime_prices():
    """Get real-time prices from WebSocket cache"""
    coins = ['BTC', 'ETH', 'SOL', 'BNB', 'XRP', 'DOGE']
    
    # If WebSocket has data, use it; otherwise fall back to REST API
    if realtime_prices:
        result = {}
        for coin in coins:
            if coin in realtime_prices:
                result[coin] = {
                    'price': realtime_prices[coin]['price'],
                    'change_24h': realtime_prices[coin]['change_24h'],
                    'volume_24h': realtime_prices[coin].get('volume_24h', 0),
                    'source': 'websocket'
                }
            else:
                # Fallback to REST API for this coin
                rest_prices = market_fetcher.get_current_prices([coin])
                if coin in rest_prices:
                    result[coin] = rest_prices[coin]
                    result[coin]['source'] = 'rest'
        return jsonify(result)
    else:
        # WebSocket not ready yet, use REST API
        prices = market_fetcher.get_current_prices(coins)
        for coin in prices:
            prices[coin]['source'] = 'rest'
        return jsonify(prices)

@app.route('/api/market/stream')
def stream_prices():
    """Server-Sent Events endpoint for real-time price streaming"""
    from flask import Response
    
    def generate():
        """Generate price updates as Server-Sent Events"""
        last_sent = {}
        
        while True:
            try:
                # Check if we have new WebSocket data
                if realtime_prices:
                    # Only send if prices have changed
                    changed = False
                    for coin, data in realtime_prices.items():
                        if coin not in last_sent or last_sent[coin] != data['price']:
                            changed = True
                            last_sent[coin] = data['price']
                    
                    if changed:
                        yield f"data: {json.dumps(realtime_prices)}\n\n"
                else:
                    # Fallback to REST API
                    coins = ['BTC', 'ETH', 'SOL', 'BNB', 'XRP', 'DOGE']
                    prices = market_fetcher.get_current_prices(coins)
                    yield f"data: {json.dumps(prices)}\n\n"
                
                time.sleep(1)  # Update every second
            except GeneratorExit:
                break
            except Exception as e:
                print(f"[ERROR] SSE stream error: {e}")
                break
    
    return Response(generate(), mimetype='text/event-stream')

# ============ Portfolio Advisor API Endpoints ============

@app.route('/api/portfolio/analyze', methods=['POST'])
def analyze_portfolio():
    """Analyze user portfolio and provide recommendations"""
    try:
        data = request.json
        portfolio_data = data.get('portfolio', [])
        provider_id = data.get('provider_id')
        
        if not portfolio_data:
            return jsonify({'error': 'Portfolio data is required'}), 400
        
        if not provider_id:
            return jsonify({'error': 'Provider ID is required'}), 400
        
        # Get provider info
        provider = db.get_provider(provider_id)
        if not provider:
            return jsonify({'error': 'Provider not found'}), 404
        
        # Get market data for portfolio symbols
        symbols = list(set([holding['symbol'] for holding in portfolio_data]))
        market_data = market_fetcher.get_current_prices(symbols)
        
        # Auto-fill current prices if not provided
        for holding in portfolio_data:
            if 'current_price' not in holding or holding['current_price'] is None:
                symbol = holding['symbol']
                if symbol in market_data:
                    holding['current_price'] = market_data[symbol]['price']
                else:
                    return jsonify({'error': f'Price not found for {symbol}'}), 400
        
        # Initialize PortfolioAdvisor
        advisor = PortfolioAdvisor(
            api_key=provider['api_key'],
            api_url=provider['api_url'],
            model_name=data.get('model_name', provider['models'].split(',')[0].strip())
        )
        
        # Analyze portfolio
        analysis = advisor.analyze_portfolio(portfolio_data, market_data)
        
        # Save snapshot and analysis
        user_id = data.get('user_id', 'default')
        snapshot_id = db.save_portfolio_snapshot(user_id, portfolio_data)
        analysis_id = db.save_portfolio_analysis(
            snapshot_id, 
            provider_id, 
            advisor.model_name, 
            analysis
        )
        
        return jsonify({
            'success': True,
            'snapshot_id': snapshot_id,
            'analysis_id': analysis_id,
            'analysis': analysis
        })
        
    except Exception as e:
        print(f"[ERROR] Portfolio analysis failed: {e}")
        import traceback
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/portfolio/save', methods=['POST'])
def save_portfolio():
    """Save portfolio snapshot without analysis"""
    try:
        data = request.json
        portfolio_data = data.get('portfolio', [])
        user_id = data.get('user_id', 'default')
        
        if not portfolio_data:
            return jsonify({'error': 'Portfolio data is required'}), 400
        
        # Auto-fill current prices from market data
        symbols = list(set([holding['symbol'] for holding in portfolio_data]))
        market_data = market_fetcher.get_current_prices(symbols)
        
        for holding in portfolio_data:
            if 'current_price' not in holding or holding['current_price'] is None:
                symbol = holding['symbol']
                if symbol in market_data:
                    holding['current_price'] = market_data[symbol]['price']
        
        snapshot_id = db.save_portfolio_snapshot(user_id, portfolio_data)
        
        return jsonify({
            'success': True,
            'snapshot_id': snapshot_id,
            'message': 'Portfolio saved successfully'
        })
        
    except Exception as e:
        print(f"[ERROR] Save portfolio failed: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/portfolio/history', methods=['GET'])
def get_portfolio_history():
    """Get portfolio analysis history"""
    try:
        user_id = request.args.get('user_id', 'default')
        limit = request.args.get('limit', 10, type=int)
        
        history = db.get_portfolio_history(user_id, limit)
        
        return jsonify({
            'success': True,
            'history': history
        })
        
    except Exception as e:
        print(f"[ERROR] Get portfolio history failed: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/models/<int:model_id>/execute', methods=['POST'])
def execute_trading(model_id):
    if model_id not in trading_engines:
        model = db.get_model(model_id)
        if not model:
            return jsonify({'error': 'Model not found'}), 404

        # Get provider info
        provider = db.get_provider(model['provider_id'])
        if not provider:
            return jsonify({'error': 'Provider not found'}), 404

        # Infer provider type from provider name
        provider_type = infer_provider_type(provider['name'], provider['api_url'])
        
        trading_engines[model_id] = TradingEngine(
            model_id=model_id,
            db=db,
            market_fetcher=market_fetcher,
            ai_trader=AITrader(
                provider_type=provider_type,
                api_key=provider['api_key'],
                api_url=provider['api_url'],
                model_name=model['model_name']
            ),
            trade_fee_rate=TRADE_FEE_RATE
        )
    
    try:
        result = trading_engines[model_id].execute_trading_cycle()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def trading_loop():
    print("[INFO] Trading loop started")
    
    while auto_trading:
        try:
            if not trading_engines:
                time.sleep(30)
                continue
            
            print(f"\n{'='*60}")
            print(f"[CYCLE] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"[INFO] Active models: {len(trading_engines)}")
            print(f"{'='*60}")
            
            for model_id, engine in list(trading_engines.items()):
                try:
                    print(f"\n[EXEC] Model {model_id}")
                    result = engine.execute_trading_cycle()
                    
                    if result.get('success'):
                        print(f"[OK] Model {model_id} completed")
                        if result.get('executions'):
                            for exec_result in result['executions']:
                                signal = exec_result.get('signal', 'unknown')
                                coin = exec_result.get('coin', 'unknown')
                                msg = exec_result.get('message', '')
                                if signal != 'hold':
                                    print(f"  [TRADE] {coin}: {msg}")
                    else:
                        error = result.get('error', 'Unknown error')
                        print(f"[WARN] Model {model_id} failed: {error}")
                        
                except Exception as e:
                    print(f"[ERROR] Model {model_id} exception: {e}")
                    import traceback
                    print(traceback.format_exc())
                    continue
            
            print(f"\n{'='*60}")
            print(f"[SLEEP] Waiting 3 minutes for next cycle")
            print(f"{'='*60}\n")
            
            time.sleep(180)
            
        except Exception as e:
            print(f"\n[CRITICAL] Trading loop error: {e}")
            import traceback
            print(traceback.format_exc())
            print("[RETRY] Retrying in 60 seconds\n")
            time.sleep(60)
    
    print("[INFO] Trading loop stopped")

@app.route('/api/leaderboard', methods=['GET'])
def get_leaderboard():
    models = db.get_all_models()
    leaderboard = []
    
    prices_data = market_fetcher.get_current_prices(['BTC', 'ETH', 'SOL', 'BNB', 'XRP', 'DOGE'])
    current_prices = {coin: prices_data[coin]['price'] for coin in prices_data}
    
    for model in models:
        portfolio = db.get_portfolio(model['id'], current_prices)
        account_value = portfolio.get('total_value', model['initial_capital'])
        returns = ((account_value - model['initial_capital']) / model['initial_capital']) * 100
        
        leaderboard.append({
            'model_id': model['id'],
            'model_name': model['name'],
            'account_value': account_value,
            'returns': returns,
            'initial_capital': model['initial_capital']
        })
    
    leaderboard.sort(key=lambda x: x['returns'], reverse=True)
    return jsonify(leaderboard)

@app.route('/api/settings', methods=['GET'])
def get_settings():
    """Get system settings"""
    try:
        settings = db.get_settings()
        return jsonify(settings)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/settings', methods=['PUT'])
def update_settings():
    """Update system settings"""
    try:
        data = request.json
        trading_frequency_minutes = int(data.get('trading_frequency_minutes', 60))
        trading_fee_rate = float(data.get('trading_fee_rate', 0.001))

        success = db.update_settings(trading_frequency_minutes, trading_fee_rate)

        if success:
            return jsonify({'success': True, 'message': 'Settings updated successfully'})
        else:
            return jsonify({'success': False, 'error': 'Failed to update settings'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/version', methods=['GET'])
def get_version():
    """Get current version information"""
    return jsonify({
        'current_version': __version__,
        'github_repo': GITHUB_REPO_URL,
        'latest_release_url': LATEST_RELEASE_URL
    })

@app.route('/api/check-update', methods=['GET'])
def check_update():
    """Check for GitHub updates"""
    try:
        import requests

        # Get latest release from GitHub
        headers = {
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'Xion/1.0'
        }

        # Try to get latest release
        try:
            response = requests.get(
                f"https://api.github.com/repos/{__github_owner__}/{__repo__}/releases/latest",
                headers=headers,
                timeout=5
            )

            if response.status_code == 200:
                release_data = response.json()
                latest_version = release_data.get('tag_name', '').lstrip('v')
                release_url = release_data.get('html_url', '')
                release_notes = release_data.get('body', '')

                # Compare versions
                is_update_available = compare_versions(latest_version, __version__) > 0

                return jsonify({
                    'update_available': is_update_available,
                    'current_version': __version__,
                    'latest_version': latest_version,
                    'release_url': release_url,
                    'release_notes': release_notes,
                    'repo_url': GITHUB_REPO_URL
                })
            else:
                # If API fails, still return current version info
                return jsonify({
                    'update_available': False,
                    'current_version': __version__,
                    'error': 'Could not check for updates'
                })
        except Exception as e:
            print(f"[WARN] GitHub API error: {e}")
            return jsonify({
                'update_available': False,
                'current_version': __version__,
                'error': 'Network error checking updates'
            })

    except Exception as e:
        print(f"[ERROR] Check update failed: {e}")
        return jsonify({
            'update_available': False,
            'current_version': __version__,
            'error': str(e)
        }), 500

def compare_versions(version1, version2):
    """Compare two version strings.

    Returns:
        1 if version1 > version2
        0 if version1 == version2
        -1 if version1 < version2
    """
    def normalize(v):
        # Extract numeric parts from version string
        parts = re.findall(r'\d+', v)
        # Pad with zeros to make them comparable
        return [int(p) for p in parts]

    v1_parts = normalize(version1)
    v2_parts = normalize(version2)

    # Pad shorter version with zeros
    max_len = max(len(v1_parts), len(v2_parts))
    v1_parts.extend([0] * (max_len - len(v1_parts)))
    v2_parts.extend([0] * (max_len - len(v2_parts)))

    # Compare
    if v1_parts > v2_parts:
        return 1
    elif v1_parts < v2_parts:
        return -1
    else:
        return 0

def init_trading_engines():
    try:
        models = db.get_all_models()

        if not models:
            print("[WARN] No trading models found")
            return

        print(f"\n[INIT] Initializing trading engines...")
        for model in models:
            model_id = model['id']
            model_name = model['name']

            try:
                # Get provider info
                provider = db.get_provider(model['provider_id'])
                if not provider:
                    print(f"  [WARN] Model {model_id} ({model_name}): Provider not found")
                    continue

                # Infer provider type from provider name
                provider_type = infer_provider_type(provider['name'], provider['api_url'])
                
                trading_engines[model_id] = TradingEngine(
                    model_id=model_id,
                    db=db,
                    market_fetcher=market_fetcher,
                    ai_trader=AITrader(
                        provider_type=provider_type,
                        api_key=provider['api_key'],
                        api_url=provider['api_url'],
                        model_name=model['model_name']
                    ),
                    trade_fee_rate=TRADE_FEE_RATE
                )
                print(f"  [OK] Model {model_id} ({model_name})")
            except Exception as e:
                print(f"  [ERROR] Model {model_id} ({model_name}): {e}")
                continue

        print(f"[INFO] Initialized {len(trading_engines)} engine(s)\n")

    except Exception as e:
        print(f"[ERROR] Init engines failed: {e}\n")

def init_hardcoded_model():
    """Initialize hardcoded AI model if not exists"""
    try:
        # Configuration - Load from environment variables
        PROVIDER_NAME = os.getenv('PROVIDER_NAME', 'OpenAI')
        API_URL = os.getenv('API_URL', 'https://api.openai.com/v1')
        API_KEY = os.getenv('API_KEY')
        AVAILABLE_MODELS = os.getenv('AVAILABLE_MODELS', 'gpt-4,gpt-4-turbo,gpt-3.5-turbo')
        MODEL_NAME = os.getenv('MODEL_NAME', 'AI Trader 1')
        MODEL_TO_USE = os.getenv('MODEL_TO_USE', 'gpt-4-turbo')
        INITIAL_CAPITAL = float(os.getenv('INITIAL_CAPITAL', '100000'))
        
        # Validate required API key
        if not API_KEY:
            print("[WARN] API_KEY not found in .env file. Skipping model initialization.")
            return
        
        # Check if provider already exists
        providers = db.get_all_providers()
        provider_id = None
        
        for p in providers:
            if p['name'] == PROVIDER_NAME:
                provider_id = p['id']
                print(f"[INFO] Using existing provider: {PROVIDER_NAME} (ID: {provider_id})")
                break
        
        if not provider_id:
            provider_id = db.add_provider(
                name=PROVIDER_NAME,
                api_url=API_URL,
                api_key=API_KEY,
                models=AVAILABLE_MODELS
            )
            print(f"[INFO] Created provider: {PROVIDER_NAME} (ID: {provider_id})")
        
        # Check if model already exists
        models = db.get_all_models()
        model_exists = any(m['name'] == MODEL_NAME for m in models)
        
        if not model_exists:
            model_id = db.add_model(
                name=MODEL_NAME,
                provider_id=provider_id,
                model_name=MODEL_TO_USE,
                initial_capital=INITIAL_CAPITAL
            )
            print(f"[INFO] Created model: {MODEL_NAME} (ID: {model_id})")
        else:
            print(f"[INFO] Model '{MODEL_NAME}' already exists")
            
    except Exception as e:
        print(f"[ERROR] Failed to initialize hardcoded model: {e}")
        import traceback
        print(traceback.format_exc())

if __name__ == '__main__':
    import webbrowser
    import os
    
    print("\n" + "=" * 60)
    print("Xion - Starting...")
    print("=" * 60)
    print("[INFO] Initializing database...")
    
    db.init_db()
    init_hardcoded_model()
    
    print("[INFO] Database initialized")
    print("[INFO] Initializing trading engines...")
    
    init_trading_engines()
    
    if auto_trading:
        trading_thread = threading.Thread(target=trading_loop, daemon=True)
        trading_thread.start()
        print("[INFO] Auto-trading enabled")
    
    # Load server configuration from environment variables
    FLASK_HOST = os.getenv('FLASK_HOST', '0.0.0.0')
    FLASK_PORT = int(os.getenv('FLASK_PORT', '5000'))
    FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    AUTO_OPEN_BROWSER = os.getenv('AUTO_OPEN_BROWSER', 'True').lower() == 'true'
    
    print("\n" + "=" * 60)
    print("Xion is running!")
    print(f"Server: http://localhost:{FLASK_PORT}")
    print("Press Ctrl+C to stop")
    print("=" * 60 + "\n")
    
    # Auto-open browser if enabled
    if AUTO_OPEN_BROWSER:
        def open_browser():
            time.sleep(1.5)  # Wait for server to start
            url = f"http://localhost:{FLASK_PORT}"
            try:
                webbrowser.open(url)
                print(f"[INFO] Browser opened: {url}")
            except Exception as e:
                print(f"[WARN] Could not open browser: {e}")
        
        browser_thread = threading.Thread(target=open_browser, daemon=True)
        browser_thread.start()
    
    app.run(debug=FLASK_DEBUG, host=FLASK_HOST, port=FLASK_PORT, use_reloader=False)
