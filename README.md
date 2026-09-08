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

## Video de apresentacao

<!-- COLE AQUI O LINK DO VIDEO (YouTube nao listado ou Google Drive com acesso liberado) -->
**Link:** _(a preencher)_

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

### Backend - as 3 agencias

```bash
cd agencia
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Cada agencia e o mesmo codigo, identificada pela variavel de ambiente `AGENCIA_ID`.
Abra tres terminais:

```bash
# Terminal 1
cd agencia && source venv/bin/activate && AGENCIA_ID=0 python -m src.main
# Terminal 2
cd agencia && source venv/bin/activate && AGENCIA_ID=1 python -m src.main
# Terminal 3
cd agencia && source venv/bin/activate && AGENCIA_ID=2 python -m src.main
```

As agencias sobem em `localhost:4000`, `4001` e `4002`. Se precisar de portas exclusivas
(maquina compartilhada de laboratorio), defina `OFFSET` com os dois ultimos digitos da
matricula: `OFFSET=42 AGENCIA_ID=0 python -m src.main`.

Confira se estao no ar:

```bash
curl -s http://localhost:4000/status
```

Documentacao interativa da API (gerada pelo FastAPI): <http://localhost:4000/docs>

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Abre em <http://localhost:5173>. O seletor "porta de entrada" no topo escolhe com qual
das 3 agencias a tela vai falar.

### Usuarios de teste

| Usuario | Senha | Contas | Agencia de cada conta |
|---------|-------|--------|------------------------|
| `ana`   | `senha123` | 0, 3 | Agencia 0, Agencia 0 |
| `bruno` | `senha123` | 1, 4 | Agencia 1, Agencia 1 |
| `carla` | `senha123` | 2, 5 | Agencia 2, Agencia 2 |

### Linha do tempo unificada

Depois de gerar operacoes, mescla os logs das 3 agencias ordenados por relogio de Lamport:

```bash
cd agencia && python mesclar_logs.py
```

### Testes do relogio de Lamport

```bash
cd agencia && python -m pytest tests/ -v
```

### Roteiro de demonstracao

`agencia/demonstracao.sh` executa a sequencia completa (login, particao, autorizacao,
transferencia local, transferencia entre agencias, idempotencia e cenarios de JWT),
pausando entre as etapas para captura de evidencias:

```bash
cd agencia && ./demonstracao.sh
```

Em macOS, `agencia/capturar-evidencias.sh` faz o mesmo percurso e **captura os prints
automaticamente** em `evidencias/sprint1/`, com a data visivel em cada tela:

```bash
cd agencia && ./capturar-evidencias.sh
```

## Endpoints

| Metodo | Rota | Protecao | Descricao |
|--------|------|----------|-----------|
| POST | `/auth/login` | publica | Autentica e devolve o JWT |
| POST | `/contas` | token de usuario | Cria conta (recusa conta de outra agencia) |
| GET | `/contas/{id}` | token de usuario | Consulta saldo |
| POST | `/contas/{id}/depositar` | token de usuario | Deposito |
| POST | `/contas/{id}/sacar` | token de usuario | Saque |
| POST | `/transferencias` | token de usuario | Transferencia local ou entre agencias. Aceita `Idempotency-Key` |
| POST | `/contas/{id}/creditar-remoto` | token de servico | Rota interna, chamada por outra agencia |
| GET | `/status` | publica | Identidade da agencia, relogio de Lamport atual e contas sob sua guarda |

## Limitacao conhecida (intencional neste sprint)

Se uma transferencia entre agencias falhar depois do debito (agencia de destino fora do
ar, rede indisponivel), o debito **nao** e revertido automaticamente - o valor
desaparece temporariamente. O sistema apenas registra a inconsistencia no log. Resolver
isso de forma correta e o objetivo do Sprint 4, com uma transacao distribuida de
verdade (2PC ou Saga).
