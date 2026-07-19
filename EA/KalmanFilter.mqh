
//+------------------------------------------------------------------+
//|                                                 KalmanFilter.mqh |
//|                                          Engenharia Quantitativa |
//+------------------------------------------------------------------+
#property copyright "Auditoria Institucional"
#property version   "1.00"

// Variáveis de estado global para a recursão do Kalman
double prev_state = 0.0;
double prev_covariance = 1.0;
bool kalman_initialized = false;

//+------------------------------------------------------------------+
//| Função principal do Filtro de Kalman 1D                          |
//| Baseado na pesquisa MQL5 e nos testes de Python (Ajuste + GARCH) |
//+------------------------------------------------------------------+
double KalmanFilter(double price, double measurement_variance=0.01, double process_variance=0.0001)
{
    // Se for a primeira inicialização do estado
    if (!kalman_initialized) {
        prev_state = price;
        kalman_initialized = true;
    }

    // Etapa de Previsão (Prediction step)
    double predicted_state = prev_state;
    double predicted_covariance = prev_covariance + process_variance;

    // Cálculo do Ganho de Kalman (Kalman gain)
    double kalman_gain = predicted_covariance / (predicted_covariance + measurement_variance);

    // Etapa de Atualização (Update step)
    double updated_state = predicted_state + kalman_gain * (price - predicted_state);
    double updated_covariance = (1.0 - kalman_gain) * predicted_covariance;

    // Guarda os estados para a próxima barra/iteração
    prev_state = updated_state;
    prev_covariance = updated_covariance;
    
    return updated_state;
}
//+------------------------------------------------------------------+

