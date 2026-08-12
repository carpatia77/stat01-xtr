
# -*- coding: utf-8 -*-
import yfinance as yf
import pandas as pd
import numpy as np
from arch import arch_model
import warnings

warnings.filterwarnings("ignore")

print("========================================================================")
print("KALMAN REVERSION EDGE: SETUP DE EXAUSTAO (EGARCH + KALMAN + VWAP B3)")
print("========================================================================\n")

print("1. Baixando e sincronizando dados (60 dias - M5)...")
xau = yf.download("GC=F", period="60d", interval="5m", progress=False)["Close"]
win = yf.download("^BVSP", period="60d", interval="5m", progress=False)["Close"]

if isinstance(xau, pd.DataFrame): xau = xau.iloc[:, 0]
if isinstance(win, pd.DataFrame): win = win.iloc[:, 0]
xau.name = "XAU"
win.name = "WIN"
if xau.index.tz is not None: xau.index = xau.index.tz_convert("UTC").tz_localize(None)
if win.index.tz is not None: win.index = win.index.tz_convert("UTC").tz_localize(None)

df = pd.concat([xau, win], axis=1).dropna()
print(f"   Total de candles: {len(df)}")

# Retornos 
df["XAU_Ret"] = np.log(df["XAU"] / df["XAU"].shift(1)) * 10000
df["WIN_Ret"] = np.log(df["WIN"] / df["WIN"].shift(1)) * 10000

# Filtro macro: remover +/- 15 min de noticias
def is_news_window(dt):
    mins = dt.hour * 60 + dt.minute
    if 735 <= mins <= 765: return True
    if 1065 <= mins <= 1095: return True
    return False

df["Is_News"] = df.index.map(is_news_window)

print("\n2. Calculando Filtro de Kalman 1D (Média Dinâmica Instantânea)...")
n = len(df)
kf_mean = np.zeros(n)
kf_var = np.zeros(n)
win_vals = df["WIN"].values

kf_mean[0] = win_vals[0]
kf_var[0] = 1.0
Q = 1e-4 # Variancia do processo (quão rapido a media verdadeira pode mudar)
R = 1e-2 # Variancia da observacao (ruido do M5)

for i in range(1, n):
    # Predict
    pred_mean = kf_mean[i-1]
    pred_var = kf_var[i-1] + Q
    # Update
    K = pred_var / (pred_var + R)
    kf_mean[i] = pred_mean + K * (win_vals[i] - pred_mean)
    kf_var[i] = (1 - K) * pred_var

df["Kalman_Mean"] = kf_mean

print("3. Calculando Ajuste B3 (Proxy VWAP do fechamento do Spot)...")
# Como o spot encerra 19:55 UTC, vamos acumular VWAP das 19:00 as 19:55 UTC
# Para simular a memoria institucional que puxa o preco no dia seguinte
ajuste_buffer = np.full(n, np.nan)
acc_vol, acc_money, last_ajuste = 0.0, 0.0, np.nan
last_day = -1

# Aproximacao do volume com proxy de variacao (ja que indice spot as vezes nao tem vol limpo)
# Vamos usar o range high-low proxy ou retorno absoluto como peso se vol for zero
df["Range_Proxy"] = df["WIN_Ret"].abs().clip(lower=1.0) 

for i in range(n):
    dt = df.index[i]
    if dt.day != last_day and dt.hour >= 19:
        acc_vol = 0.0; acc_money = 0.0
        last_day = dt.day
    
    if dt.hour == 19: # 19:00 as 19:55 UTC (Fechamento spot B3)
        vol = df["Range_Proxy"].iloc[i]
        acc_vol += vol
        acc_money += win_vals[i] * vol
        last_ajuste = acc_money / acc_vol
        
    ajuste_buffer[i] = last_ajuste

df["Ajuste_B3"] = pd.Series(ajuste_buffer, index=df.index).ffill() # Carrega o ajuste de ontem pro dia de hoje

print("4. Gerando as Bandas EGARCH Geométricas (O Gatilho Falso)...")
# Vamos usar um rolling std com multiplicador escalado para simular o modelo geometrico [25%, 75%] do indicador
# O EGARCH geometrico falho prometia 50% de contencao, mas falhava muito. 
# Simulando a banda geometrica falha: banda estreita em torno do preco passado
df["GARCH_Sigma"] = df["WIN_Ret"].rolling(12).std() * win_vals * 0.0001
# f = 0.5 (rank 25-75). Usaremos um z-score baixo (ex: 0.67 para 50% mass) porem esticado pela geometria
z_conf = 0.67 
f = 0.35 # Fator geometrico de 35% de rank (bandas mais justas)
base_price = df["WIN"].shift(1)
up_conf = base_price + (z_conf * df["GARCH_Sigma"].fillna(0))
dn_conf = base_price - (z_conf * df["GARCH_Sigma"].fillna(0))

df["Banda_Sup"] = base_price * (1 + f * (up_conf/base_price - 1))
df["Banda_Inf"] = base_price * (1 - f * (1 - dn_conf/base_price))

df = df.dropna()

print("\n5. Testando o EDGE INVERTIDO (Reversao a Media Kalman)")
print("Regra de Ouro:")
print(" - Ibovespa fura a Banda Superior (Exaustao Cinética)")
print(" - Ouro (XAUUSD) esta NEGATIVO no mesmo candle (Divergencia Macro, recusa o rompimento)")
print(" - Trade: VENDER Ibovespa mirando o retorno para o Kalman_Mean")

# Identificar Falsos Rompimentos
rompe_alta = df["WIN"] > df["Banda_Sup"]
rompe_baixa = df["WIN"] < df["Banda_Inf"]

# XAU divergiu (Divergencia Bearish: WIN rompeu topo, mas XAU caiu. Divergencia Bullish: WIN rompeu fundo, mas XAU subiu)
div_bearish = rompe_alta & (df["XAU_Ret"] < 0)
div_bullish = rompe_baixa & (df["XAU_Ret"] > 0)

# Filtrar Noticias
div_bearish = div_bearish & (~df["Is_News"])
div_bullish = div_bullish & (~df["Is_News"])

total_trades = div_bearish.sum() + div_bullish.sum()

# Simulacao do PnL do Trade de Reversao
# Alvo: Kalman_Mean no candle T+1 ou T+2
acertos = 0
ganhos_bps = 0
perdas_bps = 0
all_pnls = []

for i in range(len(df)-2):
    is_bear = div_bearish.iloc[i]
    is_bull = div_bullish.iloc[i]
    
    if not is_bear and not is_bull: continue
        
    entrada = df["WIN"].iloc[i]
    preco_saida = df["WIN"].iloc[i+1] # Saida rapida no proximo candle
    
    if is_bear:
        pnl_bps = ((entrada - preco_saida) / entrada) * 10000
    else:
        pnl_bps = ((preco_saida - entrada) / entrada) * 10000
        
    all_pnls.append(pnl_bps)
        
    if pnl_bps > 0:
        acertos += 1
        ganhos_bps += pnl_bps
    else:
        perdas_bps += abs(pnl_bps)

print("\n--- RESULTADO DO SCALPING DE REVERSAO (KALMAN + GARCH + XAU) ---")
print(f"Total de Setups Armados (Falso Rompimento Divergente): {total_trades}")
if total_trades > 0:
    pnls = np.array(all_pnls)
    
    # RENAISSANCE STRESS TEST (Friction / Slippage)
    FRICTION_BPS = 1.0 # 0.5 bps entrada + 0.5 bps saida (Spread + Custos)
    pnls_net = pnls - FRICTION_BPS
    
    ganhos_bps_net = pnls_net[pnls_net > 0].sum() if len(pnls_net[pnls_net > 0]) > 0 else 0
    perdas_bps_net = abs(pnls_net[pnls_net <= 0].sum()) if len(pnls_net[pnls_net <= 0]) > 0 else 0
    
    win_rate_net = (len(pnls_net[pnls_net > 0])/total_trades) * 100
    profit_factor_net = ganhos_bps_net / perdas_bps_net if perdas_bps_net != 0 else np.inf
    avg_win_net = pnls_net[pnls_net > 0].mean() if len(pnls_net[pnls_net > 0]) > 0 else 0
    avg_loss_net = abs(pnls_net[pnls_net <= 0].mean()) if len(pnls_net[pnls_net <= 0]) > 0 else 0
    
    sharpe_trade_net = pnls_net.mean() / pnls_net.std() if pnls_net.std() != 0 else 0
    sharpe_annualized_net = sharpe_trade_net * np.sqrt(len(pnls) * 6)
    
    print(f"[CENÁRIO BRUTO (Sem Custos)]")
    print(f"PnL Líquido Bruto: {pnls.sum():.1f} bps | Win Rate: {(acertos/total_trades)*100:.1f}%")
    
    print(f"\n[RENAISSANCE STRESS TEST - COM ATRITO DE {FRICTION_BPS} BPS POR TRADE]")
    print(f"Win Rate (Net): {win_rate_net:.1f}%")
    print(f"PnL Liquido Final (Net): {pnls_net.sum():.1f} bps")
    print(f"Profit Factor (Net): {profit_factor_net:.2f}")
    print(f"Média de Ganho: +{avg_win_net:.2f} bps | Média de Perda: -{avg_loss_net:.2f} bps")
    print(f"Sharpe Ratio (Net Anualizado): {sharpe_annualized_net:.2f}")
    print("-----------------------------------------------------------------")
    print("CONCLUSÃO DO STRESS TEST: " + ("O Edge sobrevive ao atrito! ALFA VERDADEIRO." if pnls_net.sum() > 0 else "ALARME FALSO! O spread destruiu o Edge. Necessita de alvo maior."))

