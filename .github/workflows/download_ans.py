import os
import requests
from datetime import datetime

URL = "https://www.gov.br/ans/pt-br/acesso-a-informacao/participacao-da-sociedade/atualizacao-do-rol-de-procedimentos/CorrelaoTUSS.202409Rol.2021_TUSS202605_RN652.2025_RN671.2026.xlsx"
OUTPUT_DIR = "downloads"

def download_tuss():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Simula um navegador real completo para evitar bloqueios HTTP 403 / 500 do gov.br
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.gov.br/ans/pt-br"
    }
    
    print(f"Iniciando download de: {URL}")
    
    try:
        # verify=False e timeout alto ajudam a ignorar falhas de certificado comuns em sites do governo
        response = requests.get(URL, headers=headers, stream=True, timeout=60, verify=False)
        
        print(f"Status HTTP retornado: {response.status_code}")
        
        if response.status_code == 200:
            data_atual = datetime.now().strftime("%Y-%m-%d")
            file_name = f"TUSS_ANS_{data_atual}.xlsx"
            file_path = os.path.join(OUTPUT_DIR, file_name)
            
            with open(file_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        
            print(f"Download concluído com sucesso em: {file_path}")
        else:
            raise Exception(f"Erro ao baixar o arquivo. O servidor retornou o status HTTP {response.status_code}")
            
    except Exception as e:
        print(f"Ocorreu um erro no download: {e}")
        raise e

if __name__ == "__main__":
    # Desabilita alertas de SSL inseguro no terminal
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    download_tuss()