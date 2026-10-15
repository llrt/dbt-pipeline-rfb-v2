# ruff: noqa: E501  (tabelas de preço e listas de agentes)
"""Custo por agente dos lotes pós-v1 (v1.1.0 a v1.4.0), mesma metodologia de docs/CUSTOS_AGENTES.md (v1).

Fonte: transcripts do Claude Code (~/.claude/projects), deduplicados por (message.id, requestId).
Preços (US$/M tokens): Opus 5.5 4/20, leitura de cache 0,20; Sonnet 5/5.5 2/10, leitura 0,20; escrita de
cache = 2× a entrada (TTL de 1 h). Líder: sessões 96cb3a2c e 07fdca18 (a 2ª continua a 1ª e repete o
histórico; a deduplicação por chave evita contar duas vezes), só mensagens depois do commit da RETRO v1.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

P = Path.home() / ".claude/projects"
CORTE = datetime.fromisoformat("2026-10-01T18:16:15+00:00")
PRECOS = {"opus": (4.0, 20.0, 0.20), "sonnet": (2.0, 10.0, 0.20)}
CAMBIO = 5.021

AGENTES = [  # (nome, papel, versão, arquivo)
    ("FSEM, correções do Greptile (PR #1)", "correção", "v1.1.0", "feat-camada-semantica/be28762e"),
    (
        "FNEG, contexto de negócio e ontologia",
        "implementação",
        "v1.1.0",
        "feat-camada-semantica/e5c55658",
    ),
    ("RSEM, revisão independente", "revisão", "v1.1.0", "feat-camada-semantica/63422d06"),
    ("FRSEM, correções da RSEM", "correção", "v1.1.0", "feat-camada-semantica/3817dbc3"),
    ("DIC, dicionário de dados", "implementação", "v1.2.0", "feat-dicionario-dados/57c86681"),
    ("RDIC, revisão independente", "revisão", "v1.2.0", "feat-dicionario-dados/adbbc6b3"),
    ("FDIC, correções da RDIC", "correção", "v1.2.0", "feat-dicionario-dados/54f9b8e2"),
    (
        "FDIC2, comentários do Greptile (PR #3)",
        "correção",
        "v1.2.0",
        "feat-dicionario-dados/e33e890d",
    ),
    ("RN, regras de negócio", "implementação", "v1.3.0", "feat-regras-negocio/fec6fd8f"),
    ("RRN, revisão independente", "revisão", "v1.3.0", "feat-regras-negocio/cbc69df8"),
    ("FRN, correções da RRN", "correção", "v1.3.0", "feat-regras-negocio/abea4a0e"),
    ("FRN2, comentários do Greptile (PR #4)", "correção", "v1.3.0", "feat-regras-negocio/95e0c7e9"),
    (
        "IBG1, ingestão e staging do IBGE",
        "implementação",
        "v1.4.0",
        "feat-enriquecimento-ibge/a2d1b61b",
    ),
    (
        "IBG2, gold, RN-30, semântica, cenários e docs",
        "implementação",
        "v1.4.0",
        "feat-enriquecimento-ibge/40b9da39",
    ),
    ("RIBG, revisão independente", "revisão", "v1.4.0", "feat-enriquecimento-ibge/9fec1d03"),
    (
        "FIBG, correções da RIBG e versão 1.4.0",
        "correção",
        "v1.4.0",
        "feat-enriquecimento-ibge/c2edf933",
    ),
    (
        "FIBG2, comentários do Greptile (PR #7)",
        "correção",
        "v1.4.0",
        "feat-enriquecimento-ibge/c07f76f3",
    ),
]

DIR_LIDER = P / "-Users-llrt-dev-workspaces-code-to-learn-vibe-traycer-dbt-pipeline-rfb-v2"
SESSOES_LIDER = [
    DIR_LIDER / "96cb3a2c-0308-42ab-8801-7378d5689b08.jsonl",
    DIR_LIDER / "07fdca18-f82b-4b08-9f38-b41ad1e393d4.jsonl",
]


def linhas_de(arquivos: list[Path]):
    for f in arquivos:
        if f.exists():
            yield from f.open()


def arquivo(rel: str) -> Path:
    pasta, sessao = rel.split("/")
    d = next(P.glob(f"*rfb-v2-{pasta}"))
    return next(d.glob(f"{sessao}*.jsonl"))


def medir(arquivos: list[Path], desde: datetime | None = None) -> dict:
    vistos, tempos = set(), set()
    tot = {"in": 0, "out": 0, "cr": 0, "cw": 0, "usd": 0.0, "modelos": set()}
    for linha in linhas_de(arquivos):
        try:
            o = json.loads(linha)
        except json.JSONDecodeError:
            continue
        t = o.get("timestamp")
        if not t:
            continue
        ts = datetime.fromisoformat(t.replace("Z", "+00:00"))
        if desde and ts <= desde:
            continue
        tempos.add(ts)
        msg = o.get("message") or {}
        uso, modelo = msg.get("usage"), msg.get("model") or ""
        if o.get("type") != "assistant" or not uso or "synthetic" in modelo:
            continue
        chave = (msg.get("id"), o.get("requestId"))
        if chave in vistos:
            continue
        vistos.add(chave)
        familia = "opus" if "opus" in modelo else "sonnet"
        pin, pout, pcr = PRECOS[familia]
        i, out = uso.get("input_tokens", 0), uso.get("output_tokens", 0)
        cr, cw = uso.get("cache_read_input_tokens", 0), uso.get("cache_creation_input_tokens", 0)
        tot["in"] += i
        tot["out"] += out
        tot["cr"] += cr
        tot["cw"] += cw
        tot["usd"] += (i * pin + out * pout + cr * pcr + cw * 2 * pin) / 1e6
        tot["modelos"].add(modelo)
    tempos = sorted(tempos)
    horas = (
        sum(
            (b - a).total_seconds()
            for a, b in zip(tempos, tempos[1:], strict=False)
            if b - a <= timedelta(minutes=30)
        )
        / 3600
    )
    tot["horas"] = horas
    return tot


def nome_modelo(modelos: set) -> str:
    m = " ".join(sorted(modelos))
    if "opus-5-5" in m:
        return "Claude Opus 5.5"
    if "sonnet-5-5" in m:
        return "Claude Sonnet 5.5"
    return m


linhas = []
lider = medir(SESSOES_LIDER, CORTE)
linhas.append(
    (
        "Líder (pós-v1: publicação, CI, releases, Fusion, lotes AF/SEM inline, avaliações, orquestração)",
        "líder",
        "todas",
        lider,
    )
)
for nome, papel, versao, rel in AGENTES:
    linhas.append((nome, papel, versao, medir([arquivo(rel)])))

print(
    json.dumps(
        [
            {
                "agente": n,
                "papel": p,
                "versao": v,
                "modelo": nome_modelo(t["modelos"]),
                "saida": t["out"],
                "leitura_cache": t["cr"],
                "entrada_escrita": t["in"] + t["cw"],
                "horas": round(t["horas"], 2),
                "usd": round(t["usd"], 2),
                "brl": round(t["usd"] * CAMBIO, 2),
            }
            for n, p, v, t in linhas
        ],
        ensure_ascii=False,
        indent=1,
    )
)


# Fases do líder (mesma passada, para somar ao total do líder)
FASES = [
    ("publicação no GitHub, CI e v1.0.0", "2026-10-01T18:16:15+00:00"),
    ("avaliação do Fusion, lote AF inline e v1.0.1", "2026-10-02T15:19:05+00:00"),
    ("camada semântica inicial inline", "2026-10-10T01:51:15+00:00"),
    ("orquestração delegada v1.1.0 a v1.3.0", "2026-10-10T02:07:51+00:00"),
    ("PR #5, housekeeping e avaliações (bairro, fontes gratuitas)", "2026-10-13T19:24:06+00:00"),
    ("orquestração delegada v1.4.0", "2026-10-14T11:18:49+00:00"),
]
lim = [datetime.fromisoformat(t) for _, t in FASES] + [
    datetime.fromisoformat("2099-01-01T00:00:00+00:00")
]
fase_usd, fase_t, vistos = [0.0] * len(FASES), [set() for _ in FASES], set()
for linha in linhas_de(SESSOES_LIDER):
    try:
        o = json.loads(linha)
    except json.JSONDecodeError:
        continue
    t = o.get("timestamp")
    if not t:
        continue
    ts = datetime.fromisoformat(t.replace("Z", "+00:00"))
    if ts <= lim[0]:
        continue
    i = next(k for k in range(len(FASES)) if lim[k] < ts <= lim[k + 1])
    fase_t[i].add(ts)
    m = o.get("message") or {}
    u = m.get("usage")
    if o.get("type") != "assistant" or not u or "synthetic" in (m.get("model") or ""):
        continue
    k = (m.get("id"), o.get("requestId"))
    if k in vistos:
        continue
    vistos.add(k)
    fase_usd[i] += (
        u.get("input_tokens", 0) * 4
        + u.get("output_tokens", 0) * 20
        + u.get("cache_read_input_tokens", 0) * 0.2
        + u.get("cache_creation_input_tokens", 0) * 8
    ) / 1e6
print(
    "FASES",
    json.dumps(
        [
            {
                "fase": n,
                "usd": round(fase_usd[i], 2),
                "brl": round(fase_usd[i] * CAMBIO, 2),
                "horas": round(
                    sum(
                        (b - a).total_seconds()
                        for a, b in zip(sorted(fase_t[i]), sorted(fase_t[i])[1:], strict=False)
                        if b - a <= timedelta(minutes=30)
                    )
                    / 3600,
                    2,
                ),
            }
            for i, (n, _) in enumerate(FASES)
        ],
        ensure_ascii=False,
    ),
)
