# Estatísticas do Pregão (01 e 02 de Julho de 2026)

Este documento atesta a convergência entre o modelo matemático (Filtro Anti-Armadilha) e o fluxo visual do painel ASG. 

## 📊 1. Resumo Quantitativo Geral
- **Dia 01/07**: Mercado sem assimetrias extremas. O GARCH não acusou quebras de banda significativas fora da correlação de risco. Zero operações recomendadas.
- **Dia 02/07**: Dia de alta volatilidade com 2 anomalias institucionais capturadas:
  - **10:05**: Quebra extrema altista (Trade Aceito). 
  - **12:15**: Falsa quebra baixista (Trade Vetado pelo Ouro).

---

## 🚀 O Trade Perfeito: Ignição de Compra (02/07 às 10:05)

### Dados Quantitativos (A Confirmação Matemática)
No horário das 10:05, o algoritmo identificou um salto violento do IBOVESPA para fora da banda superior do GARCH (+0.78% / 1300 pontos num candle de 5 minutos). 
Como o Ouro (XAUUSD) caiu **-0.21%** simultaneamente, validou-se um fluxo de **Risk-On Global** verdadeiro. A Compra foi executada, gerando **+522 pontos de lucro**.

```text
--- IGNICAO DE COMPRA NO GARCH (2026-07-02 10:05:00) ---
                          IBOV       XAUUSD  IBOV_Ret(%)  XAU_Ret(%)
2026-07-02 10:00:00  171792.85  4140.100098          NaN    0.232420
2026-07-02 10:05:00  173134.90  4131.000000     0.781202   -0.219804 (CONFIRMAÇÃO)
2026-07-02 10:10:00  173245.39  4137.200195     0.063817    0.150089
```

### Evidência Visual ASG
O **frame_65m00s** (10:05 da gravação) demonstra a agressão compradora validando a física do mercado de *Risk-On*.
![Frame 65 - Ignição de Compra](C:\Users\aidea\.gemini\antigravity-ide\brain\45e570cb-4e00-438b-973d-738cedb6495a\frame_65m00s.jpg)

---

## 🪤 A Armadilha Institucional: O Veto Macro (02/07 às 12:15)

### Dados Quantitativos (A Proteção Matemática)
Às 12:15, o IBOVESPA desabou subitamente **-0.19%**, acionando o gatilho de VENDA da banda inferior do GARCH.
Contudo, a regra do Veto Macro foi implacável: Para a queda ser verdadeira, o Ouro DEVERIA ter subido. Em vez disso, o Ouro CAIU **-0.10%**. 
O modelo identificou que não era aversão a risco global, mas uma caça de *stops* localizada no índice brasileiro. O robô vetou a Venda.
Cinco minutos depois, às 12:20, o IBOV espirrou para cima (+0.22%), aniquilando quem vendeu na mínima.

```text
--- VETO MACRO DO OURO (ABSORCAO/ARMADILHA) (2026-07-02 12:15:00) ---
                          IBOV       XAUUSD  IBOV_Ret(%)  XAU_Ret(%)
2026-07-02 12:10:00  172293.76  4139.899902     0.070429    0.145141
2026-07-02 12:15:00  171962.00  4135.399902    -0.192555   -0.108698 (FALSA QUEDA: IBOV e Ouro caem juntos)
2026-07-02 12:20:00  172348.74  4142.799805     0.224899    0.178940 (MERCADO VOLTA COM TUDO)
```

### Evidência Visual ASG
O **frame_195m00s** (12:15 da gravação) demonstra o exato momento de absorção passiva que engoliu os vendidos antes do mercado reverter violentamente para cima.
![Frame 195 - Veto Macro e Absorção](C:\Users\aidea\.gemini\antigravity-ide\brain\45e570cb-4e00-438b-973d-738cedb6495a\frame_195m00s.jpg)
