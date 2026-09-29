"""Mescla os logs .jsonl das 3 agencias em uma unica linha do tempo.

Sprint 2: os eventos passam a carregar o vetor do relogio vetorial
(`timestampVetorial`). Um vetor nao tem ordem total, entao a listagem usa a hora de
parede apenas como ordem de leitura; a relacao causal entre eventos e decidida
pela comparacao dos vetores.

Uso:  python mesclar_logs.py
"""

import json
import os

PASTA_DADOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def carregar_eventos() -> tuple[list[dict], int]:
    """Devolve (eventos com vetor, quantidade de eventos antigos ignorados)."""
    eventos = []
    ignorados = 0
    if not os.path.isdir(PASTA_DADOS):
        return eventos, ignorados
    for arquivo in sorted(os.listdir(PASTA_DADOS)):
        if not arquivo.endswith(".jsonl"):
            continue
        caminho = os.path.join(PASTA_DADOS, arquivo)
        with open(caminho, encoding="utf-8") as f:
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


def main() -> None:
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
    for evento in eventos:
        print(
            f"[{evento['agencia']}] vetor={evento['timestampVetorial']} "
            f"({evento['horaParede']}) {evento['tipo']} "
            f"{json.dumps(evento['detalhes'], ensure_ascii=False)}"
        )


if __name__ == "__main__":
    main()
