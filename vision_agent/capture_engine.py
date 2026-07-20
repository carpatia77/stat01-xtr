import mss
import pygetwindow as gw
from PIL import Image
import io
import base64
import time

def get_zoom_window():
    """Finds the Zoom Meeting window with resilience."""
    for _ in range(3): # Tenta achar o Zoom 3 vezes antes do fallback
        windows = gw.getWindowsWithTitle('Zoom')
        for win in windows:
            if win.title.strip() == 'Zoom Meeting' or 'Zoom' in win.title:
                if win.width > 0 and win.height > 0: # Garante que não está minimizada
                    return {'left': win.left, 'top': win.top, 'width': win.width, 'height': win.height}
        time.sleep(0.5)
    
    # Se não encontrar o Zoom ativo/visível, pega a tela toda como fallback de emergência
    print("[AVISO] Janela do Zoom não encontrada ou minimizada. Capturando a tela primária...")
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        return {'left': monitor['left'], 'top': monitor['top'], 'width': monitor['width'], 'height': monitor['height']}

def capture_and_encode():
    """Captures the defined region and returns a base64 JPEG string."""
    bbox = get_zoom_window()
    
    with mss.mss() as sct:
        # mss expects a dict with top, left, width, height
        screenshot = sct.grab(bbox)
        
        # Convert to PIL Image
        img = Image.frombytes('RGB', screenshot.size, screenshot.bgra, 'raw', 'BGRX')
        
        # Compress and save to bytes
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=85)
        
        # Convert to Base64
        base64_encoded = base64.b64encode(buffer.getvalue()).decode('utf-8')
        return base64_encoded, img

if __name__ == "__main__":
    start = time.time()
    b64, img = capture_and_encode()
    end = time.time()
    print(f"Tempo de captura e compressão: {(end - start) * 1000:.2f} ms")
    print(f"Tamanho do Base64: {len(b64) / 1024:.2f} KB")
