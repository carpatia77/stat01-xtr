# -*- coding: utf-8 -*-
import yfinance as yf
import pandas as pd
import numpy as np
import warnings

warnings.filterwarnings('ignore')

print('========================================================================')
print('EVENT-DRIVEN RESEARCH: IMPACTO MACRO NO XAUUSD E ARBITRAGEM NO WIN')
print('========================================================================\n')

# 1. Extracao de Dados (60 dias - Resolucao M5)
xau = yf.download('GC=F', period='60d', interval='5m', progress=False)['Close']
win = yf.download('^BVSP', period='60d', interval='5m', progress=False)['Close']

if isinstance(xau, pd.DataFrame): xau = xau.iloc[:, 0]
if isinstance(win, pd.DataFrame): win = win.iloc[:, 0]
xau.name = 'XAU'
win.name = 'WIN'

# Converter para UTC e tirar fuso para join
if xau.index.tz is not None: xau.index = xau.index.tz_convert('UTC').tz_localize(None)
if win.index.tz is not None: win.index = win.index.tz_convert('UTC').tz_localize(None)

df = pd.concat([xau, win], axis=1).dropna()
df['XAU_Ret'] = np.log(df['XAU'] / df['XAU'].shift(1)) * 10000 # Retorno M5 em Basis Points (bps)
df['WIN_Ret'] = np.log(df['WIN'] / df['WIN'].shift(1)) * 10000
df['XAU_Lag1'] = df['XAU_Ret'].shift(1)
df = df.dropna()

print(f'-> Total de candles: {len(df)}')

# 2. Mapeamento de Turbulencia Absoluta no XAUUSD
df['XAU_Abs_Ret'] = df['XAU_Ret'].abs()

print('\n[A] TOP 10 MAIORES CHOQUES DO OURO (M5) NOS ULTIMOS 60 DIAS')
print('Identificando a hora do epicentro global da liquidez...')
print(f'{"Data/Hora (UTC)":<22} | {"Choque Ouro":<15} | {"Reacao Ibovespa (Lag 1)":<25} | {"Status"}')
print('-'*85)

top10 = df.nlargest(10, 'XAU_Abs_Ret')
for idx, row in top10.iterrows():
    ouro_ret = row['XAU_Ret']
    win_ret = row['WIN_Ret'] # Retorno no MESMO candle
    # O impacto no Bovespa no proximo candle ja esta alinhado? 
    # Espera: queremos ver o retorno do Ibov no candle SEGUINTE ao choque.
    # idx eh o horario do choque do ouro. O proximo candle de M5 do WIN eh a reacao.
    try:
        idx_pos = df.index.get_loc(idx)
        win_reacao_t1 = df.iloc[idx_pos + 1]['WIN_Ret']
        
        direcao_certa = np.sign(ouro_ret) == np.sign(win_reacao_t1)
        status = 'VENCEU' if direcao_certa else 'PERDEU'
        
        print(f'{str(idx):<22} | {ouro_ret:>7.1f} bps     | WIN T+1: {win_reacao_t1:>7.1f} bps     | {status}')
    except:
        pass


# 3. Classificacao Event-Driven (Catalisador Economico dos EUA)
# Horarios criticos em NY (EDT):
# 08:30 EDT = 12:30 UTC -> CPI, PPI, NFP, Retail Sales, GDP
# 10:00 EDT = 14:00 UTC -> ISM PMI, Consumer Confidence, JOLTs
# 14:00 EDT = 18:00 UTC -> FOMC Rate Decision
# Em UTC, essas sao as exatas horas em que os robos HFT disparam
def is_macro_window(dt):
    # Definimos uma janela de 15 minutos (3 candles) ao redor da noticia
    t = dt.time()
    if (t.hour == 12 and t.minute in [30, 35, 40]) or \
       (t.hour == 14 and t.minute in [0, 5, 10]) or \
       (t.hour == 18 and t.minute in [0, 5, 10]):
        return True
    return False

df['Is_Macro_Event'] = df.index.map(is_macro_window)

print('\n[B] ISOLANDO A ANOMALIA E CALCULANDO O EDGE DIRECIONAL')
print('Vamos quebrar o mercado em 2 regimes: Noticias x Fluxo Organico\n')

def backtest_edge(name, mask, thresh_bps=0):
    subset = df[mask]
    # Filtro de choque
    trade_mask = abs(subset['XAU_Lag1']) > thresh_bps
    trades = subset[trade_mask]
    if len(trades) == 0:
        return
        
    acertos = np.sign(trades['WIN_Ret']) == np.sign(trades['XAU_Lag1'])
    win_rate = acertos.mean() * 100
    
    # Simulação de PnL teorico: 
    # Assume operacao direcional de 1 contrato no Ibov ganhando exatos BPS do movimento
    # Retorno direcional = Se acertou, soma o modulo do retorno do Win. Se errou, subtrai.
    pnl = np.where(acertos, abs(trades['WIN_Ret']), -abs(trades['WIN_Ret'])).sum()
    
    print(f'--- {name} ---')
    print(f'Total Trades (> {thresh_bps} bps): {len(trades)}')
    print(f'Win Rate: {win_rate:.1f}%')
    print(f'PnL Acumulado (Bruto): {pnl:.1f} bps')
    print('-'*40)

# Sem filtro de turbulencia para ver baseline
backtest_edge('1. BASELINE (Todos os Candles de fluxo organico)', ~df['Is_Macro_Event'], thresh_bps=0)
backtest_edge('2. O CAOS ORGANICO (Fluxo sem Noticia, mas com choque > 10 bps)', ~df['Is_Macro_Event'], thresh_bps=10)
backtest_edge('3. EVENT-DRIVEN MACRO (Apenas Janelas de Noticia EUA)', df['Is_Macro_Event'], thresh_bps=0)
backtest_edge('4. EVENT-DRIVEN TURBULENCIA (Janelas de Noticia EUA + Choque > 10 bps no XAU)', df['Is_Macro_Event'], thresh_bps=10)

print('\nObs: O PnL em Basis Points (bps) eh a soma linear dos retornos isolados de cada operacao no M5.')
