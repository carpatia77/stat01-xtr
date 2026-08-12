
//+------------------------------------------------------------------+
//|                                                     AjusteB3.mqh |
//|                                          Engenharia Quantitativa |
//+------------------------------------------------------------------+
#property copyright "Auditoria Institucional"
#property version   "1.00"

// Parâmetros Oficiais B3 (Índice)
input int InpStartHour = 17; // Hora de Início do Cálculo
input int InpStartMin  = 0;  // Minuto de Início
input int InpEndHour   = 17; // Hora de Fim do Cálculo
input int InpEndMin    = 15; // Minuto de Fim

double current_ajuste = 0.0;
double acc_money = 0.0;
double acc_vol = 0.0;
int last_day = -1;

//+------------------------------------------------------------------+
//| Calcula o Ajuste B3 (VWAP) no período especificado               |
//+------------------------------------------------------------------+
double CalculateAjuste(datetime time, double price, double volume)
{
    MqlDateTime dt;
    TimeToStruct(time, dt);
    
    // Reseta no início de um novo dia de pregão
    if (dt.day != last_day && dt.hour >= 9) {
        acc_money = 0.0;
        acc_vol = 0.0;
        last_day = dt.day;
    }
    
    // Verifica se está na janela de Ajuste (ex: 17:00 as 17:15)
    int current_mins = dt.hour * 60 + dt.min;
    int start_mins = InpStartHour * 60 + InpStartMin;
    int end_mins = InpEndHour * 60 + InpEndMin;
    
    if (current_mins >= start_mins && current_mins < end_mins) {
        if (volume > 0) {
            acc_money += price * volume;
            acc_vol += volume;
            current_ajuste = acc_money / acc_vol;
        }
    }
    
    return current_ajuste;
}
//+------------------------------------------------------------------+

