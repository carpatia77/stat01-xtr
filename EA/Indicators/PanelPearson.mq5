//+------------------------------------------------------------------+
//|                                                PanelPearson.mq5  |
//|                                      Copyright 2026, Antigravity |
//+------------------------------------------------------------------+
#property copyright "Antigravity"
#property link      "https://github.com/carpatia77/stat01-xtr"
#property version   "1.00"
#property indicator_chart_window
#property indicator_plots 0

#include <Canvas\Canvas.mqh>

//--- inputs
input string InpMacroSymbol = "BVSPX"; // Ticker do Ativo Macro
input int    InpPeriod      = 20;      // Período (Sempre calculado em M1)

//--- globais
double corr_history[100]; // Armazena os últimos 100 cálculos de correlação

//--- CCanvas variables
CCanvas canvas;
string obj_name = "PearsonPanelGUI";
int panel_width = 300;
int panel_height = 150;

//+------------------------------------------------------------------+
//| Custom indicator initialization function                         |
//+------------------------------------------------------------------+
int OnInit()
  {
   ArrayInitialize(corr_history, EMPTY_VALUE);
   
   // Canvas setup no Canto Inferior Esquerdo
   if(!canvas.CreateBitmapLabel(obj_name, 10, 10, panel_width, panel_height, COLOR_FORMAT_ARGB_NORMALIZE))
     {
      Print("Erro ao criar CCanvas!");
      return INIT_FAILED;
     }
     
   ObjectSetInteger(0, obj_name, OBJPROP_CORNER, CORNER_LEFT_LOWER);
   ObjectSetInteger(0, obj_name, OBJPROP_XDISTANCE, 20);
   ObjectSetInteger(0, obj_name, OBJPROP_YDISTANCE, 60); // Afastado do eixo de tempo inferior
   ObjectSetInteger(0, obj_name, OBJPROP_HIDDEN, true); // Esconde da lista de objetos padrão
   ObjectSetInteger(0, obj_name, OBJPROP_SELECTABLE, true); // Permite selecionar para arrastar
   
   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
//| Custom indicator de-initialization function                      |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   canvas.Destroy();
  }

//+------------------------------------------------------------------+
//| Map correlation [-1.0, 1.0] to Y coordinate [height, 0]          |
//+------------------------------------------------------------------+
int MapY(double value)
  {
   if(value > 1.0) value = 1.0;
   if(value < -1.0) value = -1.0;
   
   int padding = 25; // Espaço no topo para o texto
   int h = panel_height - (padding * 2);
   
   double normalized = (value + 1.0) / 2.0; 
   return panel_height - padding - (int)(normalized * h);
  }

//+------------------------------------------------------------------+
//| Render the GUI Panel                                             |
//+------------------------------------------------------------------+
void DrawPanel()
  {
   // Fundo preto translúcido (Estilo Institucional)
   canvas.Erase(ColorToARGB(clrBlack, 220));
   
   // Borda sutil
   canvas.Rectangle(0, 0, panel_width-1, panel_height-1, ColorToARGB(clrDimGray, 150));
   
   // Níveis de Referência
   int y_plus1 = MapY(1.0);
   int y_plus07 = MapY(0.7);
   int y_zero = MapY(0.0);
   int y_minus07 = MapY(-0.7);
   int y_minus1 = MapY(-1.0);
   
   // Desenha as linhas horizontais de limite
   canvas.Line(0, y_plus1, panel_width, y_plus1, ColorToARGB(clrForestGreen, 100));
   canvas.Line(0, y_plus07, panel_width, y_plus07, ColorToARGB(clrForestGreen, 200));
   canvas.Line(0, y_zero, panel_width, y_zero, ColorToARGB(clrSilver, 150));
   canvas.Line(0, y_minus07, panel_width, y_minus07, ColorToARGB(clrRed, 200));
   canvas.Line(0, y_minus1, panel_width, y_minus1, ColorToARGB(clrRed, 100));
   
   // A cor atual é baseada no valor mais recente (índice 99)
   double current_corr = corr_history[99];
   uint line_color = ColorToARGB(clrSilver, 255);
   
   if(current_corr != EMPTY_VALUE && current_corr != 0.0)
     {
      if(current_corr >= 0.7) line_color = ColorToARGB(clrLimeGreen, 255);
      else if(current_corr <= -0.7) line_color = ColorToARGB(clrOrangeRed, 255);
     }
     
   // Renderiza a linha histórica
   int total_points = 100;
   double step_x = (double)panel_width / (double)(total_points - 1);
   
   for(int i = 1; i < total_points; i++)
     {
      // Validar dados
      if(corr_history[i-1] == EMPTY_VALUE || corr_history[i] == EMPTY_VALUE) continue;
      
      int x1 = (int)((i - 1) * step_x);
      int y1 = MapY(corr_history[i-1]);
      
      int x2 = (int)(i * step_x);
      int y2 = MapY(corr_history[i]);
      
      // Plotar linha com Anti-Aliasing (sem rachar)
      canvas.LineAA(x1, y1, x2, y2, line_color);
      canvas.LineAA(x1, y1-1, x2, y2-1, line_color); // Suave espessura extra
     }
     
   // Renderiza os Textos
   canvas.FontSet("Trebuchet MS", 14, FW_BOLD);
   canvas.TextOut(10, 5, "Corr XAU/BVSPX (M1)", ColorToARGB(clrWhite, 200), TA_LEFT|TA_TOP);
   
   if(current_corr != EMPTY_VALUE && current_corr != 0.0)
     {
      string val_str = StringFormat("%.3f", current_corr);
      canvas.TextOut(panel_width - 10, 5, val_str, line_color, TA_RIGHT|TA_TOP);
     }
     
   // Atualiza o frame na tela
   canvas.Update();
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
   // Desacoplado do timeframe do gráfico atual. 
   // Vamos buscar SEMPRE os dados do M1 (PERIOD_M1).
   
   int total_history = 100;
   int needed_bars = total_history + InpPeriod; // ex: 120 barras do M1
   
   double xau_m1[];
   double mac_m1[];
   
   // Puxa o fechamento exato no M1 para o XAU e para o Ativo Macro
   if(CopyClose(_Symbol, PERIOD_M1, 0, needed_bars, xau_m1) < needed_bars) return 0;
   if(CopyClose(InpMacroSymbol, PERIOD_M1, 0, needed_bars, mac_m1) < needed_bars) return 0;
   
   // O índice 0 em CopyClose (sem ArraySetAsSeries) é o mais antigo.
   // Vamos preencher o corr_history[0...99], onde 99 é o momento atual.
   for(int i = 0; i < total_history; i++)
     {
      double sum_x = 0;
      double sum_y = 0;
      
      // Janela rolante de "InpPeriod" barras
      for(int j = 0; j < InpPeriod; j++)
        {
         sum_x += xau_m1[i + j];
         sum_y += mac_m1[i + j];
        }
        
      double mean_x = sum_x / InpPeriod;
      double mean_y = sum_y / InpPeriod;
      
      double num = 0;
      double den_x = 0;
      double den_y = 0;
      
      for(int j = 0; j < InpPeriod; j++)
        {
         double dx = xau_m1[i + j] - mean_x;
         double dy = mac_m1[i + j] - mean_y;
         
         num += dx * dy;
         den_x += dx * dx;
         den_y += dy * dy;
        }
        
      if(den_x * den_y > 0)
         corr_history[i] = num / MathSqrt(den_x * den_y);
      else
         corr_history[i] = 0.0;
     }
     
   // Renderiza no Canvas
   DrawPanel();

   return(rates_total);
  }
//+------------------------------------------------------------------+
