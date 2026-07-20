# ASG Hybrid HFT & Vision Agent (IBOVESPA)

## 🎯 Objetivo do Projeto
Este repositório contém a infraestrutura e os estudos microestruturais para a criação de um Agente Híbrido (Quantitativo + Visão Computacional) voltado para operações Day Trade no IBOVESPA (B3). O sistema mescla análise de risco macroeconômico (Ouro - XAUUSD) com o fluxo de ordens intradiário (Tape Reading) do painel A.S.G.

## 📊 1. Fundamentos Quantitativos e Estatísticos (Macro Lead-Lag)
A fundação matemática deste projeto baseia-se na correlação de risco global entre Ativos de Risco (IBOVESPA) e Ativos de Proteção (Ouro/XAUUSD).
* **Banda GARCH D1**: Modelamos a volatilidade diária do IBOVESPA usando Filtro de Kalman e modelo GARCH(1,1). Só buscamos operações nas faixas extremas de distorção estatística.
* **O Veto Macro (Filtro Anti-Armadilha)**: Se o IBOVESPA apresenta um sinal de colapso estrutural (venda forte), o Ouro **DEVE** subir (confirmando a fuga global de capital para segurança). Se o IBOV cai e o Ouro fica estático ou cai junto, a queda do IBOV é uma *Armadilha Institucional (Caça de Stops)*. O modelo quantitativo VETA a venda.

## 👁️ 2. A Física Microestrutural e o Playbook A.S.G
A segunda camada do nosso modelo não lê preços em gráficos, mas lê a dinâmica de leilão via Visão Computacional do painel A.S.G (Ajuste, Micro, Macro, Maker).
Através da dissecação de horas de pregão gravado, isolamos dois *Paretos* (Padrões Ouro):
* **A Ignição**: O preço rompe e se sustenta acima da Linha Azul (Ajuste). Simultaneamente, o fluxo Micro (curto prazo) ganha tração junto com a agressão do Maker (Smart Money). 
* **A Absorção (Exaustão Institucional)**: Os velocímetros de fluxo apontam exaustão compradora máxima, mas o preço resulta em um pavio (wick) sem romper a resistência. O lote institucional passivo absorveu toda a agressão do varejo, antecedendo um desabamento.

## ⚙️ 3. Arquitetura Tecnológica do Agente Híbrido
Não enviamos os cálculos para dentro da infraestrutura pesada do MetaTrader/MQL5. Construímos um pipeline assíncrono e resiliente em Python:
1. **Captura HFT**: Utiliza a biblioteca mss e pygetwindow para focar exclusivamente na janela de transmissão (Zoom) do painel ASG, extraindo frames em milissegundos direto para a memória RAM.
2. **AI Detector**: Envia os frames em Base64 comprimido para a API da **NVIDIA NIM** rodando o modelo open-weight Llama 3.2 Vision Instruct (11b). A IA aplica as regras do Playbook.
3. **Resiliência**: Conta com *Exponential Backoff* de rede e Fallbacks paramétricos contra minimização de janelas e alucinação de JSON.

## 📁 Estrutura do Repositório (Documentação e Logs)
* /vision_agent: Código-fonte do motor de visão computacional em Python.
* /docs/ASG_Playbook.md: Transcrição refinada das regras originais do operacional ASG.
* /docs/ASG_Trap_Analysis.md: Estudo visual dos Frames 29 (Absorção) e 98 (Ignição).
* /docs/System_Architecture.md: Diagrama de Fluxo (Mermaid) do sistema computacional.
* /frames_extraidos.zip: Banco de imagens cru (Ground Truth) para treinamento e auditoria do Agente de Visão.

---
*Projeto auditável. Desenvolvido para execução assistida e validação cruzada.*
