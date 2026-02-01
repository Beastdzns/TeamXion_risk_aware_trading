# XION TRADE: Continuous Decision-Making for Risk-Aware Trading

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/flask-3.0+-green.svg)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

> **⚠️ DISCLAIMER: Simulated trading platform for educational purposes only. DO NOT use with real assets.**

---

## 🎯 Problem Statement

Traditional trading systems treat each trade as an isolated buy/sell decision and stop reasoning after opening a position. In reality, markets move continuously, risk levels change dynamically, and capital gets locked while new opportunities emerge. Static rules lead to overexposure, missed rotations, and idle capital degrading portfolio performance.

**The Challenge**: Managing positions over time while respecting risk limits, capital availability, and changing market conditions—extremely difficult manually or with rigid systems.

---

## 🚀 Solution: Agentic AI Trading System

XION TRADE implements an **AI-powered agent** that actively manages open positions as market conditions evolve, emphasizing:

✅ **Continuous Risk Assessment** - Evaluates risk, capital, and returns for all open positions  
✅ **Adaptive Actions** - Recommends holding, reducing, exiting, or reallocating based on real-time data  
✅ **Portfolio-Level Management** - Balances multiple positions together, not individually  
✅ **Intelligent Reasoning** - Uses LLMs to analyze and explain every decision, not fixed indicators

**This is NOT a simple buy/sell bot—it's continuous, reasoning-based portfolio management.**

---

## ⚙️ Key Features

| Feature | Description |
|---------|-------------|
| **AI Portfolio Advisor** | LLM-powered analysis (OpenAI, DeepSeek, Claude) with natural language reasoning |
| **Real-Time Risk Management** | Tracks P&L, exposure levels, capital allocation, and risk thresholds |
| **Dynamic Position Management** | Holds, reduces, exits, or reallocates based on evolving conditions |
| **Multi-Model Engine** | Run multiple AI strategies simultaneously and compare performance |
| **Visual Analytics** | ECharts dashboard with portfolio tracking, P&L breakdown, trading history |
| **Configurable Environment** | Adjustable trading frequency (1-1440 min) and fee rates (simulates real costs) |

---

## 🛠️ Technology Stack

**Backend**: Python 3.9+, Flask, SQLite | **AI**: OpenAI/DeepSeek/Claude APIs  
**Frontend**: HTML5, CSS3, JavaScript, ECharts 5.4.3 | **Data**: CoinGecko API (real-time prices)

---

## 📦 Quick Start

```bash
# 1. Clone and install
git clone <repository-url>
cd tek2026
pip install -r requirements.txt

# 2. Configure API
cp config.example.py config.py
# Edit config.py with your AI API key

# 3. Run
python app.py
# Open http://localhost:5000
```

**Docker:**
```bash
docker-compose up -d  # Access at http://localhost:5000
```

---

## 📖 Usage

1. **Add API Provider** → Enter name, URL, API key → Fetch or input available models
2. **Add Trading Model** → Select provider & model → Set name & initial capital
3. **Configure Settings** → Adjust trading frequency & fee rate
4. **Monitor Dashboard** → View portfolio stats, P&L, AI reasoning logs

---

## 🎓 How It Works

**Continuous Decision Loop:**
```
Market Data Update → Risk Assessment → AI Analysis → 
Action Decision (Hold/Reduce/Exit/Reallocate) → Execute Trade → Update Portfolio
[Repeat at configured frequency]
```

**AI Decision Factors:** Current positions, market conditions, risk metrics, capital status, opportunity cost, trading fees

**Portfolio Strategy:** Risk balancing, capital efficiency, dynamic rebalancing, loss prevention, profit protection

---

## 📊 Project Structure

```
tek2026/
├── app.py                    # Flask web server
├── ai_trader.py              # AI trading logic & LLM integration
├── trading_engine.py         # Trade execution & position management
├── portfolio_advisor.py      # Portfolio analysis & recommendations
├── market_data.py            # Real-time price feeds
├── database.py               # SQLite operations
├── config.py                 # API configuration
├── static/                   # CSS, JS (app.js, style.css)
└── templates/                # HTML interface
```

---

## 🔧 Configuration

**Supported Models**: OpenAI (gpt-4, gpt-3.5-turbo), DeepSeek (deepseek-chat), Claude (via OpenRouter), any OpenAI-compatible API

**Key Parameters** (adjust in Settings or `config.py`):
- `TRADING_FREQUENCY`: AI decision interval (default: 60 min)
- `TRADING_FEE_RATE`: Commission per trade (default: 0.1%)
- `INITIAL_CAPITAL`: Starting capital (default: 10,000)

---

## 🔒 Privacy

All data stored locally in SQLite. No external tracking. API calls only to market data providers and your chosen AI service.

---

## ⚠️ Final Disclaimer

**FOR EDUCATIONAL USE ONLY.** Not financial advice. Not a real trading system. Do not use with real money. Developers assume no responsibility for financial losses. Consult qualified financial advisors before investing.

---

**XION TRADE - Intelligent, Adaptive, Risk-Aware Portfolio Management 🚀📈**
