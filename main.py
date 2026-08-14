from fastapi import FastAPI, Query
import pandas as pd
import io
import requests

app = FastAPI(
    title="API de Consulta TUSS / ANS",
    description="Consulta procedimentos na planilha atualizada da ANS diretamente do GitHub.",
    version="1.0.0"
)

# Coloque a sua URL Raw do GitHub aqui
URL_PLANILHA_GITHUB = "https://raw.githubusercontent.com/giuliannooliveira-ui/rolltussans/main/downloads/TUSS-ANS-Planilha.xlsx"

@app.get("/")
def home():
    return {"status": "API TUSS ANS Online", "instrucoes": "Use /consultar?termo=SEU_TERMO"}

@app.get("/consultar")
def consultar_procedimento(termo: str = Query(..., description="Código TUSS ou parte do nome do procedimento")):
    try:
        # Baixa a planilha direto do GitHub para a memória
        response = requests.get(URL_PLANILHA_GITHUB)
        if response.status_code != 200:
            return {"erro": "Não foi possível carregar a planilha do GitHub."}
            
        # Lê a planilha com Pandas
        df = pd.read_excel(io.BytesIO(response.content))
        
        # Converte todas as colunas para texto para facilitar a busca
        df = df.fillna("").astype(str)
        
        # Procura em todas as colunas por qualquer correspondência com o termo digitado
        filtro = df.apply(lambda col: col.str.contains(termo, case=False, na=False)).any(axis=1)
        resultados = df[filtro]
        
        if resultados.empty:
            return {
                "encontrado": False,
                "termo_buscado": termo,
                "mensagem": "Nenhum procedimento encontrado."
            }
            
        # Converte os resultados em uma lista de dicionários/JSON
        dados = resultados.to_dict(orient="records")
        
        return {
            "encontrado": True,
            "termo_buscado": termo,
            "total_encontrados": len(dados),
            "resultados": dados
        }

    except Exception as e:
        return {"erro": f"Falha interna ao processar consulta: {str(e)}"}
