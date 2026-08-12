# -*- coding: utf-8 -*-
import yfinance as yf
import pandas as pd
import numpy as np
import warnings

warnings.filterwarnings("ignore")

print("========================================================================")
print("KALMAN TRADE SIMULATOR: EVENT-DRIVEN BACKTEST (RENAISSANCE LEVEL)")
print("========================================================================\n")

print("1. Baixando dados HLC (High, Low, Close) - 60 dias (M5)...")
xau_df = yf.download("GC=F", period="60d", interval="5m", progress=False)
win_df = yf.download("^BVSP", period="60d", interval="5m", progress=False)

if isinstance(xau_df.columns, pd.MultiIndex):
    xau_df.columns = xau_df.columns.droplevel(1)
if isinstance(win_df.columns, pd.MultiIndex):
    win_df.columns = win_df.columns.droplevel(1)

# Precisamos do Close do XAU para divergencia
xau = xau_df[["Close"]].copy()
xau.columns = ["XAU_Close"]

# Precisamos do O, H, L, C do WIN para simulacao intraday
win = win_df[["Open", "High", "Low", "Close"]].copy()
win.columns = ["WIN_Open", "WIN_High", "WIN_Low", "WIN_Close"]

if xau.index.tz is not None: xau.index = xau.index.tz_convert("UTC").tz_localize(None)
if win.index.tz is not None: win.index = win.index.tz_convert("UTC").tz_localize(None)

df = pd.concat([xau, win], axis=1).dropna()
print(f"   Total de candles: {len(df)}")

df["XAU_Ret"] = np.log(df["XAU_Close"] / df["XAU_Close"].shift(1)) * 10000
df["WIN_Ret"] = np.log(df["WIN_Close"] / df["WIN_Close"].shift(1)) * 10000

# Filtrar Noticias
def is_news_window(dt):
    mins = dt.hour * 60 + dt.minute
    return (735 <= mins <= 765) or (1065 <= mins <= 1095)
df["Is_News"] = df.index.map(is_news_window)

print("2. Construindo as Forças (Kalman, Ajuste, GARCH)...")
n = len(df)

# Kalman
kf_mean = np.zeros(n)
kf_var = np.zeros(n)
win_vals = df["WIN_Close"].values
kf_mean[0] = win_vals[0]
kf_var[0] = 1.0
for i in range(1, n):
    K = (kf_var[i-1] + 1e-4) / (kf_var[i-1] + 1e-4 + 1e-2)
    kf_mean[i] = kf_mean[i-1] + K * (win_vals[i] - kf_mean[i-1])
    kf_var[i] = (1 - K) * (kf_var[i-1] + 1e-4)
df["Kalman_Mean"] = kf_mean

# Ajuste B3
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

# Bandas GARCH
df["GARCH_Sigma"] = df["WIN_Ret"].rolling(12).std() * win_vals * 0.0001
base_price = df["WIN_Close"].shift(1)
up_conf = base_price + (0.67 * df["GARCH_Sigma"].fillna(0))
dn_conf = base_price - (0.67 * df["GARCH_Sigma"].fillna(0))
f = 0.35 
df["Banda_Sup"] = base_price * (1 + f * (up_conf/base_price - 1))
df["Banda_Inf"] = base_price * (1 - f * (1 - dn_conf/base_price))

df = df.dropna()

print("\n3. Rodando o Motor de Eventos (Event-Driven)...")

def simulate_trades(target_mode="KALMAN"):
    # target_mode: "KALMAN" ou "ZONE_TO_ZONE"
    
    in_trade = False
    trade_type = 0 # 1 = Long, -1 = Short
    entry_price = 0
    sl_price = 0
    tp_price = 0
    
    pnls = []
    
    # Pre-calcula gatilhos para acelerar
    rompe_alta = df["WIN_Close"] > df["Banda_Sup"]
    rompe_baixa = df["WIN_Close"] < df["Banda_Inf"]
    div_bear = rompe_alta & (df["XAU_Ret"] < 0) & (~df["Is_News"])
    div_bull = rompe_baixa & (df["XAU_Ret"] > 0) & (~df["Is_News"])
    
    for i in range(1, len(df)-1):
        dt = df.index[i]
        
        # 1. Se estiver posicionado, verificar SL/TP no candle ATUAL
        if in_trade:
            win_high = df["WIN_High"].iloc[i]
            win_low = df["WIN_Low"].iloc[i]
            win_open = df["WIN_Open"].iloc[i]
            win_close = df["WIN_Close"].iloc[i]
            
            closed = False
            exit_price = 0
            
            # Checar Time Stop (Fim do dia)
            is_eod = False
            if dt.hour >= 19 and dt.minute >= 50: # Fechar posicoes antes do leilao
                is_eod = True
            
            if trade_type == 1: # COMPRADO
                if win_low <= sl_price:
                    exit_price = min(win_open, sl_price) # se abriu em gap de baixa, sai no open
                    closed = True
                elif win_high >= tp_price:
                    # Assumimos conservadorismo: se pegou SL e TP na mesma barra, pega SL
                    if win_low <= sl_price:
                        exit_price = min(win_open, sl_price)
                    else:
                        exit_price = max(win_open, tp_price) # se abriu acima do TP, sai no open
                    closed = True
                elif is_eod:
                    exit_price = win_close
                    closed = True
                    
            elif trade_type == -1: # VENDIDO
                if win_high >= sl_price:
                    exit_price = max(win_open, sl_price)
                    closed = True
                elif win_low <= tp_price:
                    if win_high >= sl_price:
                        exit_price = max(win_open, sl_price)
                    else:
                        exit_price = min(win_open, tp_price)
                    closed = True
                elif is_eod:
                    exit_price = win_close
                    closed = True
            
            if closed:
                # Calcular PnL liquido de friccao
                if trade_type == 1:
                    pnl_bps = ((exit_price - entry_price) / entry_price) * 10000
                else:
                    pnl_bps = ((entry_price - exit_price) / entry_price) * 10000
                    
                pnl_bps -= 1.0 # FRICCAO (Spread/Custos)
                pnls.append(pnl_bps)
                in_trade = False
                continue # Se fechou a operacao, nao abre outra no mesmo instante
        
        # 2. Se NAO estiver posicionado, buscar gatilho no candle ANTERIOR
        if not in_trade:
            trigger_idx = i - 1
            if div_bear.iloc[trigger_idx]:
                # Setup de Venda engatilhado
                in_trade = True
                trade_type = -1
                entry_price = df["WIN_Open"].iloc[i]
                
                # Stop Técnico na Máxima do Rompimento
                sl_price = df["WIN_High"].iloc[trigger_idx] + 20 # 20 pontos de margem (~1.5 bps)
                
                if target_mode == "KALMAN":
                    tp_price = df["Kalman_Mean"].iloc[trigger_idx] + 15 # Front-run de 15 pontos
                elif target_mode == "ZONE_TO_ZONE":
                    tp_price = df["Banda_Inf"].iloc[trigger_idx] + 15
                    
                # Invalida o setup se o alvo for muito curto ou negativo
                if tp_price >= entry_price:
                    in_trade = False
                    
            elif div_bull.iloc[trigger_idx]:
                # Setup de Compra engatilhado
                in_trade = True
                trade_type = 1
                entry_price = df["WIN_Open"].iloc[i]
                
                # Stop Técnico na Mínima do Rompimento
                sl_price = df["WIN_Low"].iloc[trigger_idx] - 20
                
                if target_mode == "KALMAN":
                    tp_price = df["Kalman_Mean"].iloc[trigger_idx] - 15
                elif target_mode == "ZONE_TO_ZONE":
                    tp_price = df["Banda_Sup"].iloc[trigger_idx] - 15
                    
                if tp_price <= entry_price:
                    in_trade = False
                    
    return pnls

pnls_kalman = simulate_trades("KALMAN")
pnls_zone = simulate_trades("ZONE_TO_ZONE")

def print_metrics(name, pnls_list):
    arr = np.array(pnls_list)
    total_trades = len(arr)
    if total_trades == 0:
        print(f"Sem trades para {name}")
        return
        
    acertos = (arr > 0).sum()
    win_rate = (acertos/total_trades) * 100
    ganhos = arr[arr > 0].sum()
    perdas = abs(arr[arr <= 0].sum())
    
    pf = ganhos / perdas if perdas > 0 else np.inf
    avg_w = arr[arr > 0].mean() if len(arr[arr > 0]) > 0 else 0
    avg_l = abs(arr[arr <= 0].mean()) if len(arr[arr <= 0]) > 0 else 0
    
    sharpe = (arr.mean() / arr.std()) * np.sqrt(total_trades * 6) if arr.std() != 0 else 0
    
    print(f"\n[{name}] - (Custos de 1.0 bps abatidos)")
    print(f"Total Trades: {total_trades}")
    print(f"PnL Líquido Final: {arr.sum():.1f} bps")
    print(f"Win Rate: {win_rate:.1f}%")
    print(f"Profit Factor: {pf:.2f}")
    print(f"Avg Ganho: +{avg_w:.2f} bps | Avg Perda: -{avg_l:.2f} bps")
    print(f"Sharpe Ratio Anualizado: {sharpe:.2f}")

print("\n================== CONFRONTO FINAL ==================")
print_metrics("CENÁRIO A - Alvo no Filtro de Kalman", pnls_kalman)
print_metrics("CENÁRIO B - Alvo Zone to Zone (Banda Oposta)", pnls_zone)
print("=====================================================")
