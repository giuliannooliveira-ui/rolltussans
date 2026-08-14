from fastapi import FastAPI, Query
import pandas as pd
import io
import requests

app = FastAPI(title="API TUSS / ANS")

URL_PLANILHA_GITHUB = "https://raw.githubusercontent.com/giuliannoboliveira-ui/rolltussans/main/downloads/TUSS_ANS.xlsx"

@app.get("/")
def home():
    return {"status": "API TUSS ANS Online", "instrucoes": "Use /consultar?termo=SEU_TERMO"}

@app.get("/consultar")
def consultar_procedimento(termo: str = Query(..., description="Código TUSS ou Nome")):
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        response = requests.get(URL_PLANILHA_GITHUB, headers=headers, timeout=30)
        
        if response.status_code != 200:
            return {
                "erro": "Não foi possível carregar a planilha do GitHub.",
                "status_code": response.status_code
            }
            
        # Garante que o conteúdo retornado seja um arquivo binário/excel válido
        conteudo_bytes = response.content
        if len(conteudo_bytes) < 1000:  # Um arquivo xlsx real dificilmente tem menos de 1KB
            return {"erro": "O arquivo retornado do GitHub parece inválido ou corrompido."}

        # 1. Lê os dados brutos usando a engine 'openpyxl' explicitamente
        df_raw = pd.read_excel(io.BytesIO(conteudo_bytes), engine="openpyxl", header=None)
        
        # 2. Localiza dinamicamente a linha do cabeçalho real (onde contém 'TUSS' ou 'CÓDIGO')
        header_idx = 3  # Padrão de fallback
        for idx, row in df_raw.iterrows():
            linha_texto = " ".join(row.dropna().astype(str)).upper()
            if "TUSS" in linha_texto or "CÓDIGO" in linha_texto or "PROCEDIMENTO" in linha_texto:
                header_idx = idx
                break

        # 3. Carrega o DataFrame com o cabeçalho correto e engine especificada
        df = pd.read_excel(io.BytesIO(conteudo_bytes), engine="openpyxl", header=header_idx)
        
        # Trata os nomes das colunas
        df.columns = [str(col).replace("\n", " ").strip() for col in df.columns]
        df = df.loc[:, ~df.columns.str.contains("^Unnamed")]
        df = df.fillna("").astype(str)

        # 4. Executa a busca
        filtro = df.apply(lambda col: col.str.contains(termo, case=False, na=False)).any(axis=1)
        resultados = df[filtro]

        if resultados.empty:
            return {"encontrado": False, "termo_buscado": termo, "mensagem": "Nenhum procedimento encontrado."}

        # Formatando retorno dos dados sem campos 'Unnamed'
        dados = resultados.to_dict(orient="records")
        dados_limpos = [{k: v.strip() for k, v in item.items() if k and not k.startswith("Unnamed")} for item in dados]

        return {
            "encontrado": True,
            "termo_buscado": termo,
            "total_encontrados": len(dados_limpos),
            "resultados": dados_limpos
        }

    except Exception as e:
        return {"erro": f"Erro interno ao processar consulta: {str(e)}"}
