import io
import pandas as pd
import requests
from fastapi import FastAPI, Query

app = FastAPI(title="API TUSS / ANS")

# URL Raw do repositório
URL_PLANILHA_GITHUB = "https://github.com/giuliannooliveira-ui/rolltussans/raw/refs/heads/main/downloads/TUSS_ANS.xlsx"

@app.get("/")
def home():
    return {"status": "API TUSS ANS Online", "instrucoes": "Use /consultar?termo=31602347"}

@app.get("/consultar")
def consultar_procedimento(termo: str = Query(..., description="Código TUSS ou Nome")):
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        response = requests.get(URL_PLANILHA_GITHUB, headers=headers, timeout=30)
        if response.status_code != 200:
            return {"erro": "Não foi possível carregar a planilha do GitHub.", "status_code": response.status_code}

        conteudo_bytes = response.content

        # 1. Carrega a planilha usando header=7 (onde estão os títulos dos campos)
        df = pd.read_excel(io.BytesIO(conteudo_bytes), engine="openpyxl", header=7)

        # 2. Mapeamento amigável para padronizar as chaves do JSON
        mapeamento_colunas = {
            df.columns[0]: "codigo",
            df.columns[1]: "termo_tuss",
            df.columns[2]: "correlacao",
            df.columns[3]: "procedimento_rol",
            df.columns[4]: "resolucao_normativa",
            df.columns[5]: "vigencia",
            df.columns[6]: "od",
            df.columns[7]: "amb",
            df.columns[8]: "hco",
            df.columns[9]: "hso",
            df.columns[10]: "pac",
            df.columns[11]: "dut",
            df.columns[12]: "subgrupo",
            df.columns[13]: "grupo",
            df.columns[14]: "capitulo"
        }

        # Renomeia as colunas
        df = df.rename(columns=mapeamento_colunas)

        # Remove colunas vazias ou 'Unnamed' extras se houver
        df = df.loc[:, ~df.columns.str.contains("^Unnamed", na=False)]
        
        # Converte tudo para string e limpa valores nulos (NaN)
        df = df.fillna("").astype(str)

        # 3. Executa a busca
        filtro = df.apply(lambda col: col.str.contains(termo, case=False, na=False)).any(axis=1)
        resultados = df[filtro]

        if resultados.empty:
            return {
                "encontrado": False,
                "termo_buscado": termo,
                "mensagem": "Nenhum procedimento encontrado."
            }

        # 4. Formata os registros removendo espaços em branco das pontas
        dados = resultados.to_dict(orient="records")
        dados_limpos = []
        for item in dados:
            item_formatado = {k: v.strip() for k, v in item.items() if k and not k.startswith("Unnamed")}
            dados_limpos.append(item_formatado)

        return {
            "encontrado": True,
            "termo_buscado": termo,
            "total_encontrados": len(dados_limpos),
            "resultados": dados_limpos
        }

    except Exception as e:
        return {"erro": f"Erro interno ao processar consulta: {str(e)}"}
