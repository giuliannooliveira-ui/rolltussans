from fastapi import FastAPI, Query
import pandas as pd
import io
import requests

app = FastAPI(
    title="API TUSS / ANS",
    description="Consulta otimizada com colunas tratadas da planilha TUSS/ANS"
)

URL_PLANILHA_GITHUB = "https://raw.githubusercontent.com/giuliannoboliveira-ui/rolltussans/main/downloads/TUSS_ANS.xlsx"

@app.get("/")
def home():
    return {"status": "API TUSS ANS Online", "instrucoes": "Use /consultar?termo=SEU_TERMO"}

@app.get("/consultar")
def consultar_procedimento(termo: str = Query(..., description="Código TUSS ou Nome do Procedimento")):
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        response = requests.get(URL_PLANILHA_GITHUB, headers=headers, timeout=30)
        if response.status_code != 200:
            return {"erro": "Não foi possível carregar a planilha do GitHub.", "status_code": response.status_code}
            
        # 1. Tenta ler pulando as linhas de título do governo (header=3 costuma ser o padrão da ANS)
        # Se a cabeçalho estiver em outra linha, altere o valor de header (ex: header=2 ou header=4)
        df = pd.read_excel(io.BytesIO(response.content), header=3)
        
        # Se mesmo assim vier 'Unnamed', tenta encontrar automaticamente a linha do cabeçalho real
        if any("Unnamed" in str(col) for col in df.columns):
            # Carrega a planilha sem cabeçalho para procurar onde estão as palavras chaves tipo 'CÓDIGO' ou 'TUSS'
            df_raw = pd.read_excel(io.BytesIO(response.content), header=None)
            
            # Procura a primeira linha que contém a palavra "TUSS" ou "CÓDIGO"
            header_row_idx = None
            for idx, row in df_raw.iterrows():
                row_str = " ".join(row.dropna().astype(str)).upper()
                if "TUSS" in row_str or "CÓDIGO" in row_str or "PROCEDIMENTO" in row_str:
                    header_row_idx = idx
                    break
            
            if header_row_idx is not None:
                # Recarrega definindo a linha correta como cabeçalho
                df = pd.read_excel(io.BytesIO(response.content), header=header_row_idx)

        # 2. Limpeza do DataFrame
        # Remove quebras de linha e espaços extras nos nomes das colunas
        df.columns = [str(col).replace("\n", " ").strip() for col in df.columns]
        
        # Remove colunas inteiramente sem nome ou irrelevantes se houver
        df = df.loc[:, ~df.columns.str.contains("^Unnamed")]
        
        # Substitui valores nulos (NaN) por texto vazio ""
        df = df.fillna("").astype(str)

        # 3. Filtragem pelo termo de busca
        filtro = df.apply(lambda col: col.str.contains(termo, case=False, na=False)).any(axis=1)
        resultados = df[filtro]

        if resultados.empty:
            return {
                "encontrado": False,
                "termo_buscado": termo,
                "mensagem": "Nenhum procedimento encontrado."
            }

        # 4. Limpa chaves e valores dos dicionários retornados no JSON
        dados = resultados.to_dict(orient="records")
        dados_limpos = []
        for item in dados:
            # Remove chaves vazias ou com nomes estranhos do JSON final
            item_limpo = {k: v.strip() for k, v in item.items() if k and not k.startswith("Unnamed")}
            dados_limpos.append(item_limpo)

        return {
            "encontrado": True,
            "termo_buscado": termo,
            "total_encontrados": len(dados_limpos),
            "resultados": dados_limpos
        }

    except Exception as e:
        return {"erro": f"Erro interno ao processar consulta: {str(e)}"}
