import os
import requests
from datetime import datetime

URL = "https://www.gov.br/ans/pt-br/acesso-a-informacao/participacao-da-sociedade/atualizacao-do-rol-de-procedimentos/CorrelaoTUSS.202409Rol.2021_TUSS202605_RN652.2025_RN671.2026.xlsx"
OUTPUT_DIR = "downloads"

def download_tuss():
    # Cria a pasta 'downloads' se não existir
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    print(f"Iniciando download de: {URL}")
    response = requests.get(URL, headers=headers, stream=True, timeout=30)
    
    if response.status_code == 200:
        data_atual = datetime.now().strftime("%Y-%m-%d")
        file_name = f"TUSS_ANS_{data_atual}.xlsx"
        file_path = os.path.join(OUTPUT_DIR, file_name)
        
        with open(file_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                
        print(f"Download concluído com sucesso: {file_path}")
    else:
        raise Exception(f"Falha no download. Status HTTP: {response.status_code}")

if __name__ == "__main__":
    download_tuss()