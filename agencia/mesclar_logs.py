"""Parte D (Sprint 2) - linha do tempo causal das 3 agencias.

Mescla os logs .jsonl das agencias e, alem de listar os eventos, compara os
vetores do relogio vetorial para mostrar:

1. os pares de eventos de agencias DIFERENTES que sao comprovadamente
   concorrentes (nenhum vetor domina o outro: nenhum influenciou o outro);
2. para cada transferencia entre agencias, o par envio -> credito, que tem
   relacao causal e por isso NAO pode aparecer na lista de concorrentes.

Um vetor nao tem ordem total, entao a listagem usa a hora de parede apenas como
ordem de leitura; quem decide causalidade e concorrencia e `comparar_vetores`.

Uso:
    python mesclar_logs.py            # lista ate 20 pares concorrentes
    python mesclar_logs.py --todos    # lista todos os pares concorrentes
"""

import json
import os
import sys
from itertools import combinations

from src.services.relogio_vetorial import ANTES, CONCORRENTES, comparar_vetores

PASTA_DADOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
LIMITE_PARES = 20

# Eventos que recebem uma mensagem de outra agencia (regra 3 do relogio vetorial).
TIPOS_RECEBIMENTO = ("TRANSFERENCIA_CREDITO_REMOTO", "CREDITO_REMOTO_FALHOU")


def carregar_eventos() -> tuple[list[dict], int]:
    """Devolve (eventos com vetor, quantidade de eventos antigos ignorados)."""
    eventos = []
    ignorados = 0
    if not os.path.isdir(PASTA_DADOS):
        return eventos, ignorados
    for arquivo in sorted(os.listdir(PASTA_DADOS)):
        if not arquivo.endswith(".jsonl"):
            continue
        with open(os.path.join(PASTA_DADOS, arquivo), encoding="utf-8") as f:
            for linha in f:
                linha = linha.strip()
                if not linha:
                    continue
                evento = json.loads(linha)
                # Logs do Sprint 1 (timestampLamport) nao sao comparaveis com vetores.
                if "timestampVetorial" not in evento:
                    ignorados += 1
                    continue
                eventos.append(evento)
    return eventos, ignorados


def vetor(evento: dict) -> str:
    return "[" + ",".join(str(v) for v in evento["timestampVetorial"]) + "]"


def rotulo(evento: dict) -> str:
    return f"{evento['agencia']} {evento['tipo']} {vetor(evento)}"


def resumo_detalhes(evento: dict, limite: int = 90) -> str:
    texto = json.dumps(evento["detalhes"], ensure_ascii=False)
    return texto if len(texto) <= limite else texto[: limite - 3] + "..."


def pares_concorrentes(eventos: list[dict]) -> list[tuple[dict, dict]]:
    """Compara todos os pares de agencias diferentes - O(n^2) no numero de eventos."""
    return [
        (e1, e2)
        for e1, e2 in combinations(eventos, 2)
        if e1["agencia"] != e2["agencia"]
        and comparar_vetores(e1["timestampVetorial"], e2["timestampVetorial"])
        == CONCORRENTES
    ]


def pares_de_transferencia(eventos: list[dict]) -> list[tuple[dict, dict]]:
    """Casa cada envio com o recebimento correspondente pelo idMensagem."""
    envios = {
        e["detalhes"].get("idMensagem"): e
        for e in eventos
        if e["tipo"] == "TRANSFERENCIA_ENVIADA"
    }
    pares = []
    for recebimento in eventos:
        if recebimento["tipo"] in TIPOS_RECEBIMENTO:
            envio = envios.get(recebimento["detalhes"].get("idMensagem"))
            if envio is not None:
                pares.append((envio, recebimento))
    return pares


def main() -> None:
    listar_todos = "--todos" in sys.argv[1:]
    eventos, ignorados = carregar_eventos()
    if ignorados:
        print(
            f"(ignorados {ignorados} eventos sem timestampVetorial - logs antigos do "
            "Sprint 1; apague agencia/data/*.jsonl para comecar do zero)\n"
        )
    if not eventos:
        print("Nenhum evento encontrado em data/. Rode as agencias e faca operacoes antes.")
        return

    eventos.sort(key=lambda e: e["horaParede"])

    print("=== Linha do tempo (ordenada por hora de parede) ===")
    for e in eventos:
        print(f"[{e['agencia']}] vetor={vetor(e):<9} {e['tipo']:<30} {resumo_detalhes(e)}")

    concorrentes = pares_concorrentes(eventos)
    print(
        f"\n=== Pares de eventos CONCORRENTES entre agencias diferentes "
        f"({len(concorrentes)}) ==="
    )
    if not concorrentes:
        print(
            "(nenhum par concorrente encontrado nesta execucao - gere eventos "
            "independentes em agencias diferentes e rode de novo)"
        )
    exibidos = concorrentes if listar_todos else concorrentes[:LIMITE_PARES]
    for e1, e2 in exibidos:
        print(f"  {rotulo(e1):<46} x  {rotulo(e2)}")
    if len(exibidos) < len(concorrentes):
        print(f"  ... e mais {len(concorrentes) - len(exibidos)} (use --todos para ver todos)")

    transferencias = pares_de_transferencia(eventos)
    if transferencias:
        # Conferencia explicita: um par causal nunca pode estar entre os concorrentes.
        ids_concorrentes = {frozenset((id(a), id(b))) for a, b in concorrentes}
        print("\n=== Transferencias entre agencias: envio -> recebimento (relacao causal) ===")
        for envio, recebimento in transferencias:
            relacao = comparar_vetores(
                envio["timestampVetorial"], recebimento["timestampVetorial"]
            )
            status = (
                "ERRO: apareceu como concorrente"
                if frozenset((id(envio), id(recebimento))) in ids_concorrentes
                else "fora da lista de concorrentes"
            )
            seta = "aconteceu-ANTES de" if relacao == ANTES else relacao
            print(f"  {rotulo(envio)}  {seta}  {rotulo(recebimento)}  [{status}]")


if __name__ == "__main__":
    main()
