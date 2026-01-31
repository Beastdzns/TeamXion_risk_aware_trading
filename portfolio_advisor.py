import json
from typing import Dict, List, Optional
from openai import OpenAI, APIConnectionError, APIError


class PortfolioAdvisor:
    """AI-powered portfolio analysis and rebalancing advisor"""
    
    def __init__(self, api_key: str, api_url: str, model_name: str):
        """
        Initialize Portfolio Advisor
        
        Args:
            api_key: API key for the AI provider
            api_url: Base URL for the API
            model_name: Model identifier (e.g., 'gpt-4', 'deepseek-chat')
        """
        self.api_key = api_key
        self.api_url = api_url
        self.model_name = model_name
    
    def analyze_portfolio(self, portfolio_data: List[Dict], market_data: Dict) -> Dict:
        """
        Analyze portfolio and provide recommendations
        
        Args:
            portfolio_data: List of holdings with structure:
                [{"symbol": "BTC", "quantity": 2.0, "cost_basis": 40000, "current_price": 45000}, ...]
            market_data: Market prices and indicators:
                {"BTC": {"price": 45000, "change_24h": 2.5, ...}, ...}
        
        Returns:
            Dict with analysis results:
                {
                    "risk_score": 72,
                    "diversification_score": 45,
                    "recommendations": [...],
                    "new_opportunities": [...],
                    "reasoning": "..."
                }
        """
        try:
            # Build analysis prompt
            prompt = self._build_analysis_prompt(portfolio_data, market_data)
            
            # Call AI
            response = self._call_openai_api(prompt)
            
            # Parse response
            analysis = self._parse_analysis_response(response)
            
            return analysis
            
        except Exception as e:
            print(f"[ERROR] Portfolio analysis failed: {e}")
            return {
                "risk_score": 0,
                "diversification_score": 0,
                "recommendations": [],
                "new_opportunities": [],
                "reasoning": f"Analysis failed: {str(e)}"
            }
    
    def _build_analysis_prompt(self, portfolio_data: List[Dict], market_data: Dict) -> str:
        """
        Build detailed prompt for portfolio analysis
        
        Args:
            portfolio_data: List of user holdings
            market_data: Current market information
        
        Returns:
            Formatted prompt string
        """
        # Calculate portfolio metrics
        total_value = sum(holding['quantity'] * holding['current_price'] 
                         for holding in portfolio_data)
        total_cost = sum(holding['quantity'] * holding['cost_basis'] 
                        for holding in portfolio_data)
        total_return_pct = ((total_value - total_cost) / total_cost * 100) if total_cost > 0 else 0
        
        prompt = f"""You are a professional portfolio manager analyzing a client's investment portfolio.

CURRENT PORTFOLIO:
Total Value: ${total_value:,.2f}
Total Cost Basis: ${total_cost:,.2f}
Overall Return: {total_return_pct:+.2f}%

HOLDINGS:
"""
        
        for holding in portfolio_data:
            value = holding['quantity'] * holding['current_price']
            cost = holding['quantity'] * holding['cost_basis']
            return_pct = ((holding['current_price'] - holding['cost_basis']) / holding['cost_basis'] * 100)
            allocation_pct = (value / total_value * 100) if total_value > 0 else 0
            
            prompt += f"""- {holding['symbol']}: {holding['quantity']:.4f} units
  Entry: ${holding['cost_basis']:,.2f} | Current: ${holding['current_price']:,.2f} | Return: {return_pct:+.2f}%
  Value: ${value:,.2f} ({allocation_pct:.1f}% of portfolio)
"""
        
        prompt += "\nMARKET DATA:\n"
        for symbol, data in market_data.items():
            prompt += f"{symbol}: ${data['price']:,.2f} ({data.get('change_24h', 0):+.2f}% 24h)\n"
        
        prompt += """
ANALYSIS TASKS:
1. Risk Assessment: Evaluate concentration risk, volatility exposure, correlation between assets
2. Diversification: Analyze asset allocation, sector exposure, geographic distribution
3. Rebalancing: Suggest optimal allocation adjustments to reduce risk and improve returns
4. Opportunities: Identify new investment opportunities that complement the portfolio

OUTPUT FORMAT (JSON only):
```json
{
  "risk_score": 0-100,
  "diversification_score": 0-100,
  "recommendations": [
    {
      "action": "reduce|increase|hold",
      "symbol": "BTC",
      "current_allocation": 60.0,
      "target_allocation": 40.0,
      "reasoning": "Reduce concentration risk"
    }
  ],
  "new_opportunities": [
    {
      "symbol": "ETH",
      "allocation": 10.0,
      "confidence": 0.75,
      "rationale": "Diversification into Layer-1 alternatives"
    }
  ],
  "reasoning": "Detailed analysis explaining risk factors, diversification gaps, and strategic recommendations"
}
```

Provide comprehensive analysis with actionable recommendations. Output JSON only.
"""
        
        return prompt
    
    def _call_openai_api(self, prompt: str) -> str:
        """
        Call OpenAI-compatible API
        
        Args:
            prompt: Analysis prompt
        
        Returns:
            AI response text
        """
        try:
            base_url = self.api_url.rstrip('/')
            if not base_url.endswith('/v1'):
                if '/v1' in base_url:
                    base_url = base_url.split('/v1')[0] + '/v1'
                else:
                    base_url = base_url + '/v1'
            
            client = OpenAI(
                api_key=self.api_key,
                base_url=base_url
            )
            
            response = client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a professional portfolio manager and investment advisor. Provide detailed analysis in JSON format only."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=2500
            )
            
            return response.choices[0].message.content
            
        except APIConnectionError as e:
            error_msg = f"API connection failed: {str(e)}"
            print(f"[ERROR] {error_msg}")
            raise Exception(error_msg)
        except APIError as e:
            error_msg = f"API error ({e.status_code}): {e.message}"
            print(f"[ERROR] {error_msg}")
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f"OpenAI API call failed: {str(e)}"
            print(f"[ERROR] {error_msg}")
            import traceback
            print(traceback.format_exc())
            raise Exception(error_msg)
    
    def _parse_analysis_response(self, response: str) -> Dict:
        """
        Parse AI response and extract structured analysis
        
        Args:
            response: Raw AI response text
        
        Returns:
            Parsed analysis dict with validated structure
        """
        response = response.strip()
        
        # Extract JSON from markdown code blocks if present
        if '```json' in response:
            response = response.split('```json')[1].split('```')[0]
        elif '```' in response:
            response = response.split('```')[1].split('```')[0]
        
        try:
            analysis = json.loads(response.strip())
            
            # Validate and set defaults for required fields
            result = {
                "risk_score": int(analysis.get("risk_score", 50)),
                "diversification_score": int(analysis.get("diversification_score", 50)),
                "recommendations": analysis.get("recommendations", []),
                "new_opportunities": analysis.get("new_opportunities", []),
                "reasoning": analysis.get("reasoning", "No detailed reasoning provided.")
            }
            
            # Validate score ranges
            result["risk_score"] = max(0, min(100, result["risk_score"]))
            result["diversification_score"] = max(0, min(100, result["diversification_score"]))
            
            return result
            
        except json.JSONDecodeError as e:
            print(f"[ERROR] JSON parse failed: {e}")
            print(f"[DATA] Response:\n{response}")
            
            # Return safe default structure
            return {
                "risk_score": 50,
                "diversification_score": 50,
                "recommendations": [],
                "new_opportunities": [],
                "reasoning": "Failed to parse AI response. Please try again."
            }
        except Exception as e:
            print(f"[ERROR] Response parsing failed: {e}")
            return {
                "risk_score": 0,
                "diversification_score": 0,
                "recommendations": [],
                "new_opportunities": [],
                "reasoning": f"Parsing error: {str(e)}"
            }


# ============ Manual Testing Documentation ============

"""
EXAMPLE USAGE & TESTING GUIDE

1. PORTFOLIO DATA STRUCTURE:
   Each holding must include:
   - symbol: str (e.g., "BTC", "ETH")
   - quantity: float (amount owned)
   - cost_basis: float (purchase price)
   - current_price: float (current market price, can be None to auto-fetch)

portfolio_data = [
    {
        "symbol": "BTC",
        "quantity": 2.0,
        "cost_basis": 40000.0,
        "current_price": 45000.0
    },
    {
        "symbol": "ETH",
        "quantity": 10.0,
        "cost_basis": 2500.0,
        "current_price": 3000.0
    },
    {
        "symbol": "SOL",
        "quantity": 50.0,
        "cost_basis": 100.0,
        "current_price": 120.0
    }
]

2. MARKET DATA STRUCTURE:
   Retrieved from market_fetcher.get_current_prices()

market_data = {
    "BTC": {
        "price": 45000.0,
        "change_24h": 2.5
    },
    "ETH": {
        "price": 3000.0,
        "change_24h": 1.8
    },
    "SOL": {
        "price": 120.0,
        "change_24h": -0.5
    }
}

3. BASIC USAGE:

from portfolio_advisor import PortfolioAdvisor

# Initialize advisor with API credentials
advisor = PortfolioAdvisor(
    api_key="sk-your-api-key",
    api_url="https://api.openai.com/v1",
    model_name="gpt-4"
)

# Analyze portfolio
result = advisor.analyze_portfolio(portfolio_data, market_data)

# Result structure:
{
    "risk_score": 72,                    # 0-100, higher = more risky
    "diversification_score": 45,         # 0-100, higher = better diversified
    "recommendations": [
        {
            "action": "reduce",          # "reduce", "increase", or "hold"
            "symbol": "BTC",
            "current_allocation": 60.5,
            "target_allocation": 40.0,
            "reasoning": "Reduce concentration risk in single asset"
        },
        {
            "action": "increase",
            "symbol": "ETH",
            "current_allocation": 25.0,
            "target_allocation": 30.0,
            "reasoning": "Increase exposure to Layer-1 alternatives"
        }
    ],
    "new_opportunities": [
        {
            "symbol": "LINK",
            "allocation": 10.0,          # Suggested allocation %
            "confidence": 0.75,          # 0-1 confidence score
            "rationale": "Add DeFi infrastructure exposure"
        },
        {
            "symbol": "MATIC",
            "allocation": 5.0,
            "confidence": 0.65,
            "rationale": "Layer-2 scaling solution diversification"
        }
    ],
    "reasoning": "Portfolio shows high concentration in BTC (60.5%). 
                  Recommended rebalancing to reduce single-asset risk. 
                  Consider adding DeFi and Layer-2 tokens for better sector coverage."
}

4. EXPECTED API REQUEST FORMAT (Flask):

POST /api/portfolio/analyze
Content-Type: application/json

{
    "portfolio": [
        {"symbol": "BTC", "quantity": 2.0, "cost_basis": 40000, "current_price": 45000},
        {"symbol": "ETH", "quantity": 10.0, "cost_basis": 2500, "current_price": 3000}
    ],
    "provider_id": 1,
    "model_name": "gpt-4",
    "user_id": "default"
}

5. EXPECTED API RESPONSE FORMAT:

{
    "success": true,
    "snapshot_id": 123,
    "analysis_id": 456,
    "analysis": {
        "risk_score": 72,
        "diversification_score": 45,
        "recommendations": [...],
        "new_opportunities": [...],
        "reasoning": "..."
    }
}

6. ERROR HANDLING:

# If analysis fails, returns safe defaults:
{
    "risk_score": 0,
    "diversification_score": 0,
    "recommendations": [],
    "new_opportunities": [],
    "reasoning": "Analysis failed: [error message]"
}

7. MANUAL TEST STEPS:

a) Test with single asset (high concentration):
   portfolio = [{"symbol": "BTC", "quantity": 1, "cost_basis": 40000, "current_price": 45000}]
   Expected: High risk score, low diversification, recommendations to add assets

b) Test with balanced portfolio:
   portfolio = [
       {"symbol": "BTC", "quantity": 0.5, "cost_basis": 40000, "current_price": 45000},
       {"symbol": "ETH", "quantity": 5, "cost_basis": 2500, "current_price": 3000},
       {"symbol": "SOL", "quantity": 25, "cost_basis": 100, "current_price": 120}
   ]
   Expected: Moderate scores, minor rebalancing suggestions

c) Test with losing positions:
   portfolio = [{"symbol": "BTC", "quantity": 1, "cost_basis": 50000, "current_price": 45000}]
   Expected: Analysis should acknowledge losses, suggest risk management

d) Test API endpoint via curl:
   curl -X POST http://localhost:5000/api/portfolio/analyze \
     -H "Content-Type: application/json" \
     -d '{
       "portfolio": [{"symbol": "BTC", "quantity": 1, "cost_basis": 40000, "current_price": null}],
       "provider_id": 1,
       "model_name": "gpt-4"
     }'

8. TROUBLESHOOTING:

- If "Price not found": Check symbol is in market_data.py binance_symbols mapping
- If "API connection failed": Verify api_key and api_url are correct
- If "JSON parse failed": Check AI response format in logs
- If scores are 0: Check for parsing errors or API failures in console

"""
