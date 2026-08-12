import os
import json
import base64
from typing import Dict, Any
from openai import OpenAI

# Configuração para NVIDIA NIM
# Defina NVIDIA_API_KEY no seu ambiente
NVIDIA_API_KEY = os.environ.get("NVIDIA_API_KEY", "SUA_CHAVE_AQUI")

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=NVIDIA_API_KEY
)

# Modelo Vision da Llama 3.2 rodando gratuitamente via NIM
MODEL_NAME = "meta/llama-3.2-11b-vision-instruct" 
# Alternativa: "meta/llama-3.2-90b-vision-instruct" para mais precisão

PROMPT_PLAYBOOK = """
Você é um analista de microestrutura de mercado especializado no painel A.S.G.
Sua missão é classificar a imagem da tela em uma de três categorias de acordo com o Playbook:
1. "IGNICAO": O preço rompeu acima/abaixo da Linha Azul, a Micro está acelerada na mesma direção e o Ouro não está divergindo.
2. "ABSORCAO": Os velocímetros da Macro/Micro estão apontando forte fluxo, mas o preço termina com um pavio longo (Wick) sem romper a região de liquidez (esforço máximo, resultado nulo).
3. "NEUTRO": Nenhuma armadilha ou ignição detectada no momento.

Analise a imagem base64 fornecida.
Responda APENAS com um JSON válido seguindo esta estrutura, sem markdown ou texto extra:
{
    "Padrao": "IGNICAO" | "ABSORCAO" | "NEUTRO",
    "Maker": "Nivel de forca",
    "Micro": "Nivel de forca",
    "Vela": "Cheia ou Wick",
    "Veredito": "Ação sugerida"
}
"""

def detect_pattern(img_pil, base64_image_str=None) -> Dict[str, Any]:
    """
    Envia a imagem Base64 para a API da NVIDIA NIM e retorna o dict estruturado.
    Para NVIDIA NIM/OpenAI, precisamos passar a imagem diretamente como Base64 URL no array de conteúdo.
    """
    if base64_image_str is None:
        import io
        buffer = io.BytesIO()
        img_pil.save(buffer, format='JPEG', quality=85)
        base64_image_str = base64.b64encode(buffer.getvalue()).decode('utf-8')

    image_url = f"data:image/jpeg;base64,{base64_image_str}"

    MAX_RETRIES = 3
    import time
    for attempt in range(MAX_RETRIES):
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": PROMPT_PLAYBOOK},
                            {
                                "type": "image_url",
                                "image_url": {"url": image_url}
                            }
                        ]
                    }
                ],
                max_tokens=150,
                temperature=0.1,
                timeout=10 # Fallback contra timeouts infinitos
            )
            
            text = response.choices[0].message.content.strip()
            # Resiliência de Parser (limpeza pesada do markdown da IA)
            text = text.replace("```json", "").replace("```", "").replace("\n", "").strip()
            return json.loads(text)
            
        except json.JSONDecodeError as e:
            return {"error": f"JSON Invalido: {e}", "Padrao": "ERRO", "Veredito": "A IA gerou texto livre"}
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt) # Exponential backoff (1s, 2s...)
            else:
                return {"error": str(e), "Padrao": "ERRO", "Veredito": "Falha na API NIM (Rate Limit ou Timeout)"}

if __name__ == "__main__":
    # Teste isolado
    from capture_engine import capture_and_encode
    import time
    
    print("Capturando tela...")
    b64_str, img = capture_and_encode()
    print("Analisando padrão com NVIDIA NIM (Llama 3.2 Vision)...")
    
    start = time.time()
    resultado = detect_pattern(img, base64_image_str=b64_str)
    end = time.time()
    
    print(f"Tempo de inferência: {(end - start):.2f}s")
    print(json.dumps(resultado, indent=4, ensure_ascii=False))
