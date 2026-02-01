class TradingApp {
    constructor() {
        this.currentModelId = null;
        this.isAggregatedView = false;
        this.chart = null;
        this.refreshIntervals = {
            market: null,
            portfolio: null,
            trades: null
        };
        this.isChinese = this.detectLanguage();
        this.init();
    }

    detectLanguage() {
        // Check if the page language is Chinese or if user's language includes Chinese
        const lang = document.documentElement.lang || navigator.language || navigator.userLanguage;
        return lang.toLowerCase().includes('zh');
    }

    formatPnl(value, isPnl = false) {
        // Format profit/loss value based on language preference
        if (!isPnl || value === 0) {
            return `$${Math.abs(value).toFixed(2)}`;
        }

        const absValue = Math.abs(value);
        const formatted = `$${absValue.toFixed(2)}`;

        if (this.isChinese) {
            // Chinese convention: red for profit (positive), show + sign
            if (value > 0) {
                return `+${formatted}`;
            } else {
                return `-${formatted}`;
            }
        } else {
            if (value > 0) {
                return `+${formatted}`;
            }
            return formatted;
        }
    }

    getPnlClass(value, isPnl = false) {
        if (!isPnl || value === 0) {
            return '';
        }

        if (value > 0) {
            return this.isChinese ? 'positive' : 'positive';
        } else if (value < 0) {
            // In Chinese: negative (loss) should not be red
            return this.isChinese ? 'negative' : 'negative';
        }
        return '';
    }

    init() {
        this.initEventListeners();
        this.loadModels();
        this.loadMarketPrices();
        this.startRefreshCycles();
        // Check for updates after initialization (with delay)
        setTimeout(() => this.checkForUpdates(true), 3000);
    }

    initEventListeners() {
        // Update Modal
        document.getElementById('checkUpdateBtn').addEventListener('click', () => this.checkForUpdates());
        document.getElementById('closeUpdateModalBtn').addEventListener('click', () => this.hideUpdateModal());
        document.getElementById('dismissUpdateBtn').addEventListener('click', () => this.dismissUpdate());

        // API Provider Modal
        document.getElementById('addApiProviderBtn').addEventListener('click', () => this.showApiProviderModal());
        document.getElementById('closeApiProviderModalBtn').addEventListener('click', () => this.hideApiProviderModal());
        document.getElementById('cancelApiProviderBtn').addEventListener('click', () => this.hideApiProviderModal());
        document.getElementById('saveApiProviderBtn').addEventListener('click', () => this.saveApiProvider());
        document.getElementById('fetchModelsBtn').addEventListener('click', () => this.fetchModels());

        // Model Modal
        document.getElementById('addModelBtn').addEventListener('click', () => this.showModal());
        document.getElementById('closeModalBtn').addEventListener('click', () => this.hideModal());
        document.getElementById('cancelBtn').addEventListener('click', () => this.hideModal());
        document.getElementById('submitBtn').addEventListener('click', () => this.submitModel());
        document.getElementById('modelProvider').addEventListener('change', (e) => this.updateModelOptions(e.target.value));

        // Refresh
        document.getElementById('refreshBtn').addEventListener('click', () => this.refresh());

        // Settings Modal
        document.getElementById('settingsBtn').addEventListener('click', () => this.showSettingsModal());
        document.getElementById('closeSettingsModalBtn').addEventListener('click', () => this.hideSettingsModal());
        document.getElementById('cancelSettingsBtn').addEventListener('click', () => this.hideSettingsModal());
        document.getElementById('saveSettingsBtn').addEventListener('click', () => this.saveSettings());

        // Tabs
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.switchTab(e.target.dataset.tab));
        });

        // Portfolio Advisor Modal
        document.getElementById('portfolioAdvisorBtn').addEventListener('click', () => this.showPortfolioAdvisorModal());
        document.getElementById('closePortfolioAdvisorModalBtn').addEventListener('click', () => this.hidePortfolioAdvisorModal());
        document.getElementById('cancelPortfolioAdvisorBtn').addEventListener('click', () => this.hidePortfolioAdvisorModal());
        document.getElementById('addPortfolioRowBtn').addEventListener('click', () => this.addPortfolioRow());
        document.getElementById('analyzePortfolioBtn').addEventListener('click', () => this.submitPortfolioAnalysis());
        document.getElementById('backToInputBtn').addEventListener('click', () => this.backToPortfolioInput());
        document.getElementById('portfolioAnalysisProvider').addEventListener('change', (e) => this.updatePortfolioModelOptions(e.target.value));

        // Chart Filter Buttons
        document.querySelectorAll('.filter-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.switchChartPeriod(e.target.dataset.period));
        });
    }

    async loadModels() {
        try {
            const response = await fetch('/api/models');
            const models = await response.json();
            this.renderModels(models);

            // Initialize with aggregated view if no model is selected
            if (models.length > 0 && !this.currentModelId && !this.isAggregatedView) {
                this.showAggregatedView();
            }
        } catch (error) {
            console.error('Failed to load models:', error);
        }
    }

    renderModels(models) {
        const container = document.getElementById('modelList');

        if (models.length === 0) {
            container.innerHTML = '<div class="empty-state">No models yet</div>';
            return;
        }

        // Add aggregated view option at the top
        let html = `
            <div class="model-item ${this.isAggregatedView ? 'active' : ''}"
                 onclick="app.showAggregatedView()">
                <div class="model-name">
                    <i class="bi bi-bar-chart-fill"></i> Aggregated View
                </div>
                <div class="model-info">
                    <span>All models summary</span>
                </div>
            </div>
        `;

        // Add individual models
        html += models.map(model => `
            <div class="model-item ${model.id === this.currentModelId && !this.isAggregatedView ? 'active' : ''}"
                 onclick="app.selectModel(${model.id})">
                <div class="model-name">${model.name}</div>
                <div class="model-info">
                    <span>${model.model_name}</span>
                    <span class="model-delete" onclick="event.stopPropagation(); app.deleteModel(${model.id})">
                        <i class="bi bi-trash"></i>
                    </span>
                </div>
            </div>
        `).join('');

        container.innerHTML = html;
    }

    async showAggregatedView() {
        this.isAggregatedView = true;
        this.currentModelId = null;
        this.loadModels();
        await this.loadAggregatedData();
        this.hideTabsInAggregatedView();
    }

    async selectModel(modelId) {
        this.currentModelId = modelId;
        this.isAggregatedView = false;
        this.loadModels();
        await this.loadModelData();
        this.showTabsInSingleModelView();
    }

    async loadModelData() {
        if (!this.currentModelId) return;

        try {
            const [portfolio, trades, conversations] = await Promise.all([
                fetch(`/api/models/${this.currentModelId}/portfolio`).then(r => r.json()),
                fetch(`/api/models/${this.currentModelId}/trades?limit=50`).then(r => r.json()),
                fetch(`/api/models/${this.currentModelId}/conversations?limit=20`).then(r => r.json())
            ]);

            this.updateStats(portfolio.portfolio, false);
            this.updateSingleModelChart(portfolio.account_value_history, portfolio.portfolio.total_value);
            this.updatePositions(portfolio.portfolio.positions, false);
            this.updateTrades(trades);
            this.updateConversations(conversations);
        } catch (error) {
            console.error('Failed to load model data:', error);
        }
    }

    async loadAggregatedData() {
        try {
            const response = await fetch('/api/aggregated/portfolio');
            const data = await response.json();

            this.updateStats(data.portfolio, true);
            this.updateMultiModelChart(data.chart_data);
            // Skip positions, trades, and conversations in aggregated view
            this.hideTabsInAggregatedView();
        } catch (error) {
            console.error('Failed to load aggregated data:', error);
        }
    }

    hideTabsInAggregatedView() {
        // Hide the entire tabbed content section in aggregated view
        const contentCard = document.querySelector('.content-card .card-tabs').parentElement;
        if (contentCard) {
            contentCard.style.display = 'none';
        }
    }

    showTabsInSingleModelView() {
        // Show the tabbed content section in single model view
        const contentCard = document.querySelector('.content-card .card-tabs').parentElement;
        if (contentCard) {
            contentCard.style.display = 'block';
        }
    }

    updateStats(portfolio, isAggregated = false) {
        const stats = [
            { value: portfolio.total_value || 0, isPnl: false },
            { value: portfolio.cash || 0, isPnl: false },
            { value: portfolio.realized_pnl || 0, isPnl: true },
            { value: portfolio.unrealized_pnl || 0, isPnl: true }
        ];

        document.querySelectorAll('.stat-value').forEach((el, index) => {
            if (stats[index]) {
                el.textContent = this.formatPnl(stats[index].value, stats[index].isPnl);
                el.className = `stat-value ${this.getPnlClass(stats[index].value, stats[index].isPnl)}`;
            }
        });

        // Update title for aggregated view
        const titleElement = document.querySelector('.account-info h2');
        if (titleElement) {
            if (isAggregated) {
                titleElement.innerHTML = '<i class="bi bi-bar-chart-fill"></i> Aggregated Account Overview';
            } else {
                titleElement.innerHTML = '<i class="bi bi-wallet2"></i> Account Information';
            }
        }
    }

    updateSingleModelChart(history, currentValue) {
        const chartDom = document.getElementById('accountChart');

        // Dispose existing chart to avoid state pollution
        if (this.chart) {
            this.chart.dispose();
        }

        this.chart = echarts.init(chartDom);
        window.addEventListener('resize', () => {
            if (this.chart) {
                this.chart.resize();
            }
        });

        const data = history.reverse().map(h => ({
            time: new Date(h.timestamp.replace(' ', 'T') + 'Z').toLocaleTimeString('en-IN', {
                timeZone: 'Asia/Kolkata',
                hour: '2-digit',
                minute: '2-digit'
            }),
            value: h.total_value
        }));

        if (currentValue !== undefined && currentValue !== null) {
            const now = new Date();
            const currentTime = now.toLocaleTimeString('en-IN', {
                timeZone: 'Asia/Kolkata',
                hour: '2-digit',
                minute: '2-digit'
            });
            data.push({
                time: currentTime,
                value: currentValue
            });
        }

        const option = {
            grid: {
                left: '60',
                right: '20',
                bottom: '40',
                top: '20',
                containLabel: false
            },
            xAxis: {
                type: 'category',
                boundaryGap: false,
                data: data.map(d => d.time),
                axisLine: { lineStyle: { color: '#e5e6eb' } },
                axisLabel: { color: '#86909c', fontSize: 11 }
            },
            yAxis: {
                type: 'value',
                scale: true,
                axisLine: { lineStyle: { color: '#e5e6eb' } },
                axisLabel: {
                    color: '#86909c',
                    fontSize: 11,
                    formatter: (value) => `$${value.toLocaleString()}`
                },
                splitLine: { lineStyle: { color: '#f2f3f5' } }
            },
            series: [{
                type: 'line',
                data: data.map(d => d.value),
                smooth: true,
                symbol: 'none',
                lineStyle: { color: '#3370ff', width: 2 },
                areaStyle: {
                    color: {
                        type: 'linear',
                        x: 0, y: 0, x2: 0, y2: 1,
                        colorStops: [
                            { offset: 0, color: 'rgba(51, 112, 255, 0.2)' },
                            { offset: 1, color: 'rgba(51, 112, 255, 0)' }
                        ]
                    }
                }
            }],
            tooltip: {
                trigger: 'axis',
                backgroundColor: 'rgba(255, 255, 255, 0.95)',
                borderColor: '#e5e6eb',
                borderWidth: 1,
                textStyle: { color: '#1d2129' },
                formatter: (params) => {
                    const value = params[0].value;
                    return `${params[0].axisValue}<br/>Account Value: $${value.toFixed(2)}`;
                }
            }
        };

        this.chart.setOption(option);

        setTimeout(() => {
            if (this.chart) {
                this.chart.resize();
            }
        }, 100);
    }

    updateMultiModelChart(chartData) {
        const chartDom = document.getElementById('accountChart');

        // Dispose existing chart to avoid state pollution
        if (this.chart) {
            this.chart.dispose();
        }

        this.chart = echarts.init(chartDom);
        window.addEventListener('resize', () => {
            if (this.chart) {
                this.chart.resize();
            }
        });

        if (!chartData || chartData.length === 0) {
            // Show empty state for multi-model chart
            this.chart.setOption({
                title: {
                    text: 'No model data yet',
                    left: 'center',
                    top: 'center',
                    textStyle: { color: '#86909c', fontSize: 14 }
                },
                xAxis: { show: false },
                yAxis: { show: false },
                series: []
            });
            return;
        }

        // Colors for different models
        const colors = [
            '#3370ff', '#ff6b35', '#00b96b', '#722ed1', '#fa8c16',
            '#eb2f96', '#13c2c2', '#faad14', '#f5222d', '#52c41a'
        ];

        // Prepare time axis - get all timestamps and sort them chronologically
        const allTimestamps = new Set();
        chartData.forEach(model => {
            model.data.forEach(point => {
                allTimestamps.add(point.timestamp);
            });
        });

        // Convert to array and sort by timestamp (not string sort)
        const timeAxis = Array.from(allTimestamps).sort((a, b) => {
            const timeA = new Date(a.replace(' ', 'T') + 'Z').getTime();
            const timeB = new Date(b.replace(' ', 'T') + 'Z').getTime();
            return timeA - timeB;
        });

        // Format time labels for display
        const formattedTimeAxis = timeAxis.map(timestamp => {
            return new Date(timestamp.replace(' ', 'T') + 'Z').toLocaleTimeString('en-IN', {
                timeZone: 'Asia/Kolkata',
                hour: '2-digit',
                minute: '2-digit'
            });
        });

        // Prepare series data for each model
        const series = chartData.map((model, index) => {
            const color = colors[index % colors.length];

            // Create data points aligned with time axis
            const dataPoints = timeAxis.map(time => {
                const point = model.data.find(p => p.timestamp === time);
                return point ? point.value : null;
            });

            return {
                name: model.model_name,
                type: 'line',
                data: dataPoints,
                smooth: true,
                symbol: 'circle',
                symbolSize: 4,
                lineStyle: { color: color, width: 2 },
                itemStyle: { color: color },
                connectNulls: true  // Connect points even with null values
            };
        });

        const option = {
            title: {
                text: 'Model Performance Comparison',
                left: 'center',
                top: 10,
                textStyle: { color: '#1d2129', fontSize: 16, fontWeight: 'normal' }
            },
            grid: {
                left: '60',
                right: '20',
                bottom: '80',
                top: '50',
                containLabel: false
            },
            xAxis: {
                type: 'category',
                boundaryGap: false,
                data: formattedTimeAxis,
                axisLine: { lineStyle: { color: '#e5e6eb' } },
                axisLabel: { color: '#86909c', fontSize: 11, rotate: 45 }
            },
            yAxis: {
                type: 'value',
                scale: true,
                axisLine: { lineStyle: { color: '#e5e6eb' } },
                axisLabel: {
                    color: '#86909c',
                    fontSize: 11,
                    formatter: (value) => `$${value.toLocaleString()}`
                },
                splitLine: { lineStyle: { color: '#f2f3f5' } }
            },
            legend: {
                data: chartData.map(model => model.model_name),
                bottom: 10,
                itemGap: 20,
                textStyle: { color: '#1d2129', fontSize: 12 }
            },
            series: series,
            tooltip: {
                trigger: 'axis',
                backgroundColor: 'rgba(255, 255, 255, 0.95)',
                borderColor: '#e5e6eb',
                borderWidth: 1,
                textStyle: { color: '#1d2129' },
                formatter: (params) => {
                    let result = `${params[0].axisValue}<br/>`;
                    params.forEach(param => {
                        if (param.value !== null) {
                            result += `${param.marker}${param.seriesName}: $${param.value.toFixed(2)}<br/>`;
                        }
                    });
                    return result;
                }
            }
        };

        this.chart.setOption(option);

        setTimeout(() => {
            if (this.chart) {
                this.chart.resize();
            }
        }, 100);
    }

    updatePositions(positions, isAggregated = false) {
        const tbody = document.getElementById('positionsBody');

        if (positions.length === 0) {
            if (isAggregated) {
                tbody.innerHTML = '<tr><td colspan="7" class="empty-state">No positions in aggregated view</td></tr>';
            } else {
                tbody.innerHTML = '<tr><td colspan="7" class="empty-state">No positions</td></tr>';
            }
            return;
        }

        tbody.innerHTML = positions.map(pos => {
            const sideClass = pos.side === 'long' ? 'badge-long' : 'badge-short';
            const sideText = pos.side === 'long' ? 'Long' : 'Short';

            const currentPrice = pos.current_price !== null && pos.current_price !== undefined
                ? `$${pos.current_price.toFixed(2)}`
                : '-';

            let pnlDisplay = '-';
            let pnlClass = '';
            if (pos.pnl !== undefined && pos.pnl !== 0) {
                pnlDisplay = this.formatPnl(pos.pnl, true);
                pnlClass = this.getPnlClass(pos.pnl, true);
            }

            return `
                <tr>
                    <td><strong>${pos.coin}</strong></td>
                    <td><span class="badge ${sideClass}">${sideText}</span></td>
                    <td>${pos.quantity.toFixed(4)}</td>
                    <td>$${pos.avg_price.toFixed(2)}</td>
                    <td>${currentPrice}</td>
                    <td>${pos.leverage}x</td>
                    <td class="${pnlClass}"><strong>${pnlDisplay}</strong></td>
                </tr>
            `;
        }).join('');

        // Update positions title for aggregated view
        const positionsTitle = document.querySelector('#positionsTab .card-header h3');
        if (positionsTitle) {
            if (isAggregated) {
                positionsTitle.innerHTML = '<i class="bi bi-collection"></i> Aggregated Positions';
            } else {
                positionsTitle.innerHTML = '<i class="bi bi-briefcase"></i> Current Positions';
            }
        }
    }

    updateTrades(trades) {
        const tbody = document.getElementById('tradesBody');

        if (trades.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="empty-state">No trades yet</td></tr>';
            return;
        }

        tbody.innerHTML = trades.map(trade => {
            const signalMap = {
                'buy_to_enter': { badge: 'badge-buy', text: 'Long' },
                'sell_to_enter': { badge: 'badge-sell', text: 'Short' },
                'close_position': { badge: 'badge-close', text: 'Close' }
            };
            const signal = signalMap[trade.signal] || { badge: '', text: trade.signal };
            const pnlDisplay = this.formatPnl(trade.pnl, true);
            const pnlClass = this.getPnlClass(trade.pnl, true);

            return `
                <tr>
                    <td>${new Date(trade.timestamp.replace(' ', 'T') + 'Z').toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' })}</td>
                    <td><strong>${trade.coin}</strong></td>
                    <td><span class="badge ${signal.badge}">${signal.text}</span></td>
                    <td>${trade.quantity.toFixed(4)}</td>
                    <td>$${trade.price.toFixed(2)}</td>
                    <td class="${pnlClass}">${pnlDisplay}</td>
                    <td>$${trade.fee.toFixed(2)}</td>
                </tr>
            `;
        }).join('');
    }

    updateConversations(conversations) {
        const container = document.getElementById('conversationsBody');

        if (conversations.length === 0) {
            container.innerHTML = '<div class="empty-state">No conversation history</div>';
            return;
        }

        container.innerHTML = conversations.map(conv => `
            <div class="conversation-item">
                <div class="conversation-time">${new Date(conv.timestamp.replace(' ', 'T') + 'Z').toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' })}</div>
                <div class="conversation-content">${conv.ai_response}</div>
            </div>
        `).join('');
    }

    async loadMarketPrices() {
        try {
            // Use WebSocket-cached real-time prices for instant updates
            const response = await fetch('/api/market/prices/realtime');
            const prices = await response.json();

            // Log source for debugging (optional - can be removed later)
            const sources = Object.values(prices).map(p => p.source).filter(s => s);
            if (sources.length > 0) {
                const wsCount = sources.filter(s => s === 'websocket').length;
                if (wsCount > 0) {
                    console.log(`[Realtime] ${wsCount}/${sources.length} prices from WebSocket`);
                }
            }

            this.renderMarketPrices(prices);
        } catch (error) {
            console.error('Failed to load market prices:', error);
        }
    }

    renderMarketPrices(prices) {
        const container = document.getElementById('marketPrices');

        container.innerHTML = Object.entries(prices).map(([coin, data]) => {
            const changeClass = data.change_24h >= 0 ? 'positive' : 'negative';
            const changeIcon = data.change_24h >= 0 ? '↑' : '↓';

            return `
                <div class="price-item">
                    <div>
                        <div class="price-symbol">${coin}</div>
                        <div class="price-change ${changeClass}">${changeIcon} ${Math.abs(data.change_24h).toFixed(2)}%</div>
                    </div>
                    <div class="price-value">$${data.price.toFixed(2)}</div>
                </div>
            `;
        }).join('');
    }

    switchTab(tabName) {
        document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));

        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
        document.getElementById(`${tabName}Tab`).classList.add('active');
    }

    switchChartPeriod(period) {
        // Update active button
        document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
        document.querySelector(`[data-period="${period}"]`).classList.add('active');

        // Note: Currently the chart shows all available data
        // In a future update, this could filter the data by time period
        // For now, we just update the UI to show the button is clickable
        console.log(`Chart period switched to: ${period}`);

        // Optionally reload the chart data with the new period
        // This would require backend support to filter by time period
    }

    // API Provider Methods
    async showApiProviderModal() {
        this.loadProviders();
        document.getElementById('apiProviderModal').classList.add('show');
    }

    hideApiProviderModal() {
        document.getElementById('apiProviderModal').classList.remove('show');
        this.clearApiProviderForm();
    }

    clearApiProviderForm() {
        document.getElementById('providerName').value = '';
        document.getElementById('providerApiUrl').value = '';
        document.getElementById('providerApiKey').value = '';
        document.getElementById('availableModels').value = '';
    }

    async saveApiProvider() {
        const data = {
            name: document.getElementById('providerName').value.trim(),
            api_url: document.getElementById('providerApiUrl').value.trim(),
            api_key: document.getElementById('providerApiKey').value,
            models: document.getElementById('availableModels').value.trim()
        };

        if (!data.name || !data.api_url || !data.api_key) {
            alert('Please fill in all required fields');
            return;
        }

        try {
            const response = await fetch('/api/providers', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            if (response.ok) {
                this.hideApiProviderModal();
                this.loadProviders();
                alert('API provider saved successfully');
            }
        } catch (error) {
            console.error('Failed to save provider:', error);
            alert('Failed to save API provider');
        }
    }

    async fetchModels() {
        const apiUrl = document.getElementById('providerApiUrl').value.trim();
        const apiKey = document.getElementById('providerApiKey').value;

        if (!apiUrl || !apiKey) {
            alert('Please enter API URL and key first');
            return;
        }

        const fetchBtn = document.getElementById('fetchModelsBtn');
        const originalText = fetchBtn.innerHTML;
        fetchBtn.innerHTML = '<i class="bi bi-arrow-clockwise spin"></i> Fetching...';
        fetchBtn.disabled = true;

        try {
            const response = await fetch('/api/providers/models', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ api_url: apiUrl, api_key: apiKey })
            });

            if (response.ok) {
                const data = await response.json();
                if (data.models && data.models.length > 0) {
                    document.getElementById('availableModels').value = data.models.join(', ');
                    alert(`Successfully fetched ${data.models.length} models`);
                } else {
                    alert('No models found, please enter manually');
                }
            } else {
                alert('Failed to fetch models, please check API URL and key');
            }
        } catch (error) {
            console.error('Failed to fetch models:', error);
            alert('Failed to fetch model list');
        } finally {
            fetchBtn.innerHTML = originalText;
            fetchBtn.disabled = false;
        }
    }

    async loadProviders() {
        try {
            const response = await fetch('/api/providers');
            const providers = await response.json();
            this.providers = providers;
            this.renderProviders(providers);
            this.updateModelProviderSelect(providers);
        } catch (error) {
            console.error('Failed to load providers:', error);
        }
    }

    renderProviders(providers) {
        const container = document.getElementById('providerList');

        if (providers.length === 0) {
            container.innerHTML = '<div class="empty-state">No API providers yet</div>';
            return;
        }

        container.innerHTML = providers.map(provider => {
            const models = provider.models ? provider.models.split(',').map(m => m.trim()) : [];
            const modelsHtml = models.map(model => `<span class="model-tag">${model}</span>`).join('');

            return `
                <div class="provider-item">
                    <div class="provider-info">
                        <div class="provider-name">${provider.name}</div>
                        <div class="provider-url">${provider.api_url}</div>
                        <div class="provider-models">${modelsHtml}</div>
                    </div>
                    <div class="provider-actions">
                        <span class="provider-delete" onclick="app.deleteProvider(${provider.id})" title="Delete">
                            <i class="bi bi-trash"></i>
                        </span>
                    </div>
                </div>
            `;
        }).join('');
    }

    updateModelProviderSelect(providers) {
        const select = document.getElementById('modelProvider');
        const currentValue = select.value;

        select.innerHTML = '<option value="">Please select an API provider</option>';
        providers.forEach(provider => {
            const option = document.createElement('option');
            option.value = provider.id;
            option.textContent = provider.name;
            select.appendChild(option);
        });

        // Restore previous selection if still exists
        if (currentValue && providers.find(p => p.id == currentValue)) {
            select.value = currentValue;
            this.updateModelOptions(currentValue);
        }
    }

    updateModelOptions(providerId) {
        const modelSelect = document.getElementById('modelIdentifier');
        const providerSelect = document.getElementById('modelProvider');

        if (!providerId) {
            modelSelect.innerHTML = '<option value="">Please select an API provider</option>';
            return;
        }

        // Find the selected provider
        const provider = this.providers?.find(p => p.id == providerId);
        if (!provider || !provider.models) {
            modelSelect.innerHTML = '<option value="">This provider has no models</option>';
            return;
        }

        const models = provider.models.split(',').map(m => m.trim()).filter(m => m);
        modelSelect.innerHTML = '<option value="">Please select a model</option>';
        models.forEach(model => {
            const option = document.createElement('option');
            option.value = model;
            option.textContent = model;
            modelSelect.appendChild(option);
        });
    }

    async deleteProvider(providerId) {
        if (!confirm('Are you sure you want to delete this API provider?')) return;

        try {
            const response = await fetch(`/api/providers/${providerId}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                this.loadProviders();
            }
        } catch (error) {
            console.error('Failed to delete provider:', error);
        }
    }

    showModal() {
        this.loadProviders().then(() => {
            document.getElementById('addModelModal').classList.add('show');
        });
    }

    hideModal() {
        document.getElementById('addModelModal').classList.remove('show');
    }

    async submitModel() {
        const providerId = document.getElementById('modelProvider').value;
        const modelName = document.getElementById('modelIdentifier').value;
        const displayName = document.getElementById('modelName').value.trim();
        const initialCapital = parseFloat(document.getElementById('initialCapital').value);

        if (!providerId || !modelName || !displayName) {
            alert('Please fill in all required fields');
            return;
        }

        try {
            const response = await fetch('/api/models', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    provider_id: providerId,
                    model_name: modelName,
                    name: displayName,
                    initial_capital: initialCapital
                })
            });

            if (response.ok) {
                this.hideModal();
                this.loadModels();
                this.clearForm();
            }
        } catch (error) {
            console.error('Failed to add model:', error);
            alert('Failed to add model');
        }
    }

    async deleteModel(modelId) {
        if (!confirm('Are you sure you want to delete this model?')) return;

        try {
            const response = await fetch(`/api/models/${modelId}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                if (this.currentModelId === modelId) {
                    this.currentModelId = null;
                    this.showAggregatedView();
                } else {
                    this.loadModels();
                }
            }
        } catch (error) {
            console.error('Failed to delete model:', error);
        }
    }

    clearForm() {
        document.getElementById('modelProvider').value = '';
        document.getElementById('modelIdentifier').value = '';
        document.getElementById('modelName').value = '';
        document.getElementById('initialCapital').value = '100000';
    }

    async refresh() {
        await Promise.all([
            this.loadModels(),
            this.loadMarketPrices(),
            this.isAggregatedView ? this.loadAggregatedData() : this.loadModelData()
        ]);
    }

    startRefreshCycles() {
        this.refreshIntervals.market = setInterval(() => {
            this.loadMarketPrices();
        }, 2000);

        this.refreshIntervals.portfolio = setInterval(() => {
            if (this.isAggregatedView || this.currentModelId) {
                if (this.isAggregatedView) {
                    this.loadAggregatedData();
                } else {
                    this.loadModelData();
                }
            }
        }, 10000);
    }

    stopRefreshCycles() {
        Object.values(this.refreshIntervals).forEach(interval => {
            if (interval) clearInterval(interval);
        });
    }

    async showSettingsModal() {
        try {
            const response = await fetch('/api/settings');
            const settings = await response.json();

            document.getElementById('tradingFrequency').value = settings.trading_frequency_minutes;
            document.getElementById('tradingFeeRate').value = settings.trading_fee_rate;

            document.getElementById('settingsModal').classList.add('show');
        } catch (error) {
            console.error('Failed to load settings:', error);
            alert('Failed to load settings');
        }
    }

    hideSettingsModal() {
        document.getElementById('settingsModal').classList.remove('show');
    }

    async saveSettings() {
        const tradingFrequency = parseInt(document.getElementById('tradingFrequency').value);
        const tradingFeeRate = parseFloat(document.getElementById('tradingFeeRate').value);

        if (!tradingFrequency || tradingFrequency < 1 || tradingFrequency > 1440) {
            alert('Please enter a valid trading frequency (1-1440 minutes)');
            return;
        }

        if (tradingFeeRate < 0 || tradingFeeRate > 0.01) {
            alert('Please enter a valid trading fee rate (0-0.01)');
            return;
        }

        try {
            const response = await fetch('/api/settings', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    trading_frequency_minutes: tradingFrequency,
                    trading_fee_rate: tradingFeeRate
                })
            });

            if (response.ok) {
                this.hideSettingsModal();
                alert('Settings saved successfully');
            } else {
                alert('Failed to save settings');
            }
        } catch (error) {
            console.error('Failed to save settings:', error);
            alert('Failed to save settings');
        }
    }

    // ============ Update Check Methods ============

    async checkForUpdates(silent = false) {
        try {
            const response = await fetch('/api/check-update');
            const data = await response.json();

            if (data.update_available) {
                this.showUpdateModal(data);
                this.showUpdateIndicator();
            } else if (!silent) {
                if (data.error) {
                    console.warn('Update check failed:', data.error);
                } else {
                    // Already on latest version
                    this.showUpdateIndicator(true);
                    setTimeout(() => this.hideUpdateIndicator(), 2000);
                }
            }
        } catch (error) {
            console.error('Failed to check for updates:', error);
            if (!silent) {
                alert('Failed to check for updates, please try again later');
            }
        }
    }

    showUpdateModal(data) {
        const modal = document.getElementById('updateModal');
        const currentVersion = document.getElementById('currentVersion');
        const latestVersion = document.getElementById('latestVersion');
        const releaseNotes = document.getElementById('releaseNotes');
        const githubLink = document.getElementById('githubLink');

        currentVersion.textContent = `v${data.current_version}`;
        latestVersion.textContent = `v${data.latest_version}`;
        githubLink.href = data.release_url || data.repo_url;

        // Format release notes
        if (data.release_notes) {
            releaseNotes.innerHTML = this.formatReleaseNotes(data.release_notes);
        } else {
            releaseNotes.innerHTML = '<p>No release notes available</p>';
        }

        modal.classList.add('show');
    }

    hideUpdateModal() {
        document.getElementById('updateModal').classList.remove('show');
    }

    dismissUpdate() {
        this.hideUpdateModal();
        // Hide indicator temporarily, check again in 24 hours
        this.hideUpdateIndicator();

        // Store dismissal timestamp in localStorage
        const tomorrow = new Date();
        tomorrow.setDate(tomorrow.getDate() + 1);
        localStorage.setItem('updateDismissedUntil', tomorrow.getTime().toString());
    }

    formatReleaseNotes(notes) {
        // Simple markdown-like formatting
        let formatted = notes
            .replace(/### (.*)/g, '<h3>$1</h3>')
            .replace(/## (.*)/g, '<h2>$1</h2>')
            .replace(/# (.*)/g, '<h1>$1</h1>')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`(.*?)`/g, '<code>$1</code>')
            .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>')
            .replace(/^-\s+(.*)/gm, '<li>$1</li>')
            .replace(/(<li>.*<\/li>)/gs, '<ul>$1</ul>')
            .replace(/\n\n/g, '</p><p>')
            .replace(/^(.*)/, '<p>$1')
            .replace(/(.*)$/, '$1</p>');

        // Clean up extra <p> tags around block elements
        formatted = formatted.replace(/<p>(<h\d+>.*<\/h\d+>)<\/p>/g, '$1');
        formatted = formatted.replace(/<p>(<ul>.*<\/ul>)<\/p>/g, '$1');

        return formatted;
    }

    showUpdateIndicator() {
        const indicator = document.getElementById('updateIndicator');
        // Check if dismissed recently
        const dismissedUntil = localStorage.getItem('updateDismissedUntil');
        if (dismissedUntil && Date.now() < parseInt(dismissedUntil)) {
            return;
        }
        indicator.style.display = 'block';
    }

    hideUpdateIndicator() {
        const indicator = document.getElementById('updateIndicator');
        indicator.style.display = 'none';
    }

    // ============ Portfolio Advisor Methods ============

    async showPortfolioAdvisorModal() {
        // Load providers for portfolio analysis
        await this.loadProvidersForPortfolio();

        // Initialize portfolio table with one row
        document.getElementById('portfolioInputSection').style.display = 'block';
        document.getElementById('portfolioResultsSection').style.display = 'none';

        // Setup event listeners for portfolio calculations
        this.setupPortfolioListeners();

        // Calculate initial values
        this.updatePortfolioCalculations();

        document.getElementById('portfolioAdvisorModal').classList.add('show');
    }

    hidePortfolioAdvisorModal() {
        document.getElementById('portfolioAdvisorModal').classList.remove('show');
    }

    async loadProvidersForPortfolio() {
        try {
            const response = await fetch('/api/providers');
            const providers = await response.json();
            this.portfolioProviders = providers;

            const select = document.getElementById('portfolioAnalysisProvider');
            select.innerHTML = '<option value="">Please select a provider</option>';

            providers.forEach(provider => {
                const option = document.createElement('option');
                option.value = provider.id;
                option.textContent = provider.name;
                select.appendChild(option);
            });
        } catch (error) {
            console.error('Failed to load providers:', error);
        }
    }

    updatePortfolioModelOptions(providerId) {
        const modelSelect = document.getElementById('portfolioAnalysisModel');

        if (!providerId) {
            modelSelect.innerHTML = '<option value="">Please select a provider first</option>';
            return;
        }

        const provider = this.portfolioProviders?.find(p => p.id == providerId);
        if (!provider || !provider.models) {
            modelSelect.innerHTML = '<option value="">This provider has no models</option>';
            return;
        }

        const models = provider.models.split(',').map(m => m.trim()).filter(m => m);
        modelSelect.innerHTML = '<option value="">Please select a model</option>';

        models.forEach(model => {
            const option = document.createElement('option');
            option.value = model;
            option.textContent = model;
            modelSelect.appendChild(option);
        });
    }

    addPortfolioRow() {
        const tbody = document.getElementById('portfolioTableBody');
        const newRow = document.createElement('tr');
        newRow.className = 'portfolio-input-row';
        newRow.innerHTML = `
            <td><input type="text" class="form-input portfolio-symbol" placeholder="ETH"></td>
            <td><input type="number" class="form-input portfolio-quantity" placeholder="0.0" step="0.0001"></td>
            <td><input type="number" class="form-input portfolio-cost" placeholder="0" step="0.01"></td>
            <td><input type="number" class="form-input portfolio-current" placeholder="Auto" step="0.01" readonly></td>
            <td class="portfolio-value">$0.00</td>
            <td class="portfolio-return">0.00%</td>
            <td>
                <button class="btn-icon btn-danger remove-portfolio-row" title="Remove">
                    <i class="bi bi-trash"></i>
                </button>
            </td>
        `;
        tbody.appendChild(newRow);

        // Add event listener to remove button
        newRow.querySelector('.remove-portfolio-row').addEventListener('click', () => {
            newRow.remove();
            this.updatePortfolioCalculations();
        });

        // Add input listeners
        this.setupPortfolioListeners();
    }

    setupPortfolioListeners() {
        // Add listeners to all portfolio inputs
        document.querySelectorAll('.portfolio-symbol, .portfolio-quantity, .portfolio-cost').forEach(input => {
            input.removeEventListener('input', () => this.updatePortfolioCalculations());
            input.addEventListener('input', () => this.updatePortfolioCalculations());
        });

        // Add listeners to remove buttons
        document.querySelectorAll('.remove-portfolio-row').forEach(btn => {
            btn.removeEventListener('click', null);
            btn.addEventListener('click', (e) => {
                e.target.closest('tr').remove();
                this.updatePortfolioCalculations();
            });
        });
    }

    async updatePortfolioCalculations() {
        const rows = document.querySelectorAll('.portfolio-input-row');
        let totalValue = 0;
        let totalCost = 0;

        // Collect symbols to fetch prices
        const symbols = [];
        rows.forEach(row => {
            const symbol = row.querySelector('.portfolio-symbol').value.trim().toUpperCase();
            if (symbol) symbols.push(symbol);
        });

        // Fetch current prices
        let prices = {};
        if (symbols.length > 0) {
            try {
                const response = await fetch('/api/market/prices');
                const marketData = await response.json();
                prices = marketData;
            } catch (error) {
                console.error('Failed to fetch prices:', error);
            }
        }

        // Update each row
        rows.forEach(row => {
            const symbol = row.querySelector('.portfolio-symbol').value.trim().toUpperCase();
            const quantity = parseFloat(row.querySelector('.portfolio-quantity').value) || 0;
            const costBasis = parseFloat(row.querySelector('.portfolio-cost').value) || 0;
            const currentPriceInput = row.querySelector('.portfolio-current');

            // Set current price
            let currentPrice = 0;
            if (symbol && prices[symbol]) {
                currentPrice = prices[symbol].price;
                currentPriceInput.value = currentPrice.toFixed(2);
            }

            // Calculate values
            const value = quantity * currentPrice;
            const cost = quantity * costBasis;
            const returnPct = cost > 0 ? ((currentPrice - costBasis) / costBasis * 100) : 0;

            // Update display
            row.querySelector('.portfolio-value').textContent = `$${value.toFixed(2)}`;

            const returnCell = row.querySelector('.portfolio-return');
            returnCell.textContent = `${returnPct >= 0 ? '+' : ''}${returnPct.toFixed(2)}%`;
            returnCell.className = 'portfolio-return ' + (returnPct >= 0 ? 'positive' : 'negative');

            totalValue += value;
            totalCost += cost;
        });

        // Update summary
        const totalReturnPct = totalCost > 0 ? ((totalValue - totalCost) / totalCost * 100) : 0;
        document.getElementById('portfolioTotalValue').textContent = `$${totalValue.toFixed(2)}`;
        document.getElementById('portfolioTotalCost').textContent = `$${totalCost.toFixed(2)}`;

        const returnEl = document.getElementById('portfolioTotalReturn');
        returnEl.textContent = `${totalReturnPct >= 0 ? '+' : ''}${totalReturnPct.toFixed(2)}%`;
        returnEl.className = 'summary-value ' + (totalReturnPct >= 0 ? 'positive' : 'negative');
    }

    async submitPortfolioAnalysis() {
        const providerId = document.getElementById('portfolioAnalysisProvider').value;
        const modelName = document.getElementById('portfolioAnalysisModel').value;

        if (!providerId) {
            alert('Please select an AI provider');
            return;
        }

        if (!modelName) {
            alert('Please select a model');
            return;
        }

        // Collect portfolio data
        const rows = document.querySelectorAll('.portfolio-input-row');
        const portfolio = [];

        rows.forEach(row => {
            const symbol = row.querySelector('.portfolio-symbol').value.trim().toUpperCase();
            const quantity = parseFloat(row.querySelector('.portfolio-quantity').value);
            const costBasis = parseFloat(row.querySelector('.portfolio-cost').value);
            const currentPrice = parseFloat(row.querySelector('.portfolio-current').value);

            if (symbol && quantity && costBasis) {
                portfolio.push({
                    symbol: symbol,
                    quantity: quantity,
                    cost_basis: costBasis,
                    current_price: currentPrice || null
                });
            }
        });

        if (portfolio.length === 0) {
            alert('Please add at least one asset to your portfolio');
            return;
        }

        // Show loading state
        const analyzeBtn = document.getElementById('analyzePortfolioBtn');
        const originalText = analyzeBtn.innerHTML;
        analyzeBtn.innerHTML = '<i class="bi bi-hourglass-split spin"></i> Analyzing...';
        analyzeBtn.disabled = true;

        try {
            const response = await fetch('/api/portfolio/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    portfolio: portfolio,
                    provider_id: providerId,
                    model_name: modelName,
                    user_id: 'default'
                })
            });

            if (response.ok) {
                const result = await response.json();
                this.displayAnalysisResults(result.analysis);
            } else {
                const error = await response.json();
                alert(`Analysis failed: ${error.error || 'Unknown error'}`);
            }
        } catch (error) {
            console.error('Failed to analyze portfolio:', error);
            alert('Failed to analyze portfolio. Please try again.');
        } finally {
            analyzeBtn.innerHTML = originalText;
            analyzeBtn.disabled = false;
        }
    }

    displayAnalysisResults(data) {
        // Hide input section, show results section
        document.getElementById('portfolioInputSection').style.display = 'none';
        document.getElementById('portfolioResultsSection').style.display = 'block';

        // Display risk score
        const riskScore = data.risk_score || 0;
        document.getElementById('riskScore').textContent = riskScore;
        const riskBar = document.getElementById('riskProgressBar');
        riskBar.style.width = `${riskScore}%`;
        riskBar.className = 'progress-bar ' + this.getRiskClass(riskScore);

        // Display diversification score
        const diversificationScore = data.diversification_score || 0;
        document.getElementById('diversificationScore').textContent = diversificationScore;
        const diversificationBar = document.getElementById('diversificationProgressBar');
        diversificationBar.style.width = `${diversificationScore}%`;
        diversificationBar.className = 'progress-bar ' + this.getDiversificationClass(diversificationScore);

        // Display recommendations
        const recommendationsList = document.getElementById('recommendationsList');
        if (data.recommendations && data.recommendations.length > 0) {
            recommendationsList.innerHTML = data.recommendations.map(rec => `
                <div class="recommendation-item">
                    <div class="recommendation-header">
                        <span class="recommendation-symbol">${rec.symbol}</span>
                        <span class="recommendation-action ${rec.action}">${rec.action.toUpperCase()}</span>
                    </div>
                    <div class="recommendation-body">
                        <div class="allocation-change">
                            <span>Current: ${rec.current_allocation?.toFixed(1) || 0}%</span>
                            <i class="bi bi-arrow-right"></i>
                            <span>Target: ${rec.target_allocation?.toFixed(1) || 0}%</span>
                        </div>
                        <div class="recommendation-reasoning">${rec.reasoning}</div>
                    </div>
                </div>
            `).join('');
        } else {
            recommendationsList.innerHTML = '<div class="empty-state">No rebalancing needed</div>';
        }

        // Display opportunities
        const opportunitiesList = document.getElementById('opportunitiesList');
        if (data.new_opportunities && data.new_opportunities.length > 0) {
            opportunitiesList.innerHTML = data.new_opportunities.map(opp => `
                <div class="opportunity-card">
                    <div class="opportunity-header">
                        <span class="opportunity-symbol">${opp.symbol}</span>
                        <span class="opportunity-confidence">Confidence: ${(opp.confidence * 100).toFixed(0)}%</span>
                    </div>
                    <div class="opportunity-body">
                        <div class="opportunity-allocation">Suggested Allocation: ${opp.allocation?.toFixed(1) || 0}%</div>
                        <div class="opportunity-rationale">${opp.rationale}</div>
                    </div>
                </div>
            `).join('');
        } else {
            opportunitiesList.innerHTML = '<div class="empty-state">No new opportunities identified</div>';
        }

        // Display AI reasoning
        document.getElementById('aiReasoning').innerHTML = `<p>${data.reasoning || 'No analysis provided'}</p>`;
    }

    getRiskClass(score) {
        if (score >= 70) return 'risk-high';
        if (score >= 40) return 'risk-medium';
        return 'risk-low';
    }

    getDiversificationClass(score) {
        if (score >= 70) return 'diversification-high';
        if (score >= 40) return 'diversification-medium';
        return 'diversification-low';
    }

    backToPortfolioInput() {
        document.getElementById('portfolioInputSection').style.display = 'block';
        document.getElementById('portfolioResultsSection').style.display = 'none';
    }
}

const app = new TradingApp();