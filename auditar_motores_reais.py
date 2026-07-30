from __future__ import annotations

import csv
import hashlib
import json
import os
import re
from datetime import datetime
from pathlib import Path

import pandas as pd


BASE = Path(r"C:\Nas100_dashboard")
SAIDA = BASE / "VALIDACAO_MOTORES_REAIS"
SAIDA.mkdir(parents=True, exist_ok=True)

PADROES_CANDIDATOS = [
    "trade",
    "trades",
    "operacional",
    "execucao",
    "sombra",
    "dna",
]

PADROES_DERIVADOS = [
    "backup",
    "amostra",
    "melhor_cenario",
    "melhor cenário",
    "equity",
    "estatistica",
    "estatística",
    "resumo",
    "relatorio",
    "relatório",
    "ranking",
    "auditoria",
    "autopsia",
    "autópsia",
    "unificado",
    "forensic",
    "forense",
    "linha_tempo",
    "sequencia",
    "sequência",
    "diagnostico",
    "diagnóstico",
    "manifesto",
]

COLUNAS_DATA = [
    "entrada_data_hora",
    "data_hora_entrada",
    "datetime_entrada",
    "timestamp_entrada",
    "entry_time",
    "data_hora",
    "datetime",
    "timestamp",
    "hora_entrada",
]

COLUNAS_LADO = [
    "lado",
    "direcao",
    "direção",
    "tipo",
    "sinal",
    "side",
    "operacao",
    "operação",
]

COLUNAS_RESULTADO = [
    "resultado",
    "resultado_trade",
    "status_resultado",
    "desfecho",
    "outcome",
    "classificacao",
    "classificação",
    "tipo_saida",
    "motivo_saida",
]

COLUNAS_PONTOS = [
    "resultado_pontos",
    "pontos",
    "lucro_pontos",
    "pnl_pontos",
    "profit_points",
    "resultado_pts",
]

COLUNAS_PRECO = [
    "preco_entrada",
    "preço_entrada",
    "entry_price",
    "preco",
    "preço",
    "last",
]


def normalizar(texto: object) -> str:
    return str(texto).strip().lower()


def detectar_separador(arquivo: Path) -> str:
    try:
        with arquivo.open("r", encoding="utf-8-sig", errors="replace") as f:
            amostra = f.read(10000)

        if not amostra.strip():
            return ","

        try:
            return csv.Sniffer().sniff(
                amostra,
                delimiters=",;\t|",
            ).delimiter
        except csv.Error:
            contagens = {
                ",": amostra.count(","),
                ";": amostra.count(";"),
                "\t": amostra.count("\t"),
                "|": amostra.count("|"),
            }
            return max(contagens, key=contagens.get)

    except Exception:
        return ","


def localizar_coluna(colunas: list[str], candidatos: list[str]) -> str:
    mapa = {normalizar(c): c for c in colunas}

    for candidato in candidatos:
        if candidato in mapa:
            return mapa[candidato]

    for coluna_normalizada, coluna_original in mapa.items():
        for candidato in candidatos:
            if candidato in coluna_normalizada:
                return coluna_original

    return ""


def fingerprint_rapido(arquivo: Path, bloco: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    tamanho = arquivo.stat().st_size

    with arquivo.open("rb") as f:
        inicio = f.read(bloco)
        h.update(inicio)

        if tamanho > bloco:
            f.seek(max(0, tamanho - bloco))
            fim = f.read(bloco)
            h.update(fim)

    h.update(str(tamanho).encode())
    return h.hexdigest()


def contar_linhas_aproximado(arquivo: Path) -> int:
    total = 0

    try:
        with arquivo.open("rb") as f:
            while True:
                bloco = f.read(8 * 1024 * 1024)
                if not bloco:
                    break
                total += bloco.count(b"\n")

        return max(0, total - 1)

    except Exception:
        return -1


def ler_amostra(arquivo: Path, separador: str) -> pd.DataFrame:
    erros = []

    for encoding in ["utf-8-sig", "utf-8", "latin1", "cp1252"]:
        try:
            return pd.read_csv(
                arquivo,
                sep=separador,
                encoding=encoding,
                nrows=50000,
                low_memory=False,
                on_bad_lines="skip",
            )
        except Exception as exc:
            erros.append(f"{encoding}: {exc}")

    raise RuntimeError(" | ".join(erros))


def valores_resumidos(serie: pd.Series, limite: int = 15) -> str:
    try:
        valores = (
            serie.astype(str)
            .str.strip()
            .replace({"": pd.NA, "nan": pd.NA, "None": pd.NA})
            .dropna()
            .value_counts()
            .head(limite)
        )

        return " | ".join(
            f"{indice}:{quantidade}"
            for indice, quantidade in valores.items()
        )
    except Exception:
        return ""


arquivos = []

for arquivo in BASE.rglob("*.csv"):
    caminho_texto = str(arquivo).lower()

    if "validacao_motores_reais" in caminho_texto:
        continue

    nome = arquivo.name.lower()

    if not any(padrao in nome for padrao in PADROES_CANDIDATOS):
        continue

    arquivos.append(arquivo)

arquivos = sorted(
    arquivos,
    key=lambda p: p.stat().st_mtime,
    reverse=True,
)

registros = []
erros = []

for numero, arquivo in enumerate(arquivos, start=1):
    print(f"[{numero}/{len(arquivos)}] {arquivo}")

    nome_normalizado = arquivo.name.lower()
    provavel_derivado = any(
        padrao in nome_normalizado
        for padrao in PADROES_DERIVADOS
    )

    registro = {
        "arquivo": arquivo.name,
        "caminho": str(arquivo),
        "tamanho_mb": round(arquivo.stat().st_size / 1024 / 1024, 3),
        "modificado_em": datetime.fromtimestamp(
            arquivo.stat().st_mtime
        ).isoformat(sep=" "),
        "provavel_derivado_nome": provavel_derivado,
        "linhas_aproximadas": contar_linhas_aproximado(arquivo),
        "fingerprint_rapido": fingerprint_rapido(arquivo),
    }

    try:
        separador = detectar_separador(arquivo)
        df = ler_amostra(arquivo, separador)

        colunas = [str(c) for c in df.columns]

        coluna_data = localizar_coluna(colunas, COLUNAS_DATA)
        coluna_lado = localizar_coluna(colunas, COLUNAS_LADO)
        coluna_resultado = localizar_coluna(colunas, COLUNAS_RESULTADO)
        coluna_pontos = localizar_coluna(colunas, COLUNAS_PONTOS)
        coluna_preco = localizar_coluna(colunas, COLUNAS_PRECO)

        registro.update({
            "separador": repr(separador),
            "colunas_total": len(colunas),
            "colunas": " | ".join(colunas),
            "coluna_data": coluna_data,
            "coluna_lado": coluna_lado,
            "coluna_resultado": coluna_resultado,
            "coluna_pontos": coluna_pontos,
            "coluna_preco": coluna_preco,
            "amostra_linhas": len(df),
            "valores_lado_amostra": (
                valores_resumidos(df[coluna_lado])
                if coluna_lado else ""
            ),
            "valores_resultado_amostra": (
                valores_resumidos(df[coluna_resultado])
                if coluna_resultado else ""
            ),
        })

        if coluna_data:
            datas = pd.to_datetime(
                df[coluna_data],
                errors="coerce",
                dayfirst=True,
            ).dropna()

            registro["data_min_amostra"] = (
                datas.min().isoformat()
                if not datas.empty else ""
            )
            registro["data_max_amostra"] = (
                datas.max().isoformat()
                if not datas.empty else ""
            )
        else:
            registro["data_min_amostra"] = ""
            registro["data_max_amostra"] = ""

        registro["possui_estrutura_trade"] = bool(
            coluna_data and coluna_lado
        )

        registro["possui_resultado_observado"] = bool(
            coluna_resultado or coluna_pontos
        )

    except Exception as exc:
        registro["erro_leitura"] = str(exc)
        erros.append({
            "arquivo": str(arquivo),
            "erro": str(exc),
        })

    registros.append(registro)

resultado = pd.DataFrame(registros)

if not resultado.empty:
    resultado = resultado.sort_values(
        [
            "provavel_derivado_nome",
            "possui_estrutura_trade",
            "modificado_em",
        ],
        ascending=[True, False, False],
        na_position="last",
    )

resultado.to_csv(
    SAIDA / "inventario_candidatos_trades.csv",
    index=False,
    encoding="utf-8-sig",
)

# Arquivos com o mesmo fingerprint são cópias exatas ou praticamente exatas.
duplicados = resultado[
    resultado.duplicated(
        subset=["fingerprint_rapido"],
        keep=False,
    )
].copy()

duplicados.to_csv(
    SAIDA / "arquivos_possivelmente_duplicados.csv",
    index=False,
    encoding="utf-8-sig",
)

# Candidatos mais prováveis a serem fontes originais.
if not resultado.empty:
    candidatos_originais = resultado[
        (resultado["provavel_derivado_nome"] == False)
        & (resultado["possui_estrutura_trade"] == True)
        & (resultado["possui_resultado_observado"] == True)
    ].copy()
else:
    candidatos_originais = pd.DataFrame()

candidatos_originais.to_csv(
    SAIDA / "candidatos_motores_reais.csv",
    index=False,
    encoding="utf-8-sig",
)

pd.DataFrame(erros).to_csv(
    SAIDA / "erros_leitura.csv",
    index=False,
    encoding="utf-8-sig",
)

resumo = {
    "gerado_em": datetime.now().isoformat(),
    "pasta_analisada": str(BASE),
    "arquivos_candidatos": len(resultado),
    "candidatos_originais": len(candidatos_originais),
    "arquivos_com_fingerprint_repetido": len(duplicados),
    "erros_leitura": len(erros),
    "observacao": (
        "A classificação é preliminar. O vínculo definitivo entre motor "
        "e CSV deve ser confirmado pelo comando do processo Python e "
        "pelas linhas do código que gravam o arquivo."
    ),
}

with (
    SAIDA / "resumo_validacao.json"
).open("w", encoding="utf-8") as f:
    json.dump(resumo, f, ensure_ascii=False, indent=2)

print()
print("=" * 70)
print("AUDITORIA CONCLUÍDA")
print("=" * 70)
print(json.dumps(resumo, ensure_ascii=False, indent=2))
print()
print(f"Relatórios: {SAIDA}")
