from portfolio import Portfolio, Asset
from data_fetcher import fetch_current_prices, convert_currency
from rebalance import full_rebalance, minimal_rebalance
from report import (
    print_portfolio_report,
    print_rebalance_suggestions,
    print_group_weights_report,
    print_new_portfolio_report,
)
def strtobool(val):
    """Convert a string representation of truth to true (1) or false (0)."""
    val = val.lower()
    if val in ("y", "yes", "t", "true", "on", "1"):
        return True
    elif val in ("n", "no", "f", "false", "off", "0"):
        return False
    else:
        raise ValueError(f"invalid truth value {val!r}")


def prompt_csv_path():
    path = input("Enter path to your CSV file (default: etfs.csv): ").strip()
    return path or "etfs.csv"


def prompt_currency():
    return input("Enter your base currency (e.g. USD, EUR): ").strip().upper()


def prompt_rebalance_type():
    print("\nChoose rebalancing method:")
    print("1. Full rebalance (match targets exactly)")
    print("2. Minimal rebalance (only if drift > threshold)")
    print("3. Value-preserving rebalance (total value unchanged)")
    use_ceil = strtobool(input("Use ceil for share rounding? (y/N): ") or "n")
    choice = input("Enter 1, 2, or 3: ").strip()
    return choice, use_ceil


def apply_suggestions(portfolio, suggestions):
    from copy import deepcopy

    new_portfolio = deepcopy(portfolio)
    ticker_to_asset = {a.ticker: a for a in new_portfolio.get_assets()}
    for s in suggestions:
        ticker = s["ticker"]
        if ticker in ticker_to_asset:
            asset = ticker_to_asset[ticker]
            if s["action"] == "BUY":
                asset.shares += s["shares"]
            elif s["action"] == "SELL":
                asset.shares -= s["shares"]
                if asset.shares < 0:
                    asset.shares = 0
    return new_portfolio


def main():
    print("Welcome to the Portfolio Rebalancing Tool!")
    print("Portfolio will be loaded from a CSV file.")
    from portfolio import load_portfolio_from_csv

    csv_path = prompt_csv_path()
    portfolio = load_portfolio_from_csv(csv_path)
    print(f"Loaded {len(portfolio.get_assets())} assets from {csv_path}.")
    base_currency = prompt_currency()
    prices = fetch_current_prices(portfolio.get_assets())
    for asset in portfolio.get_assets():
        price = prices.get(asset.ticker)
        if price is not None:
            if asset.currency != base_currency:
                converted = convert_currency(price, asset.currency, base_currency)
                if converted is not None:
                    asset.converted_value = converted * asset.shares
                    prices[asset.ticker] = converted
                else:
                    print(
                        f"Warning: Could not convert {asset.ticker} to {base_currency}. Skipping."
                    )
                    continue
            else:
                asset.converted_value = price * asset.shares
    print_portfolio_report(portfolio, prices, base_currency)
    print_group_weights_report(portfolio, prices, base_currency)
    choice, use_ceil = prompt_rebalance_type()
    if choice == "2":
        threshold = input(
            "Enter drift threshold as decimal (e.g. 0.05 for 5%): "
        ).strip()
        try:
            threshold = float(threshold)
        except ValueError:
            threshold = 0.05
        suggestions = minimal_rebalance(
            portfolio, prices, base_currency, threshold, use_ceil=use_ceil
        )
    elif choice == "3":
        from rebalance import value_preserving_rebalance

        suggestions = value_preserving_rebalance(
            portfolio, prices, base_currency, use_ceil=use_ceil
        )
        orig_total = sum(
            (prices.get(a.ticker, 0) or 0) * a.shares for a in portfolio.get_assets()
        )
        new_portfolio = apply_suggestions(portfolio, suggestions)
        new_total = sum(
            (prices.get(a.ticker, 0) or 0) * a.shares
            for a in new_portfolio.get_assets()
        )
        drift = abs(new_total - orig_total)
        drift_pct = drift / orig_total if orig_total else 0
        if drift_pct > 0.005:
            print(
                f"WARNING: Value drift after value-preserving rebalance is {drift:.2f} {base_currency} ({drift_pct*100:.2f}%)."
            )
    else:
        suggestions = full_rebalance(
            portfolio, prices, base_currency, use_ceil=use_ceil
        )
    print_rebalance_suggestions(suggestions, prices=prices)
    print_new_portfolio_report(portfolio, prices, base_currency, suggestions)


if __name__ == "__main__":
    main()
