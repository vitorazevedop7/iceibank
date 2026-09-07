"""Entidade de dominio: a conta bancaria mantida por uma agencia."""

from dataclasses import dataclass


@dataclass
class Conta:
    """Conta bancaria sob responsabilidade desta agencia.

    O estado vive em memoria no processo da agencia (sem banco de dados neste
    sprint, por decisao do roteiro): se o processo for reiniciado, as contas somem.
    """

    id: int
    nome_aluno: str
    saldo: float = 0.0

    def para_dict(self) -> dict:
        return {"id": self.id, "nomeAluno": self.nome_aluno, "saldo": self.saldo}
