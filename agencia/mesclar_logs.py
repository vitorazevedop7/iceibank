"""Parte E - mescla os logs .jsonl das 3 agencias em uma linha do tempo unica ordenada por Lamport.

Uso:  python mesclar_logs.py
"""

import json
import os
from collections import defaultdict

PASTA_DADOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def carregar_eventos() -> list[dict]:
    eventos = []
    if not os.path.isdir(PASTA_DADOS):
        return eventos
    for arquivo in sorted(os.listdir(PASTA_DADOS)):
        if not arquivo.endswith(".jsonl"):
            continue
        caminho = os.path.join(PASTA_DADOS, arquivo)
        with open(caminho, encoding="utf-8") as f:
            for linha in f:
                linha = linha.strip()
                if linha:
                    eventos.append(json.loads(linha))
    return eventos


def main() -> None:
    eventos = carregar_eventos()
    if not eventos:
        print("Nenhum evento encontrado em data/. Rode as agencias e faca operacoes antes.")
        return

    # Ordenacao pelo relogio LOGICO. O desempate por nome de agencia e apenas para
    # a saida ficar estavel entre execucoes - nao expressa nenhuma ordem causal.
    eventos.sort(key=lambda e: (e["timestampLamport"], e["agencia"]))

    print("=== Linha do tempo unificada (ordenada por relogio de Lamport) ===")
    for evento in eventos:
        print(
            f"[Lamport {evento['timestampLamport']:>3}] ({evento['horaParede']}) "
            f"{evento['agencia']} - {evento['tipo']} "
            f"{json.dumps(evento['detalhes'], ensure_ascii=False)}"
        )

    # Destaque dos empates: mesmo timestamp em agencias diferentes = eventos que o
    # relogio de Lamport nao consegue ordenar entre si.
    por_timestamp = defaultdict(list)
    for evento in eventos:
        por_timestamp[evento["timestampLamport"]].append(evento)

    empates = {
        ts: grupo
        for ts, grupo in por_timestamp.items()
        if len({e["agencia"] for e in grupo}) > 1
    }

    print()
    print("=== Empates de timestamp entre agencias diferentes ===")
    if not empates:
        print("Nenhum empate nesta execucao. Gere mais eventos concorrentes e rode de novo.")
        return

    for ts in sorted(empates):
        print(f"\nLamport {ts}:")
        for evento in sorted(empates[ts], key=lambda e: e["horaParede"]):
            print(f"  - {evento['agencia']:<10} {evento['tipo']:<28} horaParede={evento['horaParede']}")
        ordem_lamport = [e["agencia"] for e in empates[ts]]
        ordem_parede = [
            e["agencia"] for e in sorted(empates[ts], key=lambda e: e["horaParede"])
        ]
        print(f"  Lamport nao os ordena entre si; por hora de parede a ordem seria: {ordem_parede}")
        if ordem_lamport != ordem_parede:
            print("  (a ordem de leitura do arquivo difere da ordem por hora de parede)")


if __name__ == "__main__":
    main()
