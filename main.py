import io
import time
import requests
import pandas as pd
import unicodedata
from difflib import SequenceMatcher
from typing import Optional
from fastapi import FastAPI, Query

app = FastAPI(title="API TUSS / ANS - Busca Inteligente")

URL_PLANILHA_GITHUB = "https://github.com/giuliannooliveira-ui/rolltussans/raw/refs/heads/main/downloads/TUSS_ANS.xlsx"

# Cache em memória para garantir respostas em milissegundos
CACHE_DF = None
CACHE_TIMESTAMP = 0
CACHE_EXPIRATION_SECONDS = 3600  # Atualiza o cache a cada 1 hora

def remover_acentos(texto: str) -> str:
    """Remove acentos, pontuações extras e padroniza para maiúsculas."""
    if not isinstance(texto, str):
        return ""
    nfkd = unicodedata.normalize('NFKD', texto)
    texto_sem_acento = "".join([c for c in nfkd if not unicodedata.combining(c)]).upper().strip()
    return texto_sem_acento

def carregar_e_tratar_planilha():
    """Baixa e processa a planilha para manter na memória."""
    global CACHE_DF, CACHE_TIMESTAMP
    
    agora = time.time()
    if CACHE_DF is not None and (agora - CACHE_TIMESTAMP) < CACHE_EXPIRATION_SECONDS:
        return CACHE_DF

    print("Iniciando carregamento/atualização do cache da planilha...")
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(URL_PLANILHA_GITHUB, headers=headers, timeout=30)
    
    if response.status_code != 200:
        raise Exception(f"Não foi possível baixar a planilha. HTTP {response.status_code}")

    conteudo_bytes = response.content
    df = pd.read_excel(io.BytesIO(conteudo_bytes), engine="openpyxl", header=7)

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

    df = df.rename(columns=mapeamento_colunas)
    df = df.loc[:, ~df.columns.str.contains("^Unnamed", na=False)]
    df = df.fillna("").astype(str)

    # Colunas internas para otimização de busca
    df["_codigo_limpo"] = df["codigo"].str.strip()
    df["_nome_limpo"] = df["termo_tuss"].apply(remover_acentos) + " " + df["procedimento_rol"].apply(remover_acentos)

    CACHE_DF = df
    CACHE_TIMESTAMP = agora
    print("Cache atualizado com sucesso!")
    return CACHE_DF

@app.on_event("startup")
def startup_event():
    try:
        carregar_e_tratar_planilha()
    except Exception as e:
        print(f"Aviso no startup: {e}")

@app.get("/")
def home():
    return {
        "status": "API TUSS ANS Online",
        "exemplos_uso": [
            "/consultar?cdprocedimento=31602347",
            "/consultar?nmprocedimento=anestesya",  # Com erro de digitação
            "/consultar?nmprocedimento=ressonancia coluna"  # Termos separados
        ]
    }

@app.get("/consultar")
def consultar_procedimento(
    cdprocedimento: Optional[str] = Query(None, description="Código TUSS do procedimento"),
    nmprocedimento: Optional[str] = Query(None, description="Nome do procedimento (aceita digitação aproximada/com erros)")
):
    if not cdprocedimento and not nmprocedimento:
        return {
            "erro": "É necessário informar ao menos um parâmetro: 'cdprocedimento' ou 'nmprocedimento'."
        }

    try:
        df = carregar_e_tratar_planilha()
        resultados = df.copy()

        # 1. Filtro por Código TUSS
        if cdprocedimento and cdprocedimento.strip():
            codigo_limpo = cdprocedimento.strip()
            resultados = resultados[resultados["_codigo_limpo"].str.contains(codigo_limpo, na=False)]

        # 2. Filtro por Nome do Procedimento
        tipo_busca = "exata_ou_contem"
        if nmprocedimento and nmprocedimento.strip():
            nome_limpo = remover_acentos(nmprocedimento)
            palavras_busca = nome_limpo.split()

            # A. Primeiro tenta encontrar registros que contenham TODAS as palavras digitadas
            filtro_palavras = pd.Series(True, index=resultados.index)
            for palavra in palavras_busca:
                filtro_palavras = filtro_palavras & resultados["_nome_limpo"].str.contains(palavra, na=False)

            resultados_filtro = resultados[filtro_palavras]

            # B. Se encontrou resultados por palavras-chave
            if not resultados_filtro.empty:
                resultados = resultados_filtro
            else:
                # C. Se NÃO encontrou (ex: erro de digitação), aciona a BUSCA APROXIMADA (Fuzzy Match)
                tipo_busca = "aproximada_fuzzy"
                
                # Calcula a razão de similaridade (0 a 100%) para cada linha
                def calcular_similaridade(texto_linha):
                    return SequenceMatcher(None, nome_limpo, texto_linha).ratio()

                resultados["_similaridade"] = resultados["_nome_limpo"].apply(calcular_similaridade)
                
                # Filtra apenas registros com pelo menos 45% de similaridade
                resultados_fuzzy = resultados[resultados["_similaridade"] >= 0.45]

                # Se mesmo no fuzzy não achar, pega os top 10 mais próximos
                if resultados_fuzzy.empty:
                    resultados_fuzzy = resultados.sort_values(by="_similaridade", ascending=False).head(10)
                else:
                    resultados_fuzzy = resultados_fuzzy.sort_values(by="_similaridade", ascending=False).head(20)

                resultados = resultados_fuzzy

        if resultados.empty:
            return {
                "encontrado": False,
                "cdprocedimento_buscado": cdprocedimento,
                "nmprocedimento_buscado": nmprocedimento,
                "mensagem": "Nenhum procedimento encontrado."
            }

        # Remove colunas internas de busca antes de gerar o JSON
        colunas_internas = ["_codigo_limpo", "_nome_limpo", "_similaridade"]
        resultados = resultados.drop(columns=[c for c in colunas_internas if c in resultados.columns])

        dados = resultados.to_dict(orient="records")
        dados_limpos = [{k: v.strip() for k, v in item.items()} for item in dados]

        return {
            "encontrado": True,
            "tipo_busca": tipo_busca,  # Indica se foi busca exata ou aproximação por erro de digitação
            "cdprocedimento_buscado": cdprocedimento,
            "nmprocedimento_buscado": nmprocedimento,
            "total_encontrados": len(dados_limpos),
            "resultados": dados_limpos
        }

    except Exception as e:
        return {"erro": f"Erro interno ao processar consulta: {str(e)}"}
