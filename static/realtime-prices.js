// Real-Time Price Updates Enhancement
// Add this to your static/app.js to enable Server-Sent Events for live prices

class RealtimePriceManager {
    constructor() {
        this.eventSource = null;
        this.useSSE = false; // Set to true to enable SSE streaming
        this.realtimeEndpoint = '/api/market/prices/realtime';
        this.streamEndpoint = '/api/market/stream';
    }

    /**
     * Start real-time price updates using Server-Sent Events
     */
    startSSE(callback) {
        if (this.eventSource) {
            this.eventSource.close();
        }

        console.log('[Realtime] Starting SSE price stream...');
        this.eventSource = new EventSource(this.streamEndpoint);

        this.eventSource.onmessage = (event) => {
            try {
                const prices = JSON.parse(event.data);
                console.log('[Realtime] Received price update via SSE');
                callback(prices);
            } catch (error) {
                console.error('[Realtime] Error parsing SSE data:', error);
            }
        };

        this.eventSource.onerror = (error) => {
            console.error('[Realtime] SSE connection error:', error);
            // Reconnect after 5 seconds
            setTimeout(() => {
                console.log('[Realtime] Reconnecting SSE...');
                this.startSSE(callback);
            }, 5000);
        };

        this.eventSource.onopen = () => {
            console.log('[Realtime] SSE connection established');
        };
    }

    /**
     * Stop SSE streaming
     */
    stopSSE() {
        if (this.eventSource) {
            this.eventSource.close();
            this.eventSource = null;
            console.log('[Realtime] SSE stream stopped');
        }
    }

    /**
     * Fetch real-time prices from WebSocket cache (one-time fetch)
     */
    async fetchRealtimePrices() {
        try {
            const response = await fetch(this.realtimeEndpoint);
            const prices = await response.json();

            // Log source (websocket or rest)
            const sources = Object.values(prices).map(p => p.source).filter(s => s);
            if (sources.length > 0) {
                const wsCount = sources.filter(s => s === 'websocket').length;
                console.log(`[Realtime] Fetched prices: ${wsCount}/${sources.length} from WebSocket`);
            }

            return prices;
        } catch (error) {
            console.error('[Realtime] Error fetching realtime prices:', error);
            return null;
        }
    }
}

// Usage example:
// const realtimeManager = new RealtimePriceManager();
// 
// Option 1: Use SSE for continuous streaming
// realtimeManager.startSSE((prices) => {
//     updatePricesInUI(prices);
// });
//
// Option 2: Use faster polling with WebSocket-cached prices
// setInterval(async () => {
//     const prices = await realtimeManager.fetchRealtimePrices();
//     if (prices) updatePricesInUI(prices);
// }, 1000); // Update every second
