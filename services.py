import pandas as pd
from database import Cadastro, ConsumoResumido, get_session
from io import StringIO


# ==========================================================
# LEITURA SEGURA COM FALLBACK DE ENCODING
# ==========================================================

def ler_arquivo_seguro(path):

    encodings = ["utf-8-sig", "latin1", "cp1252"]

    for enc in encodings:
        try:
            with open(path, "r", encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError:
            continue

    raise ValueError("Não foi possível decodificar o arquivo.")


# ==========================================================
# PADRONIZAÇÃO DO ARQUIVO DE CONSUMO
# ==========================================================

def padronizar_arquivo_consumo(path):

    conteudo = ler_arquivo_seguro(path)

    linhas_validas = []

    for linha in conteudo.splitlines():

        linha = linha.strip()

        if not linha:
            continue

        if linha == "Relatorio-Dados":
            continue

        if linha.endswith(";"):
            linha = linha[:-1]

        colunas = linha.split(";")

        if len(colunas) >= 7:
            linhas_validas.append(";".join(colunas[:7]))

    if not linhas_validas:
        raise ValueError("Arquivo não possui dados válidos.")

    conteudo_limpo = "\n".join(linhas_validas)

    return pd.read_csv(
        StringIO(conteudo_limpo),
        sep=";",
        dtype=str
    )


# ==========================================================
# UTILITÁRIOS
# ==========================================================

def normalizar_colunas(df):
    df.columns = df.columns.str.strip()
    return df


def converter_para_mb(valor, unidade):
    valor = float(valor)
    unidade = unidade.strip().upper()

    if unidade == "GB":
        return valor * 1024
    elif unidade == "MB":
        return valor
    elif unidade == "KB":
        return valor / 1024
    else:
        raise ValueError(f"Unidade inválida: {unidade}")


# ==========================================================
# PROCESSAR CADASTRO
# ==========================================================

def processar_cadastro(path):

    conteudo = ler_arquivo_seguro(path)

    df = pd.read_csv(
        StringIO(conteudo),
        sep=";",
        dtype=str
    )

    df.columns = df.columns.str.strip()

    if "CP+CA+Numero" not in df.columns or "FRANQUIA" not in df.columns:
        raise ValueError("Colunas obrigatórias não encontradas no cadastro.")

    df = df.dropna(how="all")

    df["CP+CA+Numero"] = df["CP+CA+Numero"].str.strip()
    df["FRANQUIA"] = pd.to_numeric(df["FRANQUIA"], errors="coerce")

    df = df.dropna(subset=["FRANQUIA"])

    df["franquia_mb"] = df["FRANQUIA"] * 1024

    session = get_session()
    session.query(Cadastro).delete()

    registros = [
        Cadastro(
            numero=row["CP+CA+Numero"],
            franquia_mb=float(row["franquia_mb"])
        )
        for _, row in df.iterrows()
    ]

    session.bulk_save_objects(registros)
    session.commit()
    session.close()

    return len(registros)


# ==========================================================
# PROCESSAR CONSUMO
# ==========================================================

def processar_consumo(path):

    df = padronizar_arquivo_consumo(path)

    df = normalizar_colunas(df)

    colunas_necessarias = [
        "CP+CA+Numero",
        "Nome",
        "Valor Consumo",
        "Unidade Consumo",
        "Grupo de classificacao"
    ]

    for col in colunas_necessarias:
        if col not in df.columns:
            raise ValueError(f"Coluna obrigatória ausente: {col}")

    df["CP+CA+Numero"] = df["CP+CA+Numero"].str.strip()
    df["Nome"] = df["Nome"].str.strip()

    df["Grupo de classificacao"] = df["Grupo de classificacao"].str.strip().str.upper()
    df["Unidade Consumo"] = df["Unidade Consumo"].str.strip().str.upper()

    df = df[df["Grupo de classificacao"] == "WEB"]

    if df.empty:
        raise ValueError("Nenhum registro WEB encontrado após padronização.")

    df["Valor Consumo"] = pd.to_numeric(df["Valor Consumo"], errors="coerce")
    df = df.dropna(subset=["Valor Consumo"])

    df["consumo_mb"] = df.apply(
        lambda row: converter_para_mb(
            row["Valor Consumo"],
            row["Unidade Consumo"]
        ),
        axis=1
    )

    resumo = (
        df.groupby(["CP+CA+Numero", "Nome"])["consumo_mb"]
        .sum()
        .reset_index()
    )

    session = get_session()
    session.query(ConsumoResumido).delete()

    registros = [
        ConsumoResumido(
            numero=row["CP+CA+Numero"],
            nome_usuario=row["Nome"],
            consumo_mb=float(row["consumo_mb"])
        )
        for _, row in resumo.iterrows()
    ]

    session.bulk_save_objects(registros)
    session.commit()
    session.close()

    return len(registros)


# ==========================================================
# ALERTAS ≥ 80%
# ==========================================================

def obter_alertas_80():

    session = get_session()

    consumos = session.query(ConsumoResumido).all()
    cadastros = session.query(Cadastro).all()

    session.close()

    franquias = {c.numero: c.franquia_mb for c in cadastros}

    alertas = []

    for c in consumos:

        franquia = franquias.get(c.numero)
        if not franquia:
            continue

        percentual = c.consumo_mb / franquia

        if percentual >= 0.8:
            alertas.append({
                "numero": c.numero,
                "nome": c.nome_usuario,
                "franquia_gb": round(franquia / 1024, 2),
                "consumo_gb": round(c.consumo_mb / 1024, 2),
                "percentual": round(percentual * 100, 2)
            })

    return alertas


# ==========================================================
# CONSULTA POR USUÁRIO
# ==========================================================

def consultar_usuario(termo):

    session = get_session()

    consumos = session.query(ConsumoResumido).all()
    cadastros = session.query(Cadastro).all()

    session.close()

    franquias = {c.numero: c.franquia_mb for c in cadastros}

    termo = termo.lower().strip()

    resultados = []

    for c in consumos:

        if termo in c.numero.lower() or termo in c.nome_usuario.lower():

            franquia = franquias.get(c.numero, 0)
            percentual = (c.consumo_mb / franquia) if franquia else 0

            resultados.append({
                "numero": c.numero,
                "nome": c.nome_usuario,
                "franquia_gb": round(franquia / 1024, 2),
                "consumo_gb": round(c.consumo_mb / 1024, 2),
                "percentual": round(percentual * 100, 2)
            })

    return resultados