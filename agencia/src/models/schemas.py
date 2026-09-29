"""Schemas Pydantic: validacao de entrada e formato de saida da API."""

from pydantic import BaseModel, Field

from src import config


class CriarContaRequest(BaseModel):
    id: int = Field(ge=0, description="Identificador da conta; define a agencia dona (id % 3)")
    nomeAluno: str = Field(min_length=1)
    saldoInicial: float = Field(default=0.0, ge=0)


class ValorRequest(BaseModel):
    valor: float = Field(gt=0, description="Valor da operacao; precisa ser positivo")


class TransferenciaRequest(BaseModel):
    idOrigem: int = Field(ge=0)
    idDestino: int = Field(ge=0)
    valor: float = Field(gt=0)


class MensagemCredito(BaseModel):
    """Mensagem publicada no RabbitMQ para creditar uma conta de outra agencia.

    Validada ao ser consumida: a mensagem vem de fora do processo, entao nao e
    confiavel so por ter chegado na fila.
    """

    idMensagem: str = Field(min_length=1)
    idOrigem: int = Field(ge=0)
    idConta: int = Field(ge=0)
    valor: float = Field(gt=0)
    vetorEnvio: list[int] = Field(
        min_length=config.NUMERO_AGENCIAS,
        max_length=config.NUMERO_AGENCIAS,
        description="Vetor do relogio da agencia de origem no momento do envio",
    )
    origemAgencia: int = Field(ge=0, lt=config.NUMERO_AGENCIAS)


class LoginRequest(BaseModel):
    usuario: str
    senha: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expira_em_segundos: int


class ContaResponse(BaseModel):
    id: int
    nomeAluno: str
    saldo: float
