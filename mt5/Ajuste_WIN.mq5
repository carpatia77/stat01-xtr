//+------------------------------------------------------------------+
//|                                                  Ajuste_WIN.mq5  |
//|                                          Engenharia Quantitativa |
//+------------------------------------------------------------------+
#property copyright "Auditoria Institucional"
#property version   "1.01"
#property indicator_chart_window
#property indicator_buffers 1
#property indicator_plots   1

// --- Configuração Visual da Linha ---
#property indicator_label1  "Ajuste B3"
#property indicator_type1   DRAW_LINE
#property indicator_color1  clrLime       // Cor da linha do ajuste
#property indicator_style1  STYLE_SOLID
#property indicator_width1  2             // Espessura da linha

// --- Parâmetros Oficiais B3 (Índice) ---
input int InpStartHour = 17; // Hora de Início do Cálculo
input int InpStartMin  = 0;  // Minuto de Início
input int InpEndHour   = 17; // Hora de Fim do Cálculo
input int InpEndMin    = 15; // Minuto de Fim

double AjusteBuffer[];

//+------------------------------------------------------------------+
//| Custom indicator initialization function                         |
//+------------------------------------------------------------------+
int OnInit()
  {
   SetIndexBuffer(0, AjusteBuffer, INDICATOR_DATA);
   PlotIndexSetDouble(0, PLOT_EMPTY_VALUE, 0.0);
   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
//| Custom indicator iteration function                              |
//+------------------------------------------------------------------+
int OnCalculate(const int rates_total,
                const int prev_calculated,
                const datetime &time[],
                const double &open[],
                const double &high[],
                const double &low[],
                const double &close[],
                const long &tick_volume[],
                const long &volume[],
                const int &spread[])
  {
   // Garante a leitura da esquerda para a direita (cronológica)
   ArraySetAsSeries(time, false);
   ArraySetAsSeries(close, false);
   ArraySetAsSeries(volume, false);
   ArraySetAsSeries(tick_volume, false);

   // Variáveis estáticas para manter a memória do cálculo entre os ticks
   static double last_ajuste = 0.0;
   static double acc_vol = 0.0;
   static double acc_money = 0.0;
   static int last_day = -1;

   // Otimização: processa apenas os novos candles/ticks
   int limit = (prev_calculated == 0) ? 0 : prev_calculated - 1;

   for(int i = limit; i < rates_total; i++)
     {
      MqlDateTime dt;
      TimeToStruct(time[i], dt);

      int current_minutes = dt.hour * 60 + dt.min;
      int start_minutes = InpStartHour * 60 + InpStartMin;
      int end_minutes = InpEndHour * 60 + InpEndMin;

      // Reseta a calculadora na PRIMEIRA barra do dia dentro da janela de
      // ajuste da B3 -- não exige mais minuto exato (17:00:00). A versão
      // anterior só resetava se existisse uma barra exatamente nesse
      // minuto; faltando ela (gap de feed, horário de verão, indicador
      // anexado no meio do pregão), o reset nunca disparava e o
      // indicador congelava no último ajuste válido pra sempre, porque
      // a condição de acumulação abaixo (dt.day == last_day) passava a
      // ser falsa pro dia inteiro.
      bool dentro_da_janela = (current_minutes >= start_minutes && current_minutes < end_minutes);
      if(dentro_da_janela && dt.day != last_day)
        {
         acc_vol = 0.0;
         acc_money = 0.0;
         last_day = dt.day;
        }

      // Motor VWAP: Acumula volume e preço APENAS dentro da janela da B3
      if(dentro_da_janela && dt.day == last_day)
        {
         // Usa o Volume Real da B3. Se falhar, usa o Tick Volume como contingência.
         double vol = (double)volume[i];
         if(vol <= 0) vol = (double)tick_volume[i];

         if(vol > 0)
           {
            acc_vol += vol;
            acc_money += close[i] * vol;
            last_ajuste = acc_money / acc_vol; // Cálculo exato da VWAP
           }
        }

      // Projeta o ajuste calculado. Antes do primeiro cálculo, mantém zerado.
      AjusteBuffer[i] = (last_ajuste > 0) ? last_ajuste : 0.0;
     }

   return(rates_total);
  }
//+------------------------------------------------------------------+
