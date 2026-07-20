import time
import os
import colorama
from colorama import Fore, Style
from capture_engine import capture_and_encode
from ai_detector import detect_pattern

# Inicializa as cores do terminal
colorama.init(autoreset=True)

def clear_console():
    os.system('cls' if os.name == 'nt' else 'clear')

def main_loop(interval_seconds=1.0):
    print(f"{Fore.CYAN}Iniciando Agente de Visão ASG (Latência HFT)...{Style.RESET_ALL}")
    print("Pressione Ctrl+C para parar.\n")
    
    # Aguarda a chave de API
    if os.environ.get("GEMINI_API_KEY") is None or os.environ.get("GEMINI_API_KEY") == "SUA_CHAVE_AQUI":
        print(f"{Fore.RED}[ERRO] GEMINI_API_KEY não encontrada nas variáveis de ambiente.{Style.RESET_ALL}")
        print("Antes de rodar, execute: setx GEMINI_API_KEY \"sua_chave\"")
        return

    while True:
        try:
            start_total = time.time()
            
            # 1. Captura da Tela (Ultra rápido ~50ms)
            b64, img = capture_and_encode()
            
            # 2. Inferência com IA de Visão
            resultado = detect_pattern(img)
            
            # 3. Cálculo de Latência
            latencia = time.time() - start_total
            
            # 4. Formatação Visual do Alerta
            padrao = resultado.get("Padrao", "NEUTRO")
            
            clear_console()
            print(f"[{time.strftime('%H:%M:%S')}] Latência Total: {latencia:.2f}s")
            print("-" * 50)
            
            if padrao == "IGNICAO":
                print(f"{Fore.GREEN}{Style.BRIGHT}★★★ ALERTA: IGNIÇÃO DETECTADA ★★★{Style.RESET_ALL}")
            elif padrao == "ABSORCAO":
                print(f"{Fore.RED}{Style.BRIGHT}★★★ ALERTA: ABSORÇÃO (ARMADILHA) DETECTADA ★★★{Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}Neutro - Aguardando setups...{Style.RESET_ALL}")
                
            print(f"Maker : {resultado.get('Maker', 'N/A')}")
            print(f"Micro : {resultado.get('Micro', 'N/A')}")
            print(f"Vela  : {resultado.get('Vela', 'N/A')}")
            print(f"\nVeredito: {resultado.get('Veredito', 'N/A')}")
            print("-" * 50)
            
            time.sleep(interval_seconds)
            
        except KeyboardInterrupt:
            print(f"\n{Fore.CYAN}Agente de Visão Encerrado.{Style.RESET_ALL}")
            break
        except Exception as e:
            print(f"{Fore.RED}[ERRO NO LOOP]: {e}{Style.RESET_ALL}")
            time.sleep(2)

if __name__ == "__main__":
    main_loop(interval_seconds=2.0) # A cada 2 segundos tira uma 'foto'
