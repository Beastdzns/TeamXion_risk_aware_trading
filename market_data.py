"""
Market data module - Binance API integration
"""
import requests
import time
from typing import Dict, List

class MarketDataFetcher:
    """Fetch real-time market data from Binance API"""
    
    def __init__(self):
        self.binance_base_url = "https://api.binance.com/api/v3"
        self.coingecko_base_url = "https://api.coingecko.com/api/v3"
        
        # Binance symbol mapping
        self.binance_symbols = {
            'BTC': 'BTCUSDT',
            'ETH': 'ETHUSDT',
            'SOL': 'SOLUSDT',
            'BNB': 'BNBUSDT',
            'XRP': 'XRPUSDT',
            'DOGE': 'DOGEUSDT'
        }
        
        # CoinGecko mapping for technical indicators
        self.coingecko_mapping = {
            'BTC': 'bitcoin',
            'ETH': 'ethereum',
            'SOL': 'solana',
            'BNB': 'binancecoin',
            'XRP': 'ripple',
            'DOGE': 'dogecoin'
        }
        
        self._cache = {}
        self._cache_time = {}
        self._cache_duration = 300  # Cache for 5 minutes (avoid rate limits)
        self._last_successful_prices = {}  # Store last known good prices
    
    def get_current_prices(self, coins: List[str]) -> Dict[str, float]:
        """Get current prices from Binance API with fallback and retry logic"""
        # Check cache
        cache_key = 'prices_' + '_'.join(sorted(coins))
        if cache_key in self._cache:
            if time.time() - self._cache_time[cache_key] < self._cache_duration:
                return self._cache[cache_key]
        
        prices = {}
        
        # Try Binance API with retry
        for attempt in range(2):
            try:
                # Batch fetch Binance 24h ticker data
                symbols = [self.binance_symbols.get(coin) for coin in coins if coin in self.binance_symbols]
                
                if symbols:
                    # Build symbols parameter
                    symbols_param = '[' + ','.join([f'"{s}"' for s in symbols]) + ']'
                    
                    response = requests.get(
                        f"{self.binance_base_url}/ticker/24hr",
                        params={'symbols': symbols_param},
                        timeout=10
                    )
                    response.raise_for_status()
                    data = response.json()
                    
                    # Parse data
                    for item in data:
                        symbol = item['symbol']
                        # Find corresponding coin
                        for coin, binance_symbol in self.binance_symbols.items():
                            if binance_symbol == symbol:
                                prices[coin] = {
                                    'price': float(item['lastPrice']),
                                    'change_24h': float(item['priceChangePercent'])
                                }
                                break
                
                # Success! Update cache and last successful prices
                if prices:
                    self._cache[cache_key] = prices
                    self._cache_time[cache_key] = time.time()
                    self._last_successful_prices.update(prices)
                    return prices
                    
            except Exception as e:
                if attempt == 0:
                    print(f"[WARN] Binance API attempt {attempt+1} failed: {e}, retrying...")
                    time.sleep(1)
                else:
                    print(f"[ERROR] Binance API failed after retries: {e}")
        
        # Fallback to CoinGecko
        print("[INFO] Trying CoinGecko fallback...")
        prices = self._get_prices_from_coingecko(coins)
        
        # If CoinGecko also failed, use last successful prices if available
        if not prices or all(p.get('price', 0) == 0 for p in prices.values()):
            print("[WARN] All APIs failed, using last successful prices if available")
            if self._last_successful_prices:
                # Return last known good prices for requested coins
                prices = {coin: self._last_successful_prices[coin] 
                         for coin in coins 
                         if coin in self._last_successful_prices}
                if prices:
                    print(f"[INFO] Returned {len(prices)} cached prices from previous successful fetch")
                    return prices
            print("[ERROR] No cached prices available, returning zeros")
            return {coin: {'price': 0, 'change_24h': 0} for coin in coins}
        
        # Update cache and last successful prices
        if prices:
            self._cache[cache_key] = prices
            self._cache_time[cache_key] = time.time()
            self._last_successful_prices.update(prices)
        
        return prices
    
    def _get_prices_from_coingecko(self, coins: List[str]) -> Dict[str, float]:
        """Fallback: Fetch prices from CoinGecko"""
        try:
            coin_ids = [self.coingecko_mapping.get(coin, coin.lower()) for coin in coins]
            
            response = requests.get(
                f"{self.coingecko_base_url}/simple/price",
                params={
                    'ids': ','.join(coin_ids),
                    'vs_currencies': 'usd',
                    'include_24hr_change': 'true'
                },
                timeout=15
            )
            response.raise_for_status()
            data = response.json()
            
            prices = {}
            for coin in coins:
                coin_id = self.coingecko_mapping.get(coin, coin.lower())
                if coin_id in data:
                    prices[coin] = {
                        'price': data[coin_id]['usd'],
                        'change_24h': data[coin_id].get('usd_24h_change', 0)
                    }
            
            return prices
        except Exception as e:
            print(f"[ERROR] CoinGecko fallback also failed: {e}")
            return {}
    
    def get_market_data(self, coin: str) -> Dict:
        """Get detailed market data from CoinGecko"""
        coin_id = self.coingecko_mapping.get(coin, coin.lower())
        
        try:
            response = requests.get(
                f"{self.coingecko_base_url}/coins/{coin_id}",
                params={'localization': 'false', 'tickers': 'false', 'community_data': 'false'},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            market_data = data.get('market_data', {})
            
            return {
                'current_price': market_data.get('current_price', {}).get('usd', 0),
                'market_cap': market_data.get('market_cap', {}).get('usd', 0),
                'total_volume': market_data.get('total_volume', {}).get('usd', 0),
                'price_change_24h': market_data.get('price_change_percentage_24h', 0),
                'price_change_7d': market_data.get('price_change_percentage_7d', 0),
                'high_24h': market_data.get('high_24h', {}).get('usd', 0),
                'low_24h': market_data.get('low_24h', {}).get('usd', 0),
            }
        except Exception as e:
            print(f"[ERROR] Failed to get market data for {coin}: {e}")
            return {}
    
    def get_historical_prices(self, coin: str, days: int = 7) -> List[Dict]:
        """Get historical prices from CoinGecko"""
        coin_id = self.coingecko_mapping.get(coin, coin.lower())
        
        try:
            response = requests.get(
                f"{self.coingecko_base_url}/coins/{coin_id}/market_chart",
                params={'vs_currency': 'usd', 'days': days},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            prices = []
            for price_data in data.get('prices', []):
                prices.append({
                    'timestamp': price_data[0],
                    'price': price_data[1]
                })
            
            return prices
        except Exception as e:
            print(f"[ERROR] Failed to get historical prices for {coin}: {e}")
            return []
    
    def calculate_technical_indicators(self, coin: str) -> Dict:
        """Calculate technical indicators"""
        historical = self.get_historical_prices(coin, days=14)
        
        if not historical or len(historical) < 14:
            return {}
        
        prices = [p['price'] for p in historical]
        
        # Simple Moving Average
        sma_7 = sum(prices[-7:]) / 7 if len(prices) >= 7 else prices[-1]
        sma_14 = sum(prices[-14:]) / 14 if len(prices) >= 14 else prices[-1]
        
        # Simple RSI calculation
        changes = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [c if c > 0 else 0 for c in changes]
        losses = [-c if c < 0 else 0 for c in changes]
        
        avg_gain = sum(gains[-14:]) / 14 if gains else 0
        avg_loss = sum(losses[-14:]) / 14 if losses else 0
        
        if avg_loss == 0:
            rsi = 100
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
        
        return {
            'sma_7': sma_7,
            'sma_14': sma_14,
            'rsi_14': rsi,
            'current_price': prices[-1],
            'price_change_7d': ((prices[-1] - prices[0]) / prices[0]) * 100 if prices[0] > 0 else 0
        }

    def get_asset_price(self, symbol: str) -> float:
        """
        Get current price for a single asset
        
        Args:
            symbol: Asset symbol (e.g., 'BTC', 'ETH')
        
        Returns:
            Current price as float, or 0 if fetch fails
        """
        try:
            # Use existing get_current_prices method with single symbol
            result = self.get_current_prices([symbol])
            
            if symbol in result:
                return result[symbol]['price']
            else:
                print(f"[WARN] Price not found for {symbol}")
                return 0.0
                
        except Exception as e:
            print(f"[ERROR] Failed to get price for {symbol}: {e}")
            return 0.0
    
    def get_multiple_prices(self, symbols_list: List[str]) -> Dict[str, float]:
        """
        Batch fetch prices for multiple assets (for portfolio)
        
        Args:
            symbols_list: List of asset symbols (e.g., ['BTC', 'ETH', 'SOL'])
        
        Returns:
            Dict mapping symbol to price: {'BTC': 45000.0, 'ETH': 3000.0, ...}
        """
        try:
            # Remove duplicates and empty strings
            symbols = list(set([s.strip().upper() for s in symbols_list if s and s.strip()]))
            
            if not symbols:
                return {}
            
            # Use existing get_current_prices method
            result = self.get_current_prices(symbols)
            
            # Extract just the prices into simple dict
            prices_dict = {}
            for symbol, data in result.items():
                if isinstance(data, dict) and 'price' in data:
                    prices_dict[symbol] = data['price']
                else:
                    prices_dict[symbol] = 0.0
            
            # Add 0 for any symbols that weren't found
            for symbol in symbols:
                if symbol not in prices_dict:
                    print(f"[WARN] Price not found for {symbol}, using 0")
                    prices_dict[symbol] = 0.0
            
            return prices_dict
            
        except Exception as e:
            print(f"[ERROR] Failed to get multiple prices: {e}")
            # Return dict with 0 prices for all symbols
            return {symbol: 0.0 for symbol in symbols_list}

