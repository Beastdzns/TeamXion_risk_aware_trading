"""
WebSocket implementation for real-time crypto price updates
Uses Binance's FREE WebSocket API - no API key required!
"""

import asyncio
import websockets
import json
from typing import Dict, Callable, List
import threading

class PriceWebSocket:
    """Real-time price updates via Binance WebSocket (100% FREE)"""
    
    def __init__(self):
        self.ws_url = "wss://stream.binance.com:9443/ws"
        self.subscriptions = []
        self.callbacks = []
        self.running = False
        self.current_prices = {}
        
        # Symbol mapping
        self.symbols = {
            'BTC': 'btcusdt',
            'ETH': 'ethusdt',
            'SOL': 'solusdt',
            'BNB': 'bnbusdt',
            'XRP': 'xrpusdt',
            'DOGE': 'dogeusdt'
        }
    
    def subscribe_to_coins(self, coins: List[str]):
        """Subscribe to price updates for specific coins"""
        streams = []
        for coin in coins:
            if coin in self.symbols:
                symbol = self.symbols[coin]
                # Subscribe to ticker stream for real-time price
                streams.append(f"{symbol}@ticker")
        
        # Build WebSocket URL with streams
        if streams:
            self.ws_url = f"wss://stream.binance.com:9443/stream?streams={'/'.join(streams)}"
    
    def add_callback(self, callback: Callable):
        """Add callback function to be called on price updates"""
        self.callbacks.append(callback)
    
    async def _connect_and_listen(self):
        """Connect to WebSocket and listen for updates"""
        try:
            async with websockets.connect(self.ws_url) as websocket:
                print("[WebSocket] Connected to Binance WebSocket")
                
                while self.running:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=30)
                        data = json.loads(message)
                        
                        # Parse ticker data
                        if 'data' in data:
                            ticker = data['data']
                            symbol = ticker['s'].replace('USDT', '')
                            
                            # Find coin name
                            coin = None
                            for c, s in self.symbols.items():
                                if s == ticker['s'].lower():
                                    coin = c
                                    break
                            
                            if coin:
                                price_data = {
                                    'coin': coin,
                                    'price': float(ticker['c']),  # Current price
                                    'change_24h': float(ticker['P']),  # 24h change %
                                    'volume_24h': float(ticker['v']),  # 24h volume
                                    'high_24h': float(ticker['h']),  # 24h high
                                    'low_24h': float(ticker['l'])  # 24h low
                                }
                                
                                self.current_prices[coin] = price_data
                                
                                # Call all registered callbacks
                                for callback in self.callbacks:
                                    try:
                                        callback(price_data)
                                    except Exception as e:
                                        print(f"[WebSocket] Callback error: {e}")
                    
                    except asyncio.TimeoutError:
                        # Send ping to keep connection alive
                        await websocket.ping()
                    except Exception as e:
                        print(f"[WebSocket] Error receiving message: {e}")
                        break
        
        except Exception as e:
            print(f"[WebSocket] Connection error: {e}")
        finally:
            print("[WebSocket] Disconnected")
    
    def start(self, coins: List[str] = None):
        """Start WebSocket connection in background thread"""
        if coins:
            self.subscribe_to_coins(coins)
        
        self.running = True
        
        def run_async_loop():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._connect_and_listen())
        
        thread = threading.Thread(target=run_async_loop, daemon=True)
        thread.start()
        print("[WebSocket] Started in background thread")
    
    def stop(self):
        """Stop WebSocket connection"""
        self.running = False
    
    def get_current_prices(self) -> Dict:
        """Get latest prices from WebSocket"""
        return self.current_prices.copy()


# Example usage:
if __name__ == "__main__":
    def on_price_update(data):
        print(f"[PRICE UPDATE] {data['coin']}: ${data['price']:,.2f} ({data['change_24h']:+.2f}%)")
    
    ws = PriceWebSocket()
    ws.add_callback(on_price_update)
    ws.start(['BTC', 'ETH', 'SOL'])
    
    # Keep running
    try:
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        ws.stop()
        print("Stopped")
