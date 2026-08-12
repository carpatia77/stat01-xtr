import pandas as pd, numpy as np, yfinance as yf

# Re-run logic to get table
xau = yf.download("GC=F", period="60d", interval="5m", progress=False)["Close"]
win = yf.download("^BVSP", period="60d", interval="5m", progress=False)["Close"]
if isinstance(xau, pd.DataFrame): xau = xau.iloc[:, 0]
if isinstance(win, pd.DataFrame): win = win.iloc[:, 0]
xau.name, win.name = "XAU", "WIN"
xau.index = xau.index.tz_convert("UTC").tz_localize(None)
win.index = win.index.tz_convert("UTC").tz_localize(None)
df = pd.concat([xau, win], axis=1).dropna()
df["XAU_Ret"] = np.log(df["XAU"] / df["XAU"].shift(1)) * 10000
df["WIN_Ret"] = np.log(df["WIN"] / df["WIN"].shift(1)) * 10000

def is_news(dt):
    m = dt.hour * 60 + dt.minute
    return (735 <= m <= 765) or (1065 <= m <= 1095)
df["Is_News"] = df.index.map(is_news)

n = len(df)
kf_mean = np.zeros(n)
kf_var = np.zeros(n)
win_vals = df["WIN"].values
kf_mean[0] = win_vals[0]
kf_var[0] = 1.0
for i in range(1, n):
    K = (kf_var[i-1] + 1e-4) / (kf_var[i-1] + 1e-4 + 1e-2)
    kf_mean[i] = kf_mean[i-1] + K * (win_vals[i] - kf_mean[i-1])
    kf_var[i] = (1 - K) * (kf_var[i-1] + 1e-4)
df["Kalman_Mean"] = kf_mean

df["Range_Proxy"] = df["WIN_Ret"].abs().clip(lower=1.0)
ajuste_buffer = np.full(n, np.nan)
acc_vol, acc_money, last_ajuste = 0.0, 0.0, np.nan
last_day = -1
for i in range(n):
    dt = df.index[i]
    if dt.day != last_day and dt.hour >= 19:
        acc_vol = 0.0; acc_money = 0.0
        last_day = dt.day
    if dt.hour == 19:
        vol = df["Range_Proxy"].iloc[i]
        acc_vol += vol
        acc_money += win_vals[i] * vol
        last_ajuste = acc_money / acc_vol
    ajuste_buffer[i] = last_ajuste
df["Ajuste_B3"] = pd.Series(ajuste_buffer, index=df.index).ffill()

df["GARCH_Sigma"] = df["WIN_Ret"].rolling(12).std() * win_vals * 0.0001
base_price = df["WIN"].shift(1)
up_conf = base_price + (0.67 * df["GARCH_Sigma"].fillna(0))
dn_conf = base_price - (0.67 * df["GARCH_Sigma"].fillna(0))
df["Banda_Sup"] = base_price * (1 + 0.35 * (up_conf/base_price - 1))
df["Banda_Inf"] = base_price * (1 - 0.35 * (1 - dn_conf/base_price))

df = df.dropna()
div_bear = (df["WIN"] > df["Banda_Sup"]) & (df["XAU_Ret"] < 0) & (~df["Is_News"])
div_bull = (df["WIN"] < df["Banda_Inf"]) & (df["XAU_Ret"] > 0) & (~df["Is_News"])

trades = []
for i in range(len(df)-2):
    if not (div_bear.iloc[i] or div_bull.iloc[i]): continue
    t = df.index[i]
    setup = "Falso Rompimento de ALTA (Venda)" if div_bear.iloc[i] else "Falso Rompimento de BAIXA (Compra)"
    entrada = df["WIN"].iloc[i]
    alvo = df["Kalman_Mean"].iloc[i]
    xau_ret = df["XAU_Ret"].iloc[i]
    saida = df["WIN"].iloc[i+1]
    
    if div_bear.iloc[i]:
        pnl = ((entrada - saida) / entrada) * 10000
    else:
        pnl = ((saida - entrada) / entrada) * 10000
        
    ajuste_b3 = df["Ajuste_B3"].iloc[i]
    trades.append((t, setup, round(entrada,0), round(alvo,0), round(ajuste_b3,0), round(xau_ret,2), round(pnl,2)))

# Calculate convergence between Kalman and Ajuste (Delta médio em pontos)
# Para medir o quanto o Kalman orbita o Ajuste
delta_kalman_ajuste = (df["Kalman_Mean"] - df["Ajuste_B3"]).dropna().abs().mean()
corr_kalman_ajuste = df["Kalman_Mean"].corr(df["Ajuste_B3"])

print(f"--- CONVERGENCIA KALMAN x AJUSTE B3 ---")
print(f"Correlação de Pearson entre as duas forças: {corr_kalman_ajuste:.4f}")
print(f"Distância Média Absoluta: {delta_kalman_ajuste:.0f} pontos\n")

# Get last 15 trades for demo
print("| Data/Hora (UTC) | Gatilho GARCH (Setup) | WIN Preço | Kalman (Alvo Dinâmico) | Ajuste B3 (Âncora) | XAU Diverg. (bps) | PnL Trade (bps) |")
print("|----------------|-----------------------|-----------|------------------------|--------------------|-------------------|-----------------|")
for t in trades[-15:]:
    print(f"| `{t[0].strftime('%Y-%m-%d %H:%M')}` | {t[1]} | {t[2]:.0f} | {t[3]:.0f} | {t[4]:.0f} | {t[5]:.2f} | **{t[6]:.2f}** |")
