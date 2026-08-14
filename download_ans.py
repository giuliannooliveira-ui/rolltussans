import os
import requests

URL = "https://www.gov.br/ans/pt-br/acesso-a-informacao/participacao-da-sociedade/atualizacao-do-rol-de-procedimentos/CorrelaoTUSS.202409Rol.2021_TUSS202605_RN652.2025_RN671.2026.xlsx"
OUTPUT_DIR = "downloads"

def download_tuss():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": "https://www.gov.br/ans/pt-br"
    }
    
    print(f"Iniciando download de: {URL}")
    response = requests.get(URL, headers=headers, stream=True, timeout=60, verify=False)
    
    if response.status_code == 200:
        # Salva sempre com o mesmo nome fixo para a API ler facilmente
        file_path = os.path.join(OUTPUT_DIR, "TUSS_ANS.xlsx")
        
        with open(file_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    
        print(f"Download e atualização concluídos: {file_path}")
    else:
        raise Exception(f"Erro ao baixar. HTTP {response.status_code}")

if __name__ == "__main__":
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    download_tuss()
