# ICEIBank

Banco simplificado dividido em agencias, usado como projeto pratico da disciplina de
Sistemas Distribuidos (PUC Minas). O sistema evolui ao longo de 4 sprints no semestre,
cada um partindo do codigo do anterior.

| Sprint | Unidade | Tecnologia | Conceito de Sistemas Distribuidos |
|--------|---------|-----------|------------------------------------|
| 1 (atual) | U2 - Desenvolvimento Web | API REST / MVC | Relogio logico de Lamport |
| 2 | U3 - Comunicacao indireta | Mensageria / Pub-Sub | Relogio vetorial |
| 3 | U4 - Desenvolvimento Movel | App Flutter | Consenso (eleicao de lider) |
| 4 | U5 - Computacao em Nuvem | Containers | Transacoes distribuidas (2PC/Saga) |

## Arquitetura do Sprint 1

Uma agencia e um servico REST independente. O mesmo codigo e executado 3 vezes com
identidades diferentes (`AGENCIA_ID=0|1|2`), formando 3 agencias. As contas sao
**particionadas** (nao replicadas) entre elas: a agencia responsavel por uma conta e
`id_conta % 3`.

Toda operacao e carimbada com um timestamp de relogio logico de Lamport e registrada
em um arquivo de eventos por agencia, o que permite reconstruir uma linha do tempo
unificada das 3 agencias.

## Stack

- **Backend:** Python 3.12 + FastAPI (escolha mantida do Sprint 1 ao Sprint 4)
- **Comunicacao entre agencias:** HTTP/REST direto via `httpx`
- **Autenticacao:** JWT (HS256)
- **Frontend:** Vite + React + TypeScript
- **Estado:** em memoria, por processo (sem banco de dados neste sprint, por decisao do roteiro)

## Estrutura do repositorio

```
iceibank/
├── agencia/              # servico de agencia (executado 3x com AGENCIA_ID diferente)
│   ├── requirements.txt
│   ├── src/
│   │   ├── main.py           # cria o app, monta o estado do processo
│   │   ├── config.py         # particionamento e enderecos das agencias
│   │   ├── routes.py         # declaracao das rotas
│   │   ├── models/           # entidade Conta e schemas Pydantic
│   │   ├── controllers/      # contas e transferencias
│   │   ├── services/         # relogio de Lamport e registro de eventos
│   │   └── auth/             # autenticacao JWT
│   ├── data/                 # logs .jsonl gerados em execucao (fora do Git)
│   └── mesclar_logs.py       # linha do tempo unificada das 3 agencias
├── frontend/             # interface web que consome a API autenticada
├── evidencias/sprint1/   # prints de tela das execucoes
└── RESPOSTAS.md          # respostas as questoes e justificativas de design
```

## Como executar

_(a ser preenchido conforme as partes forem implementadas)_

### Backend

```bash
cd agencia
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Cada agencia sobe em um terminal proprio, identificada pela variavel de ambiente
`AGENCIA_ID`:

```bash
# Terminal 1
AGENCIA_ID=0 python -m src.main
# Terminal 2
AGENCIA_ID=1 python -m src.main
# Terminal 3
AGENCIA_ID=2 python -m src.main
```

### Frontend

_(a ser preenchido na Parte G)_

## Limitacao conhecida (intencional neste sprint)

Se uma transferencia entre agencias falhar depois do debito (agencia de destino fora do
ar, rede indisponivel), o debito **nao** e revertido automaticamente - o valor
desaparece temporariamente. O sistema apenas registra a inconsistencia no log. Resolver
isso de forma correta e o objetivo do Sprint 4, com uma transacao distribuida de
verdade (2PC ou Saga).
