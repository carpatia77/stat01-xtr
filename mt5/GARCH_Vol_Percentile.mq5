//+------------------------------------------------------------------+
//|                                        GARCH_Vol_Percentile.mq5   |
//|  Plota bandas de volatilidade condicional (GARCH/EGARCH/GJR)     |
//|  a partir de gregas (omega, alpha, beta, gamma) inseridas         |
//|  manualmente, calibradas offline (Python) contra dados diarios.  |
//|                                                                    |
//|  Reconstrucao independente, sem acesso ao codigo-fonte de         |
//|  indicadores fechados de terceiros — apenas inspirado na          |
//|  convencao de nomes de inputs observada na UI de um indicador     |
//|  ja em uso (GARCH_COMPLETO), para familiaridade do usuario.       |
//+------------------------------------------------------------------+
#property copyright "stat01-xtr"
#property indicator_chart_window
#property indicator_buffers 0
#property indicator_plots   0

//======================================================================
// === 1. Tipo de Volatilidade ===
//======================================================================
enum ENUM_VOL_MODE
  {
   VOL_CONDICIONAL,   // Vol condicional filtrada + forecast N dias
  };
input ENUM_VOL_MODE InpVolMode = VOL_CONDICIONAL;

//======================================================================
// === 2. Modelo Principal ===
//======================================================================
enum ENUM_MODEL
  {
   MODEL_GARCH_PQ,    // GARCH(p,q) — sem assimetria
   MODEL_EGARCH_PQ,   // EGARCH(p,o,q) — assimetria em log-variancia
   MODEL_GJR_PQ,      // GJR-GARCH(p,o,q) — assimetria em nivel
  };
input ENUM_MODEL InpModel = MODEL_GARCH_PQ;

//======================================================================
// === 3. GARCH(p,q) & GJR-GARCH (reaproveita Omega/Alpha/Beta) ===
//======================================================================
input double InpGarchOmega = 0.00000439;
input double InpGarchAlpha = 0.031597;   // alpha[1] (+ alpha[2] abaixo se p=2)
input double InpGarchAlpha2 = 0.0;       // alpha[2], 0 = GARCH(1,q)
input double InpGarchBeta  = 0.950707;   // beta[1]
input double InpGarchBeta2 = 0.0;        // beta[2], 0 = GARCH(p,1)
input ENUM_LINE_STYLE InpGarchStyle = STYLE_SOLID;

//======================================================================
// === 4. EGARCH(p,o,q) ===
//======================================================================
input double InpEgarchOmega = -0.386095;
input double InpEgarchAlpha = 0.070563;
input double InpEgarchAlpha2 = 0.0;
input double InpEgarchBeta  = 0.958068;
input double InpEgarchBeta2 = 0.0;
input double InpEgarchGamma = -0.239216;
input double InpEgarchGamma2 = 0.0;
input ENUM_LINE_STYLE InpEgarchStyle = STYLE_DOT;

//======================================================================
// === 5. GJR-GARCH — parametro extra (usa Omega/Alpha/Beta da secao 3)
//======================================================================
input double InpGJRGamma = 0.0;
input ENUM_LINE_STYLE InpGJRStyle = STYLE_DASH;

//======================================================================
// === 6. Distribuicao (para o quantil das bandas) ===
//======================================================================
enum ENUM_DIST
  {
   DIST_NORMAL,       // z-score da normal padrao
   DIST_STUDENT_T,     // quantil t-Student com Nu graus de liberdade
  };
input ENUM_DIST InpDist = DIST_NORMAL;
input double    InpNu   = 6.0;           // graus de liberdade (só usado se DIST_STUDENT_T)

//======================================================================
// === 7. Percentis / Visual ===
//======================================================================
enum ENUM_PCTL_MODE
  {
   PCTL_GEOMETRICO,    // fracao linear da distancia (compat. com indicadores antigos)
   PCTL_ESTATISTICO,   // percentil real via quantil da distribuicao (recomendado)
  };
input ENUM_PCTL_MODE InpPctlMode   = PCTL_ESTATISTICO;
input int             InpDivisions = 4;              // usado só no modo GEOMETRICO
input string          InpPercentiles = "5,25,50,75,95"; // usado só no modo ESTATISTICO
input int             InpHorizonDays = 5;             // N dias a frente (banda "Condicional N-Dias")
input double          InpConfidenceBand = 0.95;        // IC externo (ex.: 0.95 -> ±1.96 sigma)

input color            InpBaseColor  = clrYellow;
input color            InpUpperColor = clrLime;
input color            InpLowerColor = clrWhite;
input int              InpLineWidth  = 1;
input bool             InpShowLabels = true;
input int              InpLabelShift = 5;

//======================================================================
// === 8. Recursao Condicional ===
//======================================================================
input int InpLookbackDays = 10; // dias de historico D1 p/ "aquecer" a recursao
                                 // AVISO: com beta alto (>0.95) a meia-vida da
                                 // persistencia e ~14-34 dias; 10 dias so funciona
                                 // bem porque semeamos com a variancia incondicional
                                 // (omega/(1-alpha-beta)), nao com zero.

//======================================================================
// Constantes numericas
//======================================================================
#define OBJ_PREFIX "GVP_"

//+------------------------------------------------------------------+
//| Aproximacao racional de Acklam para a normal inversa (z-score)   |
//| Erro < 1.15e-9 para p em (0,1). Padrao de mercado, sem libs ext. |
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
//| Quantil t-Student via aproximacao de Cornish-Fisher a partir do  |
//| z-score normal (precisao adequada para bandas visuais; nao usar |
//| para inferencia formal). Nu = graus de liberdade.                |
//+------------------------------------------------------------------+
double StudentTInv(double p, double nu)
  {
   double z = NormSInv(p);
   if(nu <= 4.0) nu = 4.01; // evita divisao instavel perto de nu=2..4
   double g1 = (z*z*z + z) / 4.0;
   double g2 = (5.0*MathPow(z,5) + 16.0*MathPow(z,3) + 3.0*z) / 96.0;
   double g3 = (3.0*MathPow(z,7) + 19.0*MathPow(z,5) + 17.0*MathPow(z,3) - 15.0*z) / 384.0;
   double t  = z + g1/nu + g2/(nu*nu) + g3/(nu*nu*nu);
   return(t);
  }

//+------------------------------------------------------------------+
//| Quantil generico conforme InpDist                                |
//+------------------------------------------------------------------+
double Quantile(double p)
  {
   if(InpDist == DIST_STUDENT_T)
     {
      // reescala para variancia unitaria: t com Nu df tem var = Nu/(Nu-2)
      double tq = StudentTInv(p, InpNu);
      double scale = MathSqrt((InpNu-2.0)/InpNu);
      return(tq*scale);
     }
   return(NormSInv(p));
  }

//+------------------------------------------------------------------+
//| Log-gamma via aproximacao de Lanczos (g=7, 9 termos).             |
//| MQL5 nao tem MathGamma nativo — implementado aqui para o E|z| do |
//| Student-t. Precisao ~1e-10 para x>0.                              |
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
     {
      // reflexao: Gamma(x)*Gamma(1-x) = pi/sin(pi*x)
      return(MathLog(M_PI / MathSin(M_PI*x)) - LanczosLogGamma(1.0-x));
     }
   x -= 1.0;
   double a = g_coef[0];
   double t = x + 7.5;
   for(int i=1; i<9; i++)
      a += g_coef[i] / (x + i);
   return(0.5*MathLog(2.0*M_PI) + (x+0.5)*MathLog(t) - t + MathLog(a));
  }

//+------------------------------------------------------------------+
//| E|z| — valor esperado de |choque| padronizado (usado no forecast |
//| multi-dia do EGARCH quando assumimos choque futuro nulo)          |
//+------------------------------------------------------------------+
double ExpectedAbsZ()
  {
   if(InpDist == DIST_STUDENT_T && InpNu > 2.0)
     {
      // E|t_nu| (t "cru", var=nu/(nu-2)) = 2*sqrt(nu-2)*Gamma((nu+1)/2)
      //                                     / ((nu-1)*sqrt(pi*nu)*Gamma(nu/2))
      // reescalado para variancia unitaria multiplicando por sqrt((nu-2)/nu)
      double nu = InpNu;
      double logNum = MathLog(2.0) + 0.5*MathLog(nu-2.0) + LanczosLogGamma((nu+1.0)/2.0);
      double logDen = MathLog(nu-1.0) + 0.5*MathLog(M_PI*nu) + LanczosLogGamma(nu/2.0);
      double eAbsT_raw = MathExp(logNum - logDen);
      double eAbsT = eAbsT_raw * MathSqrt((nu-2.0)/nu);
      if(!MathIsValidNumber(eAbsT) || eAbsT <= 0.0)
         return(MathSqrt(2.0/M_PI));
      return(eAbsT);
     }
   return(MathSqrt(2.0/M_PI)); // ~0.797885, normal padrao
  }

//+------------------------------------------------------------------+
//| Estrutura com o resultado do calculo                              |
//+------------------------------------------------------------------+
struct SForecast
  {
   double baseClose;      // ultimo fechamento diario conhecido
   double sigmaDaily;     // sigma (desvio-padrao) do proximo dia, fração (nao %)
   double sigmaCumN;      // sigma acumulado dos proximos N dias
   datetime baseTime;     // horario do ultimo fechamento diario
  };

//+------------------------------------------------------------------+
//| Roda a recursao GARCH/EGARCH/GJR sobre os ultimos InpLookbackDays|
//| retornos diarios (D1) e projeta N dias a frente.                  |
//+------------------------------------------------------------------+
bool ComputeForecast(SForecast &out)
  {
   int need = InpLookbackDays + 3;
   MqlRates rates[];
   ArraySetAsSeries(rates, true);
   int copied = CopyRates(_Symbol, PERIOD_D1, 0, need, rates);
   if(copied < need)
     {
      Print("GARCH_Vol_Percentile: histórico D1 insuficiente (", copied, "/", need, ")");
      return(false);
     }

   // retornos log diarios, index 0 = mais recente
   int n = copied - 1;
   double eps[];
   ArrayResize(eps, n);
   for(int i=0; i<n; i++)
      eps[i] = MathLog(rates[i].close / rates[i+1].close);

   double a1=InpGarchAlpha, a2=InpGarchAlpha2, b1=InpGarchBeta, b2=InpGarchBeta2;
   double omega = InpGarchOmega;
   double g1=0.0, g2=0.0;

   if(InpModel == MODEL_EGARCH_PQ)
     {
      omega = InpEgarchOmega; a1=InpEgarchAlpha; a2=InpEgarchAlpha2;
      b1=InpEgarchBeta; b2=InpEgarchBeta2; g1=InpEgarchGamma; g2=InpEgarchGamma2;
     }
   else if(InpModel == MODEL_GJR_PQ)
     {
      g1 = InpGJRGamma; // reaproveita omega/alpha/beta da secao GARCH
     }

   double aSum=a1+a2, bSum=b1+b2, gSum=g1+g2;
   double Eabsz = ExpectedAbsZ();

   // --- semente: variancia incondicional (evita drift do seed em 10 dias) ---
   double sigma2, lnsigma2 = 0.0;
   if(InpModel == MODEL_EGARCH_PQ)
     {
      double denom = 1.0 - bSum;
      lnsigma2 = (MathAbs(denom) > 1e-8) ? omega/denom : omega;
      sigma2 = MathExp(lnsigma2);
     }
   else
     {
      double denom = 1.0 - aSum - bSum;
      sigma2 = (denom > 1e-8) ? omega/denom : omega*100.0; // fallback se quase-integrado
     }

   // --- recursao "filtrada": varre do dado mais antigo ao mais novo ---
   // eps[] esta em ordem decrescente de tempo (0=recente); percorremos
   // de tras pra frente (mais antigo primeiro) para simular o dia a dia.
   // IMPORTANTE: o loop precisa incluir k=0 (retorno mais recente) —
   // sem isso o forecast fica sempre "um dia atrasado".
   double sigma2_prev = sigma2, lnsigma2_prev = lnsigma2;
   for(int k=n-1; k>=0; k--)
     {
      double e = eps[k];        // choque do dia mais antigo -> mais novo
      double sd_prev = MathSqrt(MathMax(sigma2_prev, 1e-14));
      double z = e / sd_prev;

      double sigma2_new, lnsigma2_new;
      if(InpModel == MODEL_EGARCH_PQ)
        {
         lnsigma2_new = omega + bSum*lnsigma2_prev + a1*(MathAbs(z)-Eabsz) + g1*z;
         sigma2_new = MathExp(lnsigma2_new);
        }
      else if(InpModel == MODEL_GJR_PQ)
        {
         double ind = (e < 0.0) ? 1.0 : 0.0;
         sigma2_new = omega + (aSum + gSum*ind)*e*e + bSum*sigma2_prev;
         lnsigma2_new = MathLog(MathMax(sigma2_new,1e-14));
        }
      else // GARCH puro
        {
         sigma2_new = omega + aSum*e*e + bSum*sigma2_prev;
         lnsigma2_new = MathLog(MathMax(sigma2_new,1e-14));
        }
      sigma2_prev = sigma2_new;
      lnsigma2_prev = lnsigma2_new;
     }

   // sigma2_prev agora e o forecast 1-passo-a-frente (usa o choque de ontem)
   double sigma2_1 = sigma2_prev;

   // --- forecast multi-dia (choque futuro esperado = 0) ---
   double sumVar = 0.0;
   double s2 = sigma2_1;
   double ln_s2 = lnsigma2_prev;
   double sigma2_uncond = (InpModel==MODEL_EGARCH_PQ) ? MathExp(lnsigma2) : sigma2;

   for(int h=1; h<=InpHorizonDays; h++)
     {
      if(h > 1)
        {
         if(InpModel == MODEL_EGARCH_PQ)
           {
            // com z=0 esperado: termo alpha*(E|z|-E|z|)=0, gamma*0=0
            ln_s2 = omega + bSum*ln_s2;
            s2 = MathExp(ln_s2);
           }
         else if(InpModel == MODEL_GJR_PQ)
           {
            // E[I(e<0)] ~= 0.5 sob simetria (aprox.)
            s2 = omega + (aSum + 0.5*gSum)*s2 + bSum*s2; // E[e^2]=s2 (nivel anterior)
           }
         else
           {
            s2 = sigma2_uncond + MathPow(aSum+bSum, h-1)*(sigma2_1 - sigma2_uncond);
           }
        }
      sumVar += s2;
     }

   out.baseClose  = rates[0].close;
   out.baseTime   = rates[0].time;
   out.sigmaDaily = MathSqrt(MathMax(sigma2_1,0.0));
   out.sigmaCumN  = MathSqrt(MathMax(sumVar,0.0));
   return(true);
  }

//+------------------------------------------------------------------+
//| Desenha uma linha horizontal com rotulo                          |
//+------------------------------------------------------------------+
void DrawLevel(string name, double price, color clr, ENUM_LINE_STYLE style,
               string label, int width)
  {
   string objName = OBJ_PREFIX + name;
   if(ObjectFind(0, objName) < 0)
      ObjectCreate(0, objName, OBJ_HLINE, 0, 0, price);
   ObjectSetDouble(0, objName, OBJPROP_PRICE, price);
   ObjectSetInteger(0, objName, OBJPROP_COLOR, clr);
   ObjectSetInteger(0, objName, OBJPROP_STYLE, style);
   ObjectSetInteger(0, objName, OBJPROP_WIDTH, width);
   ObjectSetInteger(0, objName, OBJPROP_BACK, true);
   ObjectSetInteger(0, objName, OBJPROP_SELECTABLE, false);

   if(InpShowLabels)
     {
      string lblName = OBJ_PREFIX + name + "_lbl";
      datetime t = TimeCurrent() + PeriodSeconds(_Period)*InpLabelShift;
      if(ObjectFind(0, lblName) < 0)
         ObjectCreate(0, lblName, OBJ_TEXT, 0, t, price);
      ObjectSetInteger(0, lblName, OBJPROP_TIME, t);
      ObjectSetDouble(0, lblName, OBJPROP_PRICE, price);
      ObjectSetString(0, lblName, OBJPROP_TEXT, label);
      ObjectSetInteger(0, lblName, OBJPROP_COLOR, clr);
      ObjectSetInteger(0, lblName, OBJPROP_FONTSIZE, 8);
     }
  }

//+------------------------------------------------------------------+
//| Limpa todos os objetos do indicador                              |
//+------------------------------------------------------------------+
void ClearObjects()
  {
   int total = ObjectsTotal(0, 0, -1);
   for(int i=total-1; i>=0; i--)
     {
      string nm = ObjectName(0, i, 0, -1);
      if(StringFind(nm, OBJ_PREFIX) == 0)
         ObjectDelete(0, nm);
     }
  }

//+------------------------------------------------------------------+
//| Parseia "5,25,50,75,95" em array de doubles (0..1)                |
//+------------------------------------------------------------------+
int ParsePercentiles(double &out[])
  {
   string parts[];
   int cnt = StringSplit(InpPercentiles, ',', parts);
   ArrayResize(out, cnt);
   for(int i=0; i<cnt; i++)
      out[i] = StringToDouble(parts[i]) / 100.0;
   return(cnt);
  }

//+------------------------------------------------------------------+
//| Redesenha todas as bandas a partir de um SForecast                |
//+------------------------------------------------------------------+
void DrawBands(const SForecast &f)
  {
   ClearObjects();
   ENUM_LINE_STYLE style = (InpModel==MODEL_EGARCH_PQ) ? InpEgarchStyle :
                            (InpModel==MODEL_GJR_PQ)    ? InpGJRStyle   : InpGarchStyle;

   // --- linha base (fechamento de referencia) ---
   DrawLevel("base", f.baseClose, InpBaseColor, STYLE_SOLID,
             StringFormat("Base %s", TimeToString(f.baseTime, TIME_DATE)),
             InpLineWidth);

   // --- banda externa de confianca (ex.: 95% -> ±1.96 sigma) ---
   double zConf = Quantile(0.5 + InpConfidenceBand/2.0);
   double upConf  = f.baseClose * MathExp( zConf * f.sigmaCumN);
   double dnConf  = f.baseClose * MathExp(-zConf * f.sigmaCumN);
   double pctConf = (upConf/f.baseClose - 1.0) * 100.0;
   DrawLevel("conf_up", upConf, InpUpperColor, style,
             StringFormat("+%.4f%% Condicional (%d-Dias)", pctConf, InpHorizonDays),
             InpLineWidth+1);
   DrawLevel("conf_dn", dnConf, InpUpperColor, style,
             StringFormat("-%.4f%% Condicional (%d-Dias)", pctConf, InpHorizonDays),
             InpLineWidth+1);

   // --- niveis intermediarios ---
   if(InpPctlMode == PCTL_ESTATISTICO)
     {
      double pcts[];
      int cnt = ParsePercentiles(pcts);
      for(int i=0; i<cnt; i++)
        {
         double p = pcts[i];
         if(p <= 0.0 || p >= 1.0) continue;
         double z = Quantile(p);
         double price = f.baseClose * MathExp(z * f.sigmaCumN);
         color clr = (p > 0.5) ? InpUpperColor : (p < 0.5) ? InpLowerColor : InpBaseColor;
         DrawLevel(StringFormat("pctl_%d", (int)MathRound(p*100)), price, clr, STYLE_DOT,
                   StringFormat("%.1f%%", p*100.0), InpLineWidth);
        }
     }
   else // PCTL_GEOMETRICO — fracao linear da distancia (compat. legado)
     {
      for(int k=1; k<InpDivisions; k++)
        {
         double frac = (double)k / (double)InpDivisions;
         double upPrice = f.baseClose + frac*(upConf - f.baseClose);
         double dnPrice = f.baseClose + frac*(dnConf - f.baseClose);
         color clrU = InpUpperColor, clrD = InpLowerColor;
         DrawLevel(StringFormat("geo_up_%d", k), upPrice, clrU, STYLE_DOT,
                   StringFormat("%.1f%%", frac*100.0), InpLineWidth);
         DrawLevel(StringFormat("geo_dn_%d", k), dnPrice, clrD, STYLE_DOT,
                   StringFormat("%.1f%%", frac*100.0), InpLineWidth);
        }
     }
  }

//+------------------------------------------------------------------+
datetime g_lastD1Bar = 0;

int OnInit()
  {
   EventSetTimer(30); // reavalia a cada 30s (so redesenha se o D1 fechou)
   return(INIT_SUCCEEDED);
  }

void OnDeinit(const int reason)
  {
   EventKillTimer();
   ClearObjects();
  }

void OnTimer()
  {
   datetime d1time = iTime(_Symbol, PERIOD_D1, 0);
   if(d1time == g_lastD1Bar)
      return; // nada novo, nao redesenha
   g_lastD1Bar = d1time;

   SForecast f;
   if(ComputeForecast(f))
      DrawBands(f);
  }

int OnCalculate(const int rates_total, const int prev_calculated,
                const datetime &time[], const double &open[],
                const double &high[], const double &low[],
                const double &close[], const long &tick_volume[],
                const long &volume[], const int &spread[])
  {
   if(prev_calculated == 0)
     {
      SForecast f;
      if(ComputeForecast(f))
         DrawBands(f);
      g_lastD1Bar = iTime(_Symbol, PERIOD_D1, 0);
     }
   return(rates_total);
  }
//+------------------------------------------------------------------+
