//+------------------------------------------------------------------+
//|                                        GARCH_Vol_Percentile.mq5   |
//|  Bandas de volatilidade condicional (GARCH/EGARCH/GJR) plotadas   |
//|  como BUFFERS continuos (nao objetos), formando uma "escadinha"   |
//|  diaria sobre qualquer timeframe (M5, M15, H1...).                |
//|                                                                    |
//|  Gregas (omega, alpha, beta, gamma) inseridas manualmente,        |
//|  calibradas offline (pipeline Python) contra dados diarios.       |
//+------------------------------------------------------------------+
#property copyright "stat01-xtr"
#property indicator_chart_window

// 1 base + 2 confianca + 4 pares de percentil (ate 4 niveis simetricos,
// cobre a config default "5,25,50,75,95" com folga pra 2 pares extras).
// MQL5 exige numero de buffers FIXO na compilacao -- nao existe forma de
// tornar isso dinamico a partir da string InpPercentiles em runtime.
#define N_PCTL_PAIRS 4
#property indicator_buffers (3 + 2*N_PCTL_PAIRS)
#property indicator_plots   (3 + 2*N_PCTL_PAIRS)

#property indicator_label1  "Base"
#property indicator_type1   DRAW_LINE
#property indicator_label2  "Conf+"
#property indicator_type2   DRAW_LINE
#property indicator_label3  "Conf-"
#property indicator_type3   DRAW_LINE
#property indicator_label4  "Pctl+1"
#property indicator_type4   DRAW_LINE
#property indicator_label5  "Pctl-1"
#property indicator_type5   DRAW_LINE
#property indicator_label6  "Pctl+2"
#property indicator_type6   DRAW_LINE
#property indicator_label7  "Pctl-2"
#property indicator_type7   DRAW_LINE
#property indicator_label8  "Pctl+3"
#property indicator_type8   DRAW_LINE
#property indicator_label9  "Pctl-3"
#property indicator_type9   DRAW_LINE
#property indicator_label10 "Pctl+4"
#property indicator_type10  DRAW_LINE
#property indicator_label11 "Pctl-4"
#property indicator_type11  DRAW_LINE

//======================================================================
// === 1. Modelo ===
// O Report 1 (garch_analyzer.py) SEMPRE entrega Omega/Alpha/Beta/Gamma
// ja SOMADOS entre defasagens. So existe UM numero por grega pra colar
// aqui, nao interessa o modelo. Copie as 4 colunas (Ω, α, β, γ) direto
// da linha do ativo no .txt e selecione o Modelo que aparece na mesma linha.
//======================================================================
enum ENUM_MODEL
  {
   MODEL_GARCH_PQ,    // GARCH(p,q) ou GARCH-GJR sem gamma -- sem assimetria
   MODEL_EGARCH_PQ,   // EGARCH(p,o,q) -- assimetria em log-variancia
   MODEL_GJR_PQ,      // GJR-GARCH(p,o,q) -- assimetria em nivel
  };
input ENUM_MODEL InpModel = MODEL_EGARCH_PQ;

input double InpOmega = -0.070664533452;
input double InpAlpha = 0.07253778;
input double InpBeta  = 0.99212226;
input double InpGamma = 0.00298651;

//======================================================================
// === 2. Distribuicao (para o quantil das bandas) ===
//======================================================================
enum ENUM_DIST
  {
   DIST_NORMAL,
   DIST_STUDENT_T,
  };
input ENUM_DIST InpDist = DIST_NORMAL;
input double    InpNu   = 6.0;  // graus de liberdade (so usado se DIST_STUDENT_T)

//======================================================================
// === 3. Percentis / Visual ===
//======================================================================
enum ENUM_PCTL_MODE
  {
   PCTL_GEOMETRICO,    // fracao linear da distancia (compat. com indicadores antigos)
   PCTL_ESTATISTICO,   // percentil real via quantil da distribuicao (recomendado)
  };
input ENUM_PCTL_MODE InpPctlMode      = PCTL_ESTATISTICO;
input int             InpDivisions    = 4;  // usado so no modo GEOMETRICO
// Ate N_PCTL_PAIRS pares simetricos (ex.: "5,95" e "25,75" -> 2 pares).
// Valores fora de pares (ex.: um "50" sozinho, que coincide com a base)
// sao ignorados -- nao ha buffer dedicado pra ele, seria redundante.
input string          InpPercentiles  = "5,25,50,75,95";
input int             InpHorizonDays  = 5;     // N dias a frente (banda "Condicional N-Dias")
input double          InpConfidenceBand = 0.95; // IC externo (ex.: 0.95 -> ±1.96 sigma)

input color InpBaseColor  = clrYellow;  // linha base (fechamento de referencia)
input color InpUpperColor = clrLime;    // banda de confianca + pares de percentil, lado de cima
input color InpLowerColor = clrWhite;   // banda de confianca + pares de percentil, lado de baixo

//======================================================================
// === 4. Recursao Condicional ===
//======================================================================
// Quantos anos de historico D1 varrer pra construir a serie diaria de
// sigma. Precisa ser >= tempo suficiente pra "esquecer" o seed inicial
// (meia-vida de persistencia ~14-34 dias com beta~0.95-0.98) -- alguns
// anos e' bastante folga.
input int InpHistoryYears = 5;

//======================================================================
// Buffers
//======================================================================
double BufBase[], BufConfUp[], BufConfDn[];
// MQL5 nao aceita array 2D de buffer indicador -- usamos arrays
// individuais e endereçamos por índice fixo (1..N_PCTL_PAIRS).
double BufPUp1[], BufPDn1[], BufPUp2[], BufPDn2[];
double BufPUp3[], BufPDn3[], BufPUp4[], BufPDn4[];

//======================================================================
// Cache da serie diaria (recalculada 1x por novo fechamento D1)
//======================================================================
datetime g_dayTime[];   // g_dayTime[s] = horario (00:00) do dia no shift s (series: 0=hoje)
double   g_dayBase[];   // fechamento a usar como base da banda EXIBIDA nesse dia
double   g_daySigma1[]; // sigma (fracao) do proximo passo, calculado com dado ate o dia anterior
int      g_dayCountValid = 0;
datetime g_lastRebuild = 0;

//+------------------------------------------------------------------+
//| Aproximacao racional de Acklam para a normal inversa (z-score)   |
//+------------------------------------------------------------------+
double NormSInv(double p)
  {
   if(p <= 0.0) return(-8.0);
   if(p >= 1.0) return( 8.0);

   double a1=-3.969683028665376e+01, a2= 2.209460984245205e+02;
   double a3=-2.759285104469687e+02, a4= 1.383577518672690e+02;
   double a5=-3.066479806614716e+01, a6= 2.506628277459239e+00;
   double b1=-5.447609879822406e+01, b2= 1.615858368580409e+02;
   double b3=-1.556989798598866e+02, b4= 6.680131188771972e+01;
   double b5=-1.328068155288572e+01;
   double c1=-7.784894002430293e-03, c2=-3.223964580411365e-01;
   double c3=-2.400758277161838e+00, c4=-2.549732539343734e+00;
   double c5= 4.374664141464968e+00, c6= 2.938163982698783e+00;
   double d1= 7.784695709041462e-03, d2= 3.224671290700398e-01;
   double d3= 2.445134137142996e+00, d4= 3.754408661907416e+00;

   double p_low = 0.02425, p_high = 1.0 - p_low, q, r, x;

   if(p < p_low)
     {
      q = MathSqrt(-2.0*MathLog(p));
      x = (((((c1*q+c2)*q+c3)*q+c4)*q+c5)*q+c6) /
          ((((d1*q+d2)*q+d3)*q+d4)*q+1.0);
     }
   else if(p <= p_high)
     {
      q = p - 0.5;
      r = q*q;
      x = (((((a1*r+a2)*r+a3)*r+a4)*r+a5)*r+a6)*q /
          (((((b1*r+b2)*r+b3)*r+b4)*r+b5)*r+1.0);
     }
   else
     {
      q = MathSqrt(-2.0*MathLog(1.0-p));
      x = -(((((c1*q+c2)*q+c3)*q+c4)*q+c5)*q+c6) /
           ((((d1*q+d2)*q+d3)*q+d4)*q+1.0);
     }
   return(x);
  }

//+------------------------------------------------------------------+
//| Quantil t-Student via Cornish-Fisher a partir do z-score normal   |
//+------------------------------------------------------------------+
double StudentTInv(double p, double nu)
  {
   double z = NormSInv(p);
   if(nu <= 4.0) nu = 4.01;
   double g1 = (z*z*z + z) / 4.0;
   double g2 = (5.0*MathPow(z,5) + 16.0*MathPow(z,3) + 3.0*z) / 96.0;
   double g3 = (3.0*MathPow(z,7) + 19.0*MathPow(z,5) + 17.0*MathPow(z,3) - 15.0*z) / 384.0;
   return(z + g1/nu + g2/(nu*nu) + g3/(nu*nu*nu));
  }

//+------------------------------------------------------------------+
double Quantile(double p)
  {
   if(InpDist == DIST_STUDENT_T)
     {
      double tq = StudentTInv(p, InpNu);
      double scale = MathSqrt((InpNu-2.0)/InpNu);
      return(tq*scale);
     }
   return(NormSInv(p));
  }

//+------------------------------------------------------------------+
//| Log-gamma via Lanczos (MQL5 nao tem MathGamma nativo)             |
//+------------------------------------------------------------------+
double LanczosLogGamma(double x)
  {
   static double g_coef[9] =
     {
      0.99999999999980993, 676.5203681218851, -1259.1392167224028,
      771.32342877765313, -176.61502916214059, 12.507343278686905,
      -0.13857109526572012, 9.9843695780195716e-6, 1.5056327351493116e-7
     };
   if(x < 0.5)
      return(MathLog(M_PI / MathSin(M_PI*x)) - LanczosLogGamma(1.0-x));
   x -= 1.0;
   double a = g_coef[0];
   double t = x + 7.5;
   for(int i=1; i<9; i++)
      a += g_coef[i] / (x + i);
   return(0.5*MathLog(2.0*M_PI) + (x+0.5)*MathLog(t) - t + MathLog(a));
  }

//+------------------------------------------------------------------+
//| E|z| -- usado no forecast multi-dia do EGARCH (choque futuro = 0)|
//+------------------------------------------------------------------+
double ExpectedAbsZ()
  {
   if(InpDist == DIST_STUDENT_T && InpNu > 2.0)
     {
      double nu = InpNu;
      double logNum = MathLog(2.0) + 0.5*MathLog(nu-2.0) + LanczosLogGamma((nu+1.0)/2.0);
      double logDen = MathLog(nu-1.0) + 0.5*MathLog(M_PI*nu) + LanczosLogGamma(nu/2.0);
      double eAbsT = MathExp(logNum - logDen) * MathSqrt((nu-2.0)/nu);
      if(!MathIsValidNumber(eAbsT) || eAbsT <= 0.0)
         return(MathSqrt(2.0/M_PI));
      return(eAbsT);
     }
   return(MathSqrt(2.0/M_PI));
  }

//+------------------------------------------------------------------+
//| Parseia "5,25,50,75,95" em ate N_PCTL_PAIRS pares simetricos      |
//| (p, 100-p). Ignora valores sem par (inclui o 50, que coincide     |
//| com a base) e excedentes alem da capacidade de buffers.           |
//+------------------------------------------------------------------+
int ParsePercentilePairs(double &lo[], double &hi[])
  {
   string parts[];
   int cnt = StringSplit(InpPercentiles, ',', parts);
   double vals[];
   ArrayResize(vals, cnt);
   int nv = 0;
   for(int i=0; i<cnt; i++)
     {
      double v = StringToDouble(parts[i]);
      if(v > 0.0 && v < 50.0) vals[nv++] = v;  // so guarda a metade < 50; o par >50 e' implicito
     }
   ArrayResize(lo, MathMin(nv, N_PCTL_PAIRS));
   ArrayResize(hi, MathMin(nv, N_PCTL_PAIRS));
   int n = 0;
   for(int i=0; i<nv && n<N_PCTL_PAIRS; i++)
     {
      lo[n] = vals[i] / 100.0;
      hi[n] = 1.0 - lo[n];
      n++;
     }
   return(n);
  }

//+------------------------------------------------------------------+
//| Reconstroi a serie diaria de sigma (D1) do zero. So roda quando   |
//| um novo dia D1 fecha (ver deteccao em OnCalculate).               |
//|                                                                    |
//| CUIDADO COM LOOKAHEAD: a barra D1 shift=0 (hoje) pode estar em    |
//| FORMACAO -- seu "close" muda a cada tick. Ela e' EXCLUIDA da      |
//| recursao (nunca usada como retorno realizado). O sigma exibido    |
//| "hoje" usa dados conhecidos ATE ONTEM, e cada dia HISTORICO exibe |
//| a banda que era conhecida no INICIO daquele dia (nunca o proprio  |
//| fechamento do dia sendo mostrado) -- e' o que garante que o       |
//| "backtest visual" nao tenha vies de olhar o futuro.               |
//+------------------------------------------------------------------+
bool RebuildDailySeries()
  {
   int need = MathMax(InpHistoryYears * 252 + 5, 30);
   MqlRates rates[];
   ArraySetAsSeries(rates, true);
   int copied = CopyRates(_Symbol, PERIOD_D1, 0, need, rates);
   if(copied < 5)
     {
      Print("GARCH_Vol_Percentile: histórico D1 insuficiente (", copied, ")");
      return(false);
     }

   // eps[i] = retorno do dia no shift i, usa closes[i]/closes[i+1].
   // i=0 (retorno "de hoje") e' EXCLUIDO -- rates[0].close ainda flutua.
   int m = copied;             // m dias de close disponiveis, shift 0..m-1
   int nEps = m - 1;           // eps[i] definido pra i=0..nEps-1, mas pulamos i=0
   double eps[];
   ArrayResize(eps, nEps);
   for(int i=0; i<nEps; i++)
      eps[i] = MathLog(rates[i].close / rates[i+1].close);

   double omega = InpOmega, aSum = InpAlpha, bSum = InpBeta, gSum = InpGamma;
   double Eabsz = ExpectedAbsZ();

   double sigma2_seed, lnsigma2_seed = 0.0;
   if(InpModel == MODEL_EGARCH_PQ)
     {
      double denom = 1.0 - bSum;
      lnsigma2_seed = (MathAbs(denom) > 1e-8) ? omega/denom : omega;
      sigma2_seed = MathExp(lnsigma2_seed);
     }
   else
     {
      double denom = 1.0 - aSum - bSum;
      sigma2_seed = (denom > 1e-8) ? omega/denom : omega*100.0;
     }

   // Prealoca arrays de saida: um valor de sigma "filtrado" por shift de
   // eps consumido (shift 1..nEps-1 -- pulamos shift 0 por ser a barra
   // em formacao). g_daySigma1[s] = sigma calculado apos consumir o
   // retorno do dia (s+1), i.e., a previsao 1-passo valida PARA o dia s.
   // g_dayBase[s] = fechamento do dia (s+1) (a base dessa previsao).
   ArrayResize(g_dayTime,   nEps);
   ArrayResize(g_dayBase,   nEps);
   ArrayResize(g_daySigma1, nEps);
   ArraySetAsSeries(g_dayTime, true);
   ArraySetAsSeries(g_dayBase, true);
   ArraySetAsSeries(g_daySigma1, true);

   // recursao varre do retorno mais antigo (i=nEps-1) ate o mais novo
   // usavel (i=1); i=0 nunca e consumido.
   double sigma2_prev = sigma2_seed, lnsigma2_prev = lnsigma2_seed;
   int filled = 0;
   for(int i=nEps-1; i>=1; i--)
     {
      double e = eps[i];
      double sd_prev = MathSqrt(MathMax(sigma2_prev, 1e-14));
      double z = e / sd_prev;

      double sigma2_new, lnsigma2_new;
      if(InpModel == MODEL_EGARCH_PQ)
        {
         lnsigma2_new = omega + bSum*lnsigma2_prev + aSum*(MathAbs(z)-Eabsz) + gSum*z;
         sigma2_new = MathExp(lnsigma2_new);
        }
      else if(InpModel == MODEL_GJR_PQ)
        {
         double ind = (e < 0.0) ? 1.0 : 0.0;
         sigma2_new = omega + (aSum + gSum*ind)*e*e + bSum*sigma2_prev;
         lnsigma2_new = MathLog(MathMax(sigma2_new,1e-14));
        }
      else
        {
         sigma2_new = omega + aSum*e*e + bSum*sigma2_prev;
         lnsigma2_new = MathLog(MathMax(sigma2_new,1e-14));
        }
      sigma2_prev = sigma2_new;
      lnsigma2_prev = lnsigma2_new;

      // apos consumir eps[i] (retorno do dia shift i), a previsao 1-passo
      // vale PARA o dia (i-1); a base e' o fechamento do dia i.
      int dayShift = i - 1;      // 0..nEps-2
      g_dayTime[dayShift]   = rates[i].time;   // horario do dia (i), a base
      g_dayBase[dayShift]   = rates[i].close;
      g_daySigma1[dayShift] = MathSqrt(MathMax(sigma2_prev, 0.0));
      filled++;
     }

   g_dayCountValid = filled;
   g_lastRebuild = rates[1].time;  // ultimo dia FECHADO usado (nao o de hoje)
   return(filled > 0);
  }

//+------------------------------------------------------------------+
//| Preenche os buffers de um bar do grafico (qualquer timeframe) a  |
//| partir do dia D1 ao qual ele pertence.                            |
//+------------------------------------------------------------------+
void FillBarBands(int idx, double baseClose, double sigma1)
  {
   // forecast multi-dia (choque futuro esperado = 0), mesma logica do
   // "Condicional (N-Dias)" original.
   double sumVar = 0.0;
   double s2 = sigma1*sigma1;
   double ln_s2 = MathLog(MathMax(s2, 1e-14));
   double omega = InpOmega, aSum = InpAlpha, bSum = InpBeta, gSum = InpGamma;
   double sigma2_uncond;
   if(InpModel == MODEL_EGARCH_PQ)
     {
      double denom = 1.0 - bSum;
      double lnU = (MathAbs(denom) > 1e-8) ? omega/denom : omega;
      sigma2_uncond = MathExp(lnU);
     }
   else
     {
      double denom = 1.0 - aSum - bSum;
      sigma2_uncond = (denom > 1e-8) ? omega/denom : omega*100.0;
     }

   for(int h=1; h<=InpHorizonDays; h++)
     {
      if(h > 1)
        {
         if(InpModel == MODEL_EGARCH_PQ)
           {
            ln_s2 = omega + bSum*ln_s2;
            s2 = MathExp(ln_s2);
           }
         else if(InpModel == MODEL_GJR_PQ)
           {
            s2 = omega + (aSum + 0.5*gSum)*s2 + bSum*s2;
           }
         else
           {
            s2 = sigma2_uncond + MathPow(aSum+bSum, h-1)*(sigma1*sigma1 - sigma2_uncond);
           }
        }
      sumVar += s2;
     }
   double sigmaCumN = MathSqrt(MathMax(sumVar, 0.0));

   BufBase[idx] = baseClose;

   double zConf = Quantile(0.5 + InpConfidenceBand/2.0);
   double upConf = baseClose * MathExp( zConf * sigmaCumN);
   double dnConf = baseClose * MathExp(-zConf * sigmaCumN);
   BufConfUp[idx] = upConf;
   BufConfDn[idx] = dnConf;

   double lo[], hi[];
   int npairs = ParsePercentilePairs(lo, hi);

   double upBuf[N_PCTL_PAIRS], dnBuf[N_PCTL_PAIRS];
   for(int k=0; k<N_PCTL_PAIRS; k++) { upBuf[k] = EMPTY_VALUE; dnBuf[k] = EMPTY_VALUE; }

   for(int k=0; k<npairs; k++)
     {
      if(InpPctlMode == PCTL_ESTATISTICO)
        {
         double zHi = Quantile(hi[k]);
         double zLo = Quantile(lo[k]);
         upBuf[k] = baseClose * MathExp(zHi * sigmaCumN);
         dnBuf[k] = baseClose * MathExp(zLo * sigmaCumN);
        }
      else // PCTL_GEOMETRICO: fracao linear da distancia ate a banda de confianca,
           // posicionada proporcional ao rank do par (k=0 mais perto do centro)
        {
         double f = (double)(k+1) / (double)(npairs+1);
         upBuf[k] = baseClose + f*(upConf - baseClose);
         dnBuf[k] = baseClose + f*(dnConf - baseClose);
        }
     }

   BufPUp1[idx]=upBuf[0]; BufPDn1[idx]=dnBuf[0];
   BufPUp2[idx]=upBuf[1]; BufPDn2[idx]=dnBuf[1];
   BufPUp3[idx]=upBuf[2]; BufPDn3[idx]=dnBuf[2];
   BufPUp4[idx]=upBuf[3]; BufPDn4[idx]=dnBuf[3];
  }

//+------------------------------------------------------------------+
int OnInit()
  {
   SetIndexBuffer(0, BufBase,   INDICATOR_DATA);
   SetIndexBuffer(1, BufConfUp, INDICATOR_DATA);
   SetIndexBuffer(2, BufConfDn, INDICATOR_DATA);
   SetIndexBuffer(3, BufPUp1,   INDICATOR_DATA);
   SetIndexBuffer(4, BufPDn1,   INDICATOR_DATA);
   SetIndexBuffer(5, BufPUp2,   INDICATOR_DATA);
   SetIndexBuffer(6, BufPDn2,   INDICATOR_DATA);
   SetIndexBuffer(7, BufPUp3,   INDICATOR_DATA);
   SetIndexBuffer(8, BufPDn3,   INDICATOR_DATA);
   SetIndexBuffer(9, BufPUp4,   INDICATOR_DATA);
   SetIndexBuffer(10,BufPDn4,   INDICATOR_DATA);

   for(int i=0; i<=10; i++)
      PlotIndexSetDouble(i, PLOT_EMPTY_VALUE, EMPTY_VALUE);

   // --- cores/estilos: sem isso as 11 linhas saem todas parecidas (default
   // do MT5), impossível distinguir "qual banda é qual" só olhando o
   // gráfico. Usa InpBaseColor/InpUpperColor/InpLowerColor (já existiam
   // como input mas nunca estavam conectados a nada) + estilo/espessura
   // crescente conforme a distância do centro, pra diferenciar os pares
   // de percentil mesmo compartilhando a mesma cor.
   PlotIndexSetInteger(0, PLOT_LINE_COLOR, InpBaseColor);
   PlotIndexSetInteger(0, PLOT_LINE_WIDTH, 2);
   PlotIndexSetInteger(0, PLOT_LINE_STYLE, STYLE_SOLID);

   PlotIndexSetInteger(1, PLOT_LINE_COLOR, InpUpperColor);   // conf+ (banda externa, mais grossa)
   PlotIndexSetInteger(1, PLOT_LINE_WIDTH, 2);
   PlotIndexSetInteger(1, PLOT_LINE_STYLE, STYLE_SOLID);
   PlotIndexSetInteger(2, PLOT_LINE_COLOR, InpLowerColor);   // conf-
   PlotIndexSetInteger(2, PLOT_LINE_WIDTH, 2);
   PlotIndexSetInteger(2, PLOT_LINE_STYLE, STYLE_SOLID);

   // pares de percentil: rank 1 = mais perto do centro (pontilhado, fino),
   // rank crescente = mais longe (traços maiores). Nunca usa STYLE_SOLID
   // pra não confundir com a banda de confiança (índices 1/2).
   int pctlStyles[N_PCTL_PAIRS] = { STYLE_DOT, STYLE_DASH, STYLE_DASHDOT, STYLE_DASHDOTDOT };
   int upIdx[N_PCTL_PAIRS] = {3,5,7,9};
   int dnIdx[N_PCTL_PAIRS] = {4,6,8,10};
   for(int k=0; k<N_PCTL_PAIRS; k++)
     {
      PlotIndexSetInteger(upIdx[k], PLOT_LINE_COLOR, InpUpperColor);
      PlotIndexSetInteger(upIdx[k], PLOT_LINE_STYLE, pctlStyles[k]);
      PlotIndexSetInteger(upIdx[k], PLOT_LINE_WIDTH, 1);
      PlotIndexSetInteger(dnIdx[k], PLOT_LINE_COLOR, InpLowerColor);
      PlotIndexSetInteger(dnIdx[k], PLOT_LINE_STYLE, pctlStyles[k]);
      PlotIndexSetInteger(dnIdx[k], PLOT_LINE_WIDTH, 1);
     }

   ArraySetAsSeries(BufBase, false);
   ArraySetAsSeries(BufConfUp, false);
   ArraySetAsSeries(BufConfDn, false);
   ArraySetAsSeries(BufPUp1, false); ArraySetAsSeries(BufPDn1, false);
   ArraySetAsSeries(BufPUp2, false); ArraySetAsSeries(BufPDn2, false);
   ArraySetAsSeries(BufPUp3, false); ArraySetAsSeries(BufPDn3, false);
   ArraySetAsSeries(BufPUp4, false); ArraySetAsSeries(BufPDn4, false);

   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
int OnCalculate(const int rates_total, const int prev_calculated,
                const datetime &time[], const double &open[],
                const double &high[], const double &low[],
                const double &close[], const long &tick_volume[],
                const long &volume[], const int &spread[])
  {
   // recalcula a serie diaria so quando um novo D1 fechar (nao a cada tick)
   datetime lastClosedD1 = iTime(_Symbol, PERIOD_D1, 1);  // shift 1 = ultimo D1 FECHADO
   if(lastClosedD1 != g_lastRebuild || g_dayCountValid == 0)
     {
      if(!RebuildDailySeries())
         return(rates_total);
     }

   int start = (prev_calculated > 1) ? prev_calculated - 1 : 0;

   for(int idx=start; idx<rates_total; idx++)
     {
      // acha a qual dia D1 esse bar pertence e usa a banda daquele dia.
      int d1shift = iBarShift(_Symbol, PERIOD_D1, time[idx], false);
      if(d1shift < 0)
        {
         BufBase[idx]=EMPTY_VALUE; BufConfUp[idx]=EMPTY_VALUE; BufConfDn[idx]=EMPTY_VALUE;
         BufPUp1[idx]=EMPTY_VALUE; BufPDn1[idx]=EMPTY_VALUE;
         BufPUp2[idx]=EMPTY_VALUE; BufPDn2[idx]=EMPTY_VALUE;
         BufPUp3[idx]=EMPTY_VALUE; BufPDn3[idx]=EMPTY_VALUE;
         BufPUp4[idx]=EMPTY_VALUE; BufPDn4[idx]=EMPTY_VALUE;
         continue;
        }
      // g_day*[] esta indexado por "dias atras do hoje-em-formacao";
      // d1shift=0 (hoje) usa g_day*[0] (que ja exclui a barra de hoje da
      // recursao); d1shift=1 (ontem) usa g_day*[1], etc.
      int s = d1shift;
      if(s >= g_dayCountValid)
        {
         BufBase[idx]=EMPTY_VALUE; BufConfUp[idx]=EMPTY_VALUE; BufConfDn[idx]=EMPTY_VALUE;
         BufPUp1[idx]=EMPTY_VALUE; BufPDn1[idx]=EMPTY_VALUE;
         BufPUp2[idx]=EMPTY_VALUE; BufPDn2[idx]=EMPTY_VALUE;
         BufPUp3[idx]=EMPTY_VALUE; BufPDn3[idx]=EMPTY_VALUE;
         BufPUp4[idx]=EMPTY_VALUE; BufPDn4[idx]=EMPTY_VALUE;
         continue;
        }
      FillBarBands(idx, g_dayBase[s], g_daySigma1[s]);
     }

   return(rates_total);
  }
//+------------------------------------------------------------------+
