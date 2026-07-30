from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

BASE_PADRAO = Path(r"C:\Nas100_dashboard")
PASTA_REGISTRY = "C7_REGISTRY"
ARQ_REGISTRY = "c7_registry_oficial.json"
ARQ_RELATORIO = "c7_registry_validacao.csv"
ARQ_PROCESSOS = "c7_registry_processos_ativos.csv"
ARQ_VEREDITO = "c7_registry_veredito.txt"

# Motores produtores já confirmados pela auditoria de 29/07/2026.
# O script valida os caminhos em cada execução. Nada é alterado nos motores.
MOTORES_PRECONFIGURADOS: list[dict[str, Any]] = [
    {
        "id": "motor_operacional_c7_v3_1",
        "nome": "Motor Operacional C7 v3.1 — campanha virtual/logger",
        "tipo": "MOTOR_DECISAO",
        "script": "motor_operacional_c7_v3_1_campanha_virtual_logger.py",
        "gera_trades": True,
        "usar_no_lab_dna": True,
        "arquivos": {
            "trades": "trades_quantower_operacional_v3_1_v5_2.csv",
            "sinais": "sinais_quantower_operacional_v3_1_v5_2.csv",
            "bloqueios": "bloqueios_quantower_operacional_v3_1_v5_2.csv",
            "estados": "estados_quantower_operacional_v3_1_v5_2.csv",
            "trade_aberto": "trade_aberto_quantower_operacional_v3_1_v5_2.csv",
            "telemetria_posicoes": "telemetria_posicoes_operacional_v3_1_v5_2.csv",
        },
        "observacao": "Fonte original de decisões/trades. Não confundir com relatórios derivados do laboratório.",
    },
    {
        "id": "motor_c7_dna_fluxo_v5_2",
        "nome": "Motor C7 DNA Fluxo v5.2 — sombra/invalidação",
        "tipo": "MOTOR_DECISAO_SOMBRA",
        "script": "motor_c7_dna_fluxo_v5_2_sombra_invalidacao_v1_corrigido.py",
        "gera_trades": True,
        "usar_no_lab_dna": True,
        "arquivos": {
            "trades": "trades_c7_dna_fluxo_v5_2.csv",
            "sinais": "sinais_c7_dna_fluxo_v5_2.csv",
            "bloqueios": "bloqueios_c7_dna_fluxo_v5_2.csv",
            "estados": "estados_c7_dna_fluxo_v5_2.csv",
            "trade_aberto": "trade_aberto_c7_dna_fluxo_v5_2.csv",
            "invalidacoes": "invalidacoes_tese_sombra_v1.csv",
        },
        "observacao": "Fonte original de decisões/trades em sombra.",
    },
    {
        "id": "c7_live_13a_shadow_engine_v2",
        "nome": "C7 LIVE 13A Shadow Engine v2",
        "tipo": "MOTOR_DECISAO_SOMBRA_CANDIDATO",
        "script": "C7_LIVE_13A_SHADOW_ENGINE_v2.py",
        "gera_trades": None,
        "usar_no_lab_dna": False,
        "arquivos": {},
        "observacao": "Processo ativo, porém o vínculo com o CSV original ainda precisa ser confirmado. Fica fora do LAB até validação.",
    },
]

AUXILIARES_PRECONFIGURADOS: list[dict[str, Any]] = [
    {"id": "rotacionador_quantower", "script": "rotacionar_export_quantower.py", "tipo": "INFRAESTRUTURA"},
    {"id": "logger_estado_mercado", "script": "logger_estado_mercado.py", "tipo": "COLETOR_ESTADO"},
    {"id": "c7_live_13b", "script": "C7_LIVE_13B_SHADOW_ANALYTICS.py", "tipo": "ANALYTICS"},
    {"id": "c7_live_13c", "script": "C7_LIVE_13C_STABILITY_MONITOR_v2.py", "tipo": "MONITOR"},
    {"id": "c7_live_13d", "script": "C7_LIVE_13D_PROMOTION_ENGINE_v2.py", "tipo": "PROMOCAO"},
]

DERIVADOS_BLOQUEADOS = [
    "backup", "amostra", "melhor_cenario", "equity", "estatistica", "resumo",
    "relatorio", "ranking", "auditoria", "autopsia", "unificado", "forensic",
    "forense", "linha_tempo", "sequencia", "diagnostico", "manifesto",
]


def agora_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def sha256_rapido(path: Path, bloco: int = 1024 * 1024) -> str:
    if not path.exists() or not path.is_file():
        return ""
    h = hashlib.sha256()
    tamanho = path.stat().st_size
    with path.open("rb") as f:
        h.update(f.read(bloco))
        if tamanho > bloco:
            f.seek(max(0, tamanho - bloco))
            h.update(f.read(bloco))
    h.update(str(tamanho).encode("utf-8"))
    return h.hexdigest()


def detectar_sep(path: Path) -> str:
    try:
        with path.open("r", encoding="utf-8-sig", errors="replace") as f:
            amostra = f.read(12000)
        if not amostra:
            return ","
        try:
            return csv.Sniffer().sniff(amostra, delimiters=",;\t|").delimiter
        except csv.Error:
            cont = {s: amostra.count(s) for s in [",", ";", "\t", "|"]}
            return max(cont, key=cont.get)
    except Exception:
        return ","


def ler_cabecalho(path: Path) -> list[str]:
    if not path.exists() or not path.is_file() or path.stat().st_size == 0:
        return []
    sep = detectar_sep(path)
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin1"):
        try:
            with path.open("r", encoding=enc, errors="strict", newline="") as f:
                return next(csv.reader(f, delimiter=sep), [])
        except Exception:
            continue
    return []


def localizar_arquivo(base: Path, nome: str) -> tuple[Path | None, list[str]]:
    direto = base / nome
    candidatos: list[Path] = []
    if direto.exists():
        candidatos.append(direto)
    try:
        for p in base.rglob(nome):
            if p not in candidatos and PASTA_REGISTRY.lower() not in str(p).lower():
                candidatos.append(p)
    except OSError:
        pass
    candidatos.sort(key=lambda p: (0 if p.parent == base else 1, -p.stat().st_mtime))
    return (candidatos[0] if candidatos else None, [str(x) for x in candidatos])


def processos_python() -> list[dict[str, str]]:
    ps = r'''Get-CimInstance Win32_Process | Where-Object {$_.Name -match "python"} | Select-Object ProcessId,CreationDate,ExecutablePath,CommandLine | ConvertTo-Json -Depth 3'''
    try:
        cp = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
            text=True, capture_output=True, timeout=30, check=False,
        )
        if cp.returncode != 0 or not cp.stdout.strip():
            return []
        data = json.loads(cp.stdout)
        if isinstance(data, dict):
            data = [data]
        return [{k: "" if v is None else str(v) for k, v in x.items()} for x in data]
    except Exception:
        return []


def script_ativo(script: str, processos: Iterable[dict[str, str]]) -> bool:
    alvo = script.lower()
    return any(alvo in p.get("CommandLine", "").lower() for p in processos)


def validar_motor(base: Path, motor: dict[str, Any], processos: list[dict[str, str]]) -> dict[str, Any]:
    out = dict(motor)
    script_path, script_candidatos = localizar_arquivo(base, motor["script"])
    out["script_path"] = str(script_path) if script_path else ""
    out["script_encontrado"] = bool(script_path)
    out["script_ativo"] = script_ativo(motor["script"], processos)
    out["script_candidatos"] = script_candidatos
    out["arquivos_resolvidos"] = {}
    out["validacoes"] = []

    for papel, nome in motor.get("arquivos", {}).items():
        path, candidatos = localizar_arquivo(base, nome)
        info: dict[str, Any] = {
            "nome_declarado": nome,
            "path": str(path) if path else "",
            "encontrado": bool(path),
            "candidatos": candidatos,
            "duplicidade_caminho": len(candidatos) > 1,
        }
        if path:
            stat = path.stat()
            cab = ler_cabecalho(path)
            info.update({
                "tamanho_bytes": stat.st_size,
                "modificado_em": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
                "fingerprint_rapido": sha256_rapido(path),
                "cabecalho": cab,
                "colunas_total": len(cab),
                "nome_sugere_derivado": any(t in path.name.lower() for t in DERIVADOS_BLOQUEADOS),
            })
        out["arquivos_resolvidos"][papel] = info

    trade_info = out["arquivos_resolvidos"].get("trades")
    if motor.get("gera_trades") is True:
        if not trade_info or not trade_info.get("encontrado"):
            out["validacoes"].append("ERRO: motor declara trades, mas arquivo de trades não foi encontrado")
        else:
            cab_norm = {c.strip().lower() for c in trade_info.get("cabecalho", [])}
            possui_tempo = any(c in cab_norm for c in {"data_hora", "data_hora_entrada", "entry_time", "timestamp"})
            possui_lado = any(c in cab_norm for c in {"lado", "side", "direcao", "direção"})
            possui_resultado = any(c in cab_norm for c in {"resultado_mt5", "resultado", "resultado_pontos", "gain", "stop", "status"})
            if not possui_tempo:
                out["validacoes"].append("ALERTA: arquivo de trades sem coluna temporal reconhecida")
            if not possui_lado:
                out["validacoes"].append("ALERTA: arquivo de trades sem coluna de lado reconhecida")
            if not possui_resultado:
                out["validacoes"].append("ALERTA: arquivo de trades sem resultado reconhecido")
            if trade_info.get("nome_sugere_derivado"):
                out["validacoes"].append("ERRO: arquivo de trades parece derivado pelo nome")
    if motor.get("usar_no_lab_dna") and not out["script_ativo"]:
        out["validacoes"].append("ALERTA: motor habilitado para o LAB, porém não aparece ativo agora")

    erros = [x for x in out["validacoes"] if x.startswith("ERRO")]
    out["status_registry"] = "INVALIDO" if erros else ("VALIDO_COM_ALERTAS" if out["validacoes"] else "VALIDO")
    return out


def escrever_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    campos = [
        "id", "nome", "tipo", "script", "script_path", "script_encontrado", "script_ativo",
        "gera_trades", "usar_no_lab_dna", "status_registry", "arquivo_trades", "trades_encontrado",
        "trades_path", "trades_tamanho_mb", "trades_modificado_em", "trades_colunas_total",
        "trades_duplicidade_caminho", "validacoes",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=campos, extrasaction="ignore")
        w.writeheader()
        for m in rows:
            t = m.get("arquivos_resolvidos", {}).get("trades", {})
            w.writerow({
                "id": m.get("id"), "nome": m.get("nome"), "tipo": m.get("tipo"),
                "script": m.get("script"), "script_path": m.get("script_path"),
                "script_encontrado": m.get("script_encontrado"), "script_ativo": m.get("script_ativo"),
                "gera_trades": m.get("gera_trades"), "usar_no_lab_dna": m.get("usar_no_lab_dna"),
                "status_registry": m.get("status_registry"),
                "arquivo_trades": t.get("nome_declarado", ""), "trades_encontrado": t.get("encontrado", False),
                "trades_path": t.get("path", ""),
                "trades_tamanho_mb": round(t.get("tamanho_bytes", 0) / 1024 / 1024, 3) if t else 0,
                "trades_modificado_em": t.get("modificado_em", ""), "trades_colunas_total": t.get("colunas_total", 0),
                "trades_duplicidade_caminho": t.get("duplicidade_caminho", False),
                "validacoes": " | ".join(m.get("validacoes", [])),
            })


def main() -> int:
    parser = argparse.ArgumentParser(description="Cadastro e validação oficial das fontes C7")
    parser.add_argument("--base", default=str(BASE_PADRAO), help="Pasta raiz do projeto")
    parser.add_argument("--habilitar-13a", action="store_true", help="Habilita 13A no LAB somente após você confirmar seu CSV de trades")
    parser.add_argument("--csv-13a", default="", help="Nome ou caminho relativo do CSV original de trades do 13A")
    args = parser.parse_args()

    base = Path(args.base)
    if not base.exists():
        print(f"ERRO: pasta não encontrada: {base}")
        return 2

    outdir = base / PASTA_REGISTRY
    outdir.mkdir(parents=True, exist_ok=True)
    processos = processos_python()

    motores = json.loads(json.dumps(MOTORES_PRECONFIGURADOS))
    if args.csv_13a:
        for m in motores:
            if m["id"] == "c7_live_13a_shadow_engine_v2":
                m["arquivos"]["trades"] = args.csv_13a
                m["gera_trades"] = True
                m["usar_no_lab_dna"] = bool(args.habilitar_13a)
                m["observacao"] = "CSV do 13A informado manualmente e submetido à validação do registry."

    validados = [validar_motor(base, m, processos) for m in motores]

    auxiliares = []
    for a in AUXILIARES_PRECONFIGURADOS:
        path, cand = localizar_arquivo(base, a["script"])
        aux = dict(a)
        aux.update({
            "script_path": str(path) if path else "",
            "script_encontrado": bool(path),
            "script_ativo": script_ativo(a["script"], processos),
            "gera_trades": False,
            "usar_no_lab_dna": False,
        })
        auxiliares.append(aux)

    elegiveis = [m["id"] for m in validados if m.get("usar_no_lab_dna") and m["status_registry"] != "INVALIDO"]
    invalidos = [m["id"] for m in validados if m["status_registry"] == "INVALIDO"]

    registry = {
        "schema": "c7.registry.v1",
        "gerado_em": agora_iso(),
        "base": str(base),
        "principio": "Somente fontes declaradas e validadas entram na população de trades do LAB.",
        "motores": validados,
        "componentes_auxiliares": auxiliares,
        "politica_lab": {
            "motores_elegiveis": elegiveis,
            "excluir_relatorios_derivados": True,
            "termos_derivados_bloqueados": DERIVADOS_BLOQUEADOS,
            "deduplicacao": "por motor + horário de entrada + lado + preço de entrada",
            "campos_decisorios_proibidos_no_dna": [
                "aprovado", "aprovado_base", "hard_gates_ok", "qtd_hard_gates_ok",
                "regra", "regra_disparada", "sinal", "bloqueado", "resultado",
                "resultado_mt5", "mfe_mt5", "mae_mt5",
            ],
        },
        "resumo": {
            "motores_cadastrados": len(validados),
            "motores_elegiveis_lab": len(elegiveis),
            "motores_invalidos": len(invalidos),
            "processos_python_detectados": len(processos),
        },
    }

    with (outdir / ARQ_REGISTRY).open("w", encoding="utf-8") as f:
        json.dump(registry, f, ensure_ascii=False, indent=2)

    escrever_csv(outdir / ARQ_RELATORIO, validados)

    with (outdir / ARQ_PROCESSOS).open("w", encoding="utf-8-sig", newline="") as f:
        campos = ["ProcessId", "CreationDate", "ExecutablePath", "CommandLine"]
        w = csv.DictWriter(f, fieldnames=campos, extrasaction="ignore")
        w.writeheader()
        w.writerows(processos)

    linhas = [
        "C7 REGISTRY v1 — VEREDITO",
        "=" * 60,
        f"Gerado em: {registry['gerado_em']}",
        f"Motores cadastrados: {len(validados)}",
        f"Motores elegíveis para o LAB: {len(elegiveis)}",
        f"Elegíveis: {', '.join(elegiveis) if elegiveis else 'nenhum'}",
        f"Inválidos: {', '.join(invalidos) if invalidos else 'nenhum'}",
        "",
        "IMPORTANTE:",
        "- O registry não altera nem reinicia qualquer motor.",
        "- O 13A permanece fora da população até seu CSV original ser confirmado.",
        "- O próximo LAB deve ler apenas politica_lab.motores_elegiveis.",
    ]
    (outdir / ARQ_VEREDITO).write_text("\n".join(linhas), encoding="utf-8")

    print("\n".join(linhas))
    print(f"\nArquivos gerados em: {outdir}")
    print(f"Registry oficial: {outdir / ARQ_REGISTRY}")
    return 0 if not invalidos else 1


if __name__ == "__main__":
    raise SystemExit(main())
