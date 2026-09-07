"""Parte B - registro de eventos em arquivo .jsonl (uma linha JSON por evento).

Esses arquivos sao a materia-prima da linha do tempo unificada da Parte E.
"""

import json
import os
from datetime import datetime, timezone

_PASTA_DADOS = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "data"
)


class RegistroEventos:
    def __init__(self, nome_agencia: str) -> None:
        self.nome_agencia = nome_agencia
        os.makedirs(_PASTA_DADOS, exist_ok=True)
        self.caminho_arquivo = os.path.join(
            _PASTA_DADOS, f"eventos-{nome_agencia}.jsonl"
        )

    def registrar(self, tipo: str, timestamp_lamport: int, detalhes: dict) -> dict:
        """Grava um evento e o ecoa no console da agencia.

        Cada evento guarda dois carimbos de tempo: `timestampLamport` (o relogio
        logico, unico usado para ordenar) e `horaParede` (o relogio fisico da
        maquina, mantido apenas para comparacao na Parte E - nenhuma decisao do
        sistema depende dele).
        """
        evento = {
            "agencia": self.nome_agencia,
            "tipo": tipo,
            "timestampLamport": timestamp_lamport,
            "horaParede": datetime.now(timezone.utc).isoformat(),
            "detalhes": detalhes,
        }
        with open(self.caminho_arquivo, "a", encoding="utf-8") as arquivo:
            arquivo.write(json.dumps(evento, ensure_ascii=False) + "\n")
        print(f"[Lamport {timestamp_lamport}] {tipo} {detalhes}", flush=True)
        return evento
