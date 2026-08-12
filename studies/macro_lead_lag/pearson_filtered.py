# -*- coding: utf-8 -*-
import yfinance as yf
import pandas as pd
import numpy as np
import scipy.stats as stats
import warnings

warnings.filterwarnings('ignore')

print('========================================================================')
print('PEARSON CORRELATION (ORGANIC FLOW) - EXCLUINDO JANELAS DE NOTICIA')
print('========================================================================\n')

# 1. Download
print('Baixando dados...')
xau = yf.download('GC=F', period='60d', interval='5m', progress=False)['Close']
win = yf.download('^BVSP', period='60d', interval='5m', progress=False)['Close']

if isinstance(xau, pd.DataFrame): xau = xau.iloc[:, 0]
if isinstance(win, pd.DataFrame): win = win.iloc[:, 0]
xau.name = 'XAU'
win.name = 'WIN'

if xau.index.tz is not None: xau.index = xau.index.tz_convert('UTC').tz_localize(None)
if win.index.tz is not None: win.index = win.index.tz_convert('UTC').tz_localize(None)

df = pd.concat([xau, win], axis=1).dropna()

df['XAU_Ret'] = np.log(df['XAU'] / df['XAU'].shift(1))
df['WIN_Ret'] = np.log(df['WIN'] / df['WIN'].shift(1))

# Construir "caminho de preco" acumulado (Normalized Price Path)
# Comecando do zero apos o primeiro retorno
df['XAU_Path'] = df['XAU_Ret'].cumsum() * 100
df['WIN_Path'] = df['WIN_Ret'].cumsum() * 100

df = df.dropna()

print(f'-> Total de candles sincronizados iniciais: {len(df)}')

# 2. Filtragem de +/- 15 minutos ao redor das noticias
# Janelas:
# NFP/CPI = 12:30 UTC -> Excluir de 12:15 as 12:45
# FOMC = 18:00 UTC -> Excluir de 17:45 as 18:15

def is_news_window(dt):
    t = dt.time()
    # Converte para minutos desde meia-noite para facilitar a logica
    mins = t.hour * 60 + t.minute
    
    # Janela 1: 12:15 as 12:45 (735 a 765)
    if 735 <= mins <= 765:
        return True
    
    # Janela 2: 17:45 as 18:15 (1065 a 1095)
    if 1065 <= mins <= 1095:
        return True
        
    return False

mask_news = df.index.map(is_news_window)
df_organic = df[~mask_news]

print(f'-> Total de candles removidos (Ruido HFT da Noticia): {sum(mask_news)}')
print(f'-> Total de candles no fluxo ORGANICO PURO: {len(df_organic)}')

# 3. Correlacao de Pearson
print('\n[RESULTADOS ESTATISTICOS DO FLUXO ORGANICO]')

# A. Correlacao dos Retornos no mesmo M5 (Acao/Reacao instantanea)
corr_ret, p_ret = stats.pearsonr(df_organic['XAU_Ret'], df_organic['WIN_Ret'])
print(f'\n1. Correlacao de Retornos (Atrito Instantaneo M5):')
print(f'   Pearson R: {corr_ret:.4f}')
print(f'   P-Value  : {p_ret:.4e}')
if p_ret < 0.01:
    print('   -> (***) Significancia extrema. Eles estao conectados no nivel molecular do fluxo.')

# B. Correlacao do Caminho de Preco (Tendencia Estrutural / Cumulative Path)
corr_path, p_path = stats.pearsonr(df_organic['XAU_Path'], df_organic['WIN_Path'])
print(f'\n2. Correlacao do Caminho de Preco (Similaridade Estrutural Acumulada):')
print(f'   Pearson R: {corr_path:.4f}')
print(f'   P-Value  : {p_path:.4e}')

if corr_path > 0.7:
    print('   -> (***) Sincronia massiva! O caminho geometrico do Ibovespa eh um espelho do DXY/Ouro quando isolamos as noticias.')
elif corr_path > 0.4:
    print('   -> (**) Forte similaridade direcional de longo prazo.')
else:
    print('   -> (-) Caminhos se separam a longo prazo apesar da reacao no M5.')

print('\nObs: O "Caminho de Preco" mede o formato da curva geometrica dos dois ativos no bimestre.')
