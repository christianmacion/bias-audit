"""
Project 9 — Look-Ahead Bias Audit ("how a backtest lies")
=========================================================
The most dangerous backtest errors are not bad ideas — they are subtle leaks
that make a worthless rule look brilliant. This project demonstrates two and
quantifies the phantom alpha each creates, then shows the diagnostic every
result should pass: the SHIFT TEST (lag the signal one more bar; a real edge
barely moves, a leaked one collapses).

  Leak 1 — same-bar execution: trade at the close used to BUILD the signal.
  Leak 2 — future-peeking smoother: a CENTERED moving average sees the future.

Free data: Binance BTC daily. quantlib for stats. Author: Christian Macion.
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "quantlib"))
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
import quantlib as q
ANN = 365

def breakout_signal(px, win=20, center=False):
    """Trade WITH the deviation from a moving average (breakout/momentum).
    With center=True the moving average peeks at the future (Leak 2)."""
    ma = px.rolling(win, center=center).mean()
    sd = px.rolling(win, center=center).std()
    z = (px - ma) / sd
    return np.sign(z)                                   # long above the mean, short below

def sharpe_at_lag(signal, ret, lag):
    return q.sharpe((signal.shift(lag) * ret).dropna(), ANN)

def main():
    print("Pulling BTC daily (Binance) ...")
    px = q.binance_klines("BTCUSDT", "1d", start="2017-08-01")["close"]
    ret = px.pct_change()

    # ---- LEAK 1: same-bar execution vs honest next-bar ----
    sig = breakout_signal(px, 20, center=False)
    leaked = sharpe_at_lag(sig, ret, 0)                 # signal_t on ret_t : trades the bar it just saw
    honest = sharpe_at_lag(sig, ret, 1)                 # signal_t on ret_{t+1} : tradeable
    print(f"\nLEAK 1 — same-bar execution:")
    print(f"  leaked (lag 0, look-ahead) Sharpe = {leaked:+.2f}")
    print(f"  honest (lag 1, tradeable)  Sharpe = {honest:+.2f}")
    print(f"  >>> phantom alpha from the leak: {leaked - honest:+.2f} Sharpe")

    # ---- LEAK 2: future-peeking centered smoother (with honest lag-1 execution) ----
    sig_centered = breakout_signal(px, 20, center=True)
    centered = sharpe_at_lag(sig_centered, ret, 1)
    print(f"\nLEAK 2 — centered (future-peeking) moving average, executed honestly at lag 1:")
    print(f"  centered-smoother Sharpe = {centered:+.2f}  vs trailing-smoother {honest:+.2f}  "
          f">>> phantom {centered - honest:+.2f}")

    # ---- THE SHIFT TEST: Sharpe vs execution lag ----
    lags = [0, 1, 2, 3, 5, 10]
    curve = [sharpe_at_lag(sig, ret, L) for L in lags]
    print(f"\nSHIFT TEST (Sharpe by execution lag): " +
          ", ".join(f"lag{L}:{s:+.2f}" for L, s in zip(lags, curve)))
    print(f"  The cliff between lag 0 ({curve[0]:+.2f}) and lag 1 ({curve[1]:+.2f}) IS the look-ahead.")
    print(f"  Beyond lag 1 the (honest) edge is flat/small ({curve[1]:+.2f} -> {curve[-1]:+.2f}) "
          f"-> no genuine multi-day edge here.")

    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
    ax[0].bar(["leaked\n(same-bar)","honest\n(next-bar)","centered\nsmoother"],
              [leaked, honest, centered], color=["#b3402f","#2e6f4e","#b3402f"])
    ax[0].axhline(0, color="gray", lw=0.7); ax[0].set_ylabel("Sharpe")
    ax[0].set_title("Two leaks vs the honest result")
    ax[1].plot(lags, curve, "o-", color="#243b6b")
    ax[1].axhline(0, color="gray", lw=0.7)
    ax[1].annotate("look-ahead cliff", xy=(0.5,(curve[0]+curve[1])/2), fontsize=8, color="crimson")
    ax[1].set_xlabel("execution lag (bars)"); ax[1].set_ylabel("Sharpe")
    ax[1].set_title("The shift test: Sharpe vs lag")
    fig.tight_layout(); fig.savefig(os.path.join(os.path.dirname(__file__),"results","figure.png"), dpi=130)

    json.dump({"leaked_lag0_sharpe":round(leaked,3),"honest_lag1_sharpe":round(honest,3),
               "phantom_alpha_sharpe":round(leaked-honest,3),"centered_smoother_sharpe":round(centered,3),
               "shift_test":{f"lag{L}":round(s,3) for L,s in zip(lags,curve)}},
              open(os.path.join(os.path.dirname(__file__),"results","results.json"),"w"), indent=2)
    print("\nSaved results/figure.png and results/results.json")

if __name__ == "__main__":
    main()
