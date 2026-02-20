import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import skew, kurtosis

# -----------------------------
# 1. Data Download
# -----------------------------
tickers = ["BTC-USD", "ETH-USD", "BNB-USD", "SOL-USD"]

data = yf.download(tickers, start="2021-01-01")["Close"]
data = data.dropna()

# -----------------------------
# 2. Log Returns
# -----------------------------
returns = np.log(data / data.shift(1))
returns = returns.dropna()

# -----------------------------
# 3. Multi-Horizon Momentum
# -----------------------------
momentum_7 = returns.rolling(7).sum()
momentum_14 = returns.rolling(14).sum()
momentum_30 = returns.rolling(30).sum()

combined_momentum = (momentum_7 + momentum_14 + momentum_30) / 3

# -----------------------------
# 4. Volatility Adjustment
# -----------------------------
rolling_vol = returns.rolling(20).std()

score = combined_momentum / rolling_vol
score = score.clip(-5, 5)

# -----------------------------
# 5. Portfolio Weights
# -----------------------------
weights = score.div(score.abs().sum(axis=1), axis=0)

# Exposure scaling (reduce aggressiveness)
weights = weights * 0.5

# Volatility regime filter
market_vol = rolling_vol.mean(axis=1)
vol_threshold = market_vol.quantile(0.75)
high_vol_regime = market_vol > vol_threshold
weights[high_vol_regime] = weights[high_vol_regime] * 0.5

# -----------------------------
# 6. Dynamic Backtest (Weekly Rebalance + Cost)
# -----------------------------
equity = 1.0
equity_list = []

current_weights = weights.iloc[0]

for i in range(len(returns)):

    if i == 0:
        equity_list.append(equity)
        continue

    # Weekly rebalance
    if i % 5 == 0:
        turnover = (weights.iloc[i-1] - current_weights).abs().sum()
        cost = turnover * 0.001
        current_weights = weights.iloc[i-1]
    else:
        cost = 0

    daily_return = (current_weights * returns.iloc[i]).sum()
    daily_return -= cost

    equity *= (1 + daily_return)
    equity_list.append(equity)

# -----------------------------
# 7. Performance Metrics
# -----------------------------
dynamic_equity = pd.Series(equity_list, index=returns.index)

dynamic_returns = dynamic_equity.pct_change().dropna()

dynamic_sharpe = (dynamic_returns.mean() / dynamic_returns.std()) * np.sqrt(252)

rolling_max = dynamic_equity.cummax()
dynamic_drawdown = (dynamic_equity - rolling_max) / rolling_max
max_drawdown = dynamic_drawdown.min()

strategy_skew = skew(dynamic_returns)
strategy_kurtosis = kurtosis(dynamic_returns)

print("Final Equity:", dynamic_equity.iloc[-1])
print("Sharpe:", dynamic_sharpe)
print("Max Drawdown:", max_drawdown)
print("Skew:", strategy_skew)
print("Kurtosis:", strategy_kurtosis)

# -----------------------------
# 9. Turnover Calculation
# -----------------------------
rebalance_flags = [i % 5 == 0 for i in range(len(weights))]
turnover_series = []

prev_weights = weights.iloc[0]

for i in range(len(weights)):
    if i % 5 == 0 and i != 0:
        turnover = (weights.iloc[i-1] - prev_weights).abs().sum()
        turnover_series.append(turnover)
        prev_weights = weights.iloc[i-1]
    else:
        turnover_series.append(0)

avg_turnover = np.mean(turnover_series)

print("Average Turnover:", avg_turnover)

# -----------------------------
# 8. Plots
# -----------------------------
plt.figure(figsize=(10,5))
dynamic_equity.plot()
plt.title("Equity Curve")
plt.show()

plt.figure(figsize=(10,5))
dynamic_drawdown.plot()
plt.title("Drawdown")
plt.show()