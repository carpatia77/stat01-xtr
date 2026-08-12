# -*- coding: utf-8 -*-
import yfinance as yf
import pandas as pd
import numpy as np
import warnings
from statsmodels.tsa.stattools import adfuller, grangercausalitytests
import scipy.stats as stats

warnings.filterwarnings('ignore')

print('========================================================================')
print('DOSSIE QUANTITATIVO RENAISSANCE: LEAD-LAG XAUUSD -> WIN (M5)')
print('========================================================================\n')

print('[1] EXTRAINDO DADOS...')
xau = yf.download('GC=F', period='60d', interval='5m', progress=False)['Close']
win = yf.download('^BVSP', period='60d', interval='5m', progress=False)['Close']

if isinstance(xau, pd.DataFrame): xau = xau.iloc[:, 0]
if isinstance(win, pd.DataFrame): win = win.iloc[:, 0]
xau.name = 'XAU'
win.name = 'WIN'

if xau.index.tz is not None: xau.index = xau.index.tz_convert('UTC').tz_localize(None)
if win.index.tz is not None: win.index = win.index.tz_convert('UTC').tz_localize(None)

df = pd.concat([xau, win], axis=1).dropna()
print(f'-> Total de candles sincronizados (overlapping): {len(df)}')

# Calculando Log Returns (em BPS - Basis Points)
df['XAU_Ret'] = np.log(df['XAU'] / df['XAU'].shift(1)) * 10000
df['WIN_Ret'] = np.log(df['WIN'] / df['WIN'].shift(1)) * 10000
df = df.dropna()

print('\n[2] TESTE DE ESTACIONARIEDADE (ADF TEST)')
# Fundamental para validar que as regressões não são espúrias
adf_xau = adfuller(df['XAU_Ret'])
adf_win = adfuller(df['WIN_Ret'])

def print_adf(res, name):
    print(f'   {name} ADF Statistic: {res[0]:.4f} (p-value: {res[1]:.4e})')
    if res[1] < 0.01:
        print('      -> [PASS] Serie estritamente estacionaria (Nivel de Confianca > 99%)')
    else:
        print('      -> [FAIL] Serie nao estacionaria')

print_adf(adf_xau, 'XAU_Ret')
print_adf(adf_win, 'WIN_Ret')

print('\n[3] TESTE DE CAUSALIDADE DE GRANGER')
print('H0: Ouro (XAU_Ret) NAO causa na media o Indice (WIN_Ret)')
print('H1: Ouro (XAU_Ret) contem informacao preditiva estatisticamente robusta sobre o Indice (WIN_Ret)')

# O teste Granger exige df no formato [Target, Predictor]
data_granger = df[['WIN_Ret', 'XAU_Ret']]
# Vamos testar lags de 1 a 3 (5 a 15 minutos)
maxlag = 3
gc_res = grangercausalitytests(data_granger, maxlag, verbose=False)

for lag in range(1, maxlag+1):
    p_val = gc_res[lag][0]['ssr_ftest'][1]
    f_val = gc_res[lag][0]['ssr_ftest'][0]
    significativo = 'REJEITAMOS H0 (EDGE CONFIRMADO)' if p_val < 0.05 else 'FALHAMOS EM REJEITAR H0 (RUIDO)'
    print(f'   Lag {lag} (Atraso {lag*5} min) -> F-Stat: {f_val:.2f} | p-value: {p_val:.4e} | {significativo}')


print('\n[4] ANALISE CROSS-CORRELATION COM SIGNIFICANCIA')
print(f'   {"Atraso (Lag)":<20} | {"Correlacao (Pearson)":<25} | {"Significancia (p-value)"}')
print('   ' + '-'*75)

for lag in range(-2, 4):
    xau_shifted = df['XAU_Ret'].shift(lag)
    valid_data = pd.concat([df['WIN_Ret'], xau_shifted], axis=1).dropna()
    
    if len(valid_data) > 0:
        corr, p_value = stats.pearsonr(valid_data.iloc[:,0], valid_data.iloc[:,1])
        minutes = lag * 5
        interp = f'Ouro lidera {minutes}m' if lag > 0 else (f'Bolsa lidera {abs(minutes)}m' if lag < 0 else 'Simultaneo (0m)')
        marker = '*** (Preditor Chefe)' if (lag > 0 and p_value < 0.01 and corr > 0.1) else ''
        print(f'   Lag {lag:2d} ({interp:16s}) | {corr:23.4f} | {p_value:23.4e} {marker}')


print('\n[5] MODELAGEM ESTRUTURAL DA TAXA DE ACERTO (WIN RATE VS TURBULENCIA)')
df['XAU_Lag1'] = df['XAU_Ret'].shift(1)
df = df.dropna()

def test_direction(thresh_bps):
    trade_mask = abs(df['XAU_Lag1']) > thresh_bps
    trades = df[trade_mask]
    if len(trades) < 30: return # Amostra sem peso estatistico
    
    # Sign-test direcional
    acertos = np.sign(trades['WIN_Ret']) == np.sign(trades['XAU_Lag1'])
    win_rate = acertos.mean() * 100
    
    # Teste binomial exato para provar se WinRate > 50% nao eh sorte
    # n = len(trades), k = sum(acertos), p=0.5
    p_val_binomial = stats.binomtest(k=acertos.sum(), n=len(trades), p=0.5, alternative='greater').pvalue
    
    asteriscos = '***' if p_val_binomial < 0.01 else ('**' if p_val_binomial < 0.05 else '')
    
    print(f'   Filtro |XAU(t-1)| > {thresh_bps:4.1f} bps | N = {len(trades):4d} trades | Win Rate = {win_rate:5.1f}% | Binomial p-value: {p_val_binomial:.4f} {asteriscos}')

print('   BPS (Basis Points) -> 10.0 bps = variacao de 0.10% no M5 do Ouro')
for t in [0.0, 5.0, 10.0, 12.0, 15.0, 20.0]:
    test_direction(t)

print('\n========================================================================')
print('PESQUISA CONCLUIDA.')
