# ICEIBank - Respostas e decisoes de design

Disciplina de Sistemas Distribuidos - PUC Minas
Backend em Python + FastAPI | Frontend em Vite + React + TypeScript

- [Sprint 2 - Mensageria (Publish/Subscribe) e relogio vetorial](#sprint-2---mensageria-publishsubscribe-e-relogio-vetorial)
- [Sprint 1 - API REST/MVC e relogio de Lamport](#sprint-1---api-restmvc-e-relogio-de-lamport)

---

# Sprint 2 - Mensageria (Publish/Subscribe) e relogio vetorial

Evidencias em `evidencias/sprint2/`. Todas foram geradas pelo script
`agencia/capturar-evidencias-sprint2.sh`, executado contra a instancia RabbitMQ do CloudAMQP
(plano Little Lemur).

| Print | O que mostra |
|-------|--------------|
| `transferencia-assincrona.png` | transferencia 0 -> 1 pela fila, com o log das duas agencias |
| `resiliencia-fila.png` | Agencia 1 fora do ar, mensagem retida na fila e o que acontece quando ela volta |
| `linha-do-tempo-causal.png` | pares concorrentes e o par causal envio -> credito |
| `funcionalidade-adicional.png` | dead-letter queue: falha, fila-mortas, reprocessamento |
| `frontend-regressao.png` | frontend do Sprint 1 fazendo uma transferencia entre agencias pela fila |

---

## Parte B - Relogio vetorial (secao 6.4)

### 1. Com 10 agencias, o que acontece com o tamanho do vetor anexado a cada mensagem? Isso e um problema?

O vetor tem uma posicao por agencia, entao cresce **linearmente**: com 10 agencias, cada mensagem
e cada evento do log carregam 10 inteiros em vez de 3. Para 3 ou 10 agencias isso nao e problema -
sao dezenas de bytes perto do resto da mensagem (`idMensagem`, conta, valor).

O problema aparece em outras duas situacoes:

- **Escala:** com milhares de processos, o vetor passa a ser maior que a propria mensagem, e cada
  comparacao custa O(N). Isso tambem pesa no `mesclar_logs.py`, que compara vetores par a par.
- **Numero de participantes fixo:** o vetor pressupoe que todo mundo sabe quantos processos
  existem. No nosso codigo isso esta em `config.NUMERO_AGENCIAS`, e o schema `MensagemCredito`
  exige um `vetorEnvio` com exatamente esse tamanho. Colocar uma 4a agencia exige reiniciar todas
  com a configuracao nova; uma agencia antiga mandando vetor de 3 posicoes teria a mensagem
  rejeitada.

Solucoes conhecidas para isso: enviar so as posicoes que mudaram, usar *version vectors* por
item de dado em vez de por processo, ou estruturas que crescem e encolhem com os participantes
(*interval tree clocks*). Quando so e preciso uma ordem aproximada, relogios hibridos (HLC)
resolvem com tamanho constante.

### 2. `V1 = [3, 1, 0]` e `V2 = [3, 2, 0]`: qual aconteceu primeiro?

**V1 aconteceu antes de V2.** Comparando posicao a posicao:

| posicao | V1 | V2 | |
|---|---|---|---|
| 0 | 3 | 3 | igual |
| 1 | 1 | 2 | V1 menor |
| 2 | 0 | 0 | igual |

Todas as posicoes de V1 sao menores ou iguais as de V2 e os vetores sao diferentes. Na pratica,
e o que se ve quando a agencia 1 registra mais um evento proprio depois de V1: so a posicao dela
avanca. O caso esta coberto em `tests/test_relogio_vetorial.py`
(`test_pergunta_2_da_secao_6_4_v1_aconteceu_antes`).

### 3. `V1 = [3, 1, 0]` e `V2 = [1, 3, 0]`: qual aconteceu primeiro?

**Sao concorrentes.** Na posicao 0, V1 e maior (3 > 1); na posicao 1, V2 e maior (3 > 1). Nenhum
domina o outro: V1 "sabe" de eventos da agencia 0 que V2 nao conhece, e V2 sabe de eventos da
agencia 1 que V1 nao conhece. Entao nenhum dos dois pode ter influenciado o outro. Coberto por
`test_pergunta_3_da_secao_6_4_concorrentes`.

---

## Parte C - Publish/Subscribe entre agencias (secao 7.5)

### 1. O que aconteceu quando a Agencia 1 voltou? A mensagem "sumiu" por falha da mensageria?

Sequencia observada (`resiliencia-fila.png`):

1. Com a Agencia 1 derrubada, a transferencia de R$ 10 da conta 0 para a conta 1 respondeu
   **HTTP 200** ("publicada para a Agencia 1"), e a `fila-agencia-1` ficou com **1 mensagem**.
2. Ao subir de novo, a Agencia 1 conectou, assinou a fila e consumiu a mensagem na hora:

   ```
   [Agencia 1] consumindo a fila fila-agencia-1
   [Vetor [3, 1, 0]] CREDITO_REMOTO_FALHOU {... 'idConta': 1, 'valor': 10.0,
                     'vetorRecebido': [3, 0, 0], 'motivo': 'conta nao encontrada'}
   ```
3. A fila voltou a 0 mensagens e `GET /contas/1` respondeu **404**.

**A mensageria nao falhou:** a mensagem ficou retida enquanto nao havia consumidor, foi entregue
assim que a agencia voltou, e o vetor mostra a regra 3 funcionando (`[3,0,0]` recebido, `[3,1,0]`
resultante). O credito nao foi aplicado porque a **conta nao existia mais**: as contas vivem na
memoria do processo, e o processo novo da Agencia 1 comecou vazio. A mensagem chegou, mas nao
encontrou onde aplicar o valor.

Com a funcionalidade adicional (dead-letter), esse credito nao e mais descartado: depois de duas
tentativas ele vai para a `fila-mortas` e pode ser reprocessado quando a conta for recriada.

### 2. O que melhorou em relacao ao Sprint 1 e o que continua em aberto?

**O que melhorou:**

- **Desacoplamento no tempo.** No Sprint 1, com a agencia de destino fora do ar, a chamada REST
  falhava na hora (502) e o debito ficava aplicado sem credito (`TRANSFERENCIA_FALHOU`). Agora a
  origem so precisa que o *broker* esteja no ar: a mensagem e duravel (`durable` na fila e
  `persistent` na mensagem) e espera o destino voltar.
- **Falha local detectavel.** Com *publisher confirms* e `mandatory`, a origem sabe se o broker
  aceitou a mensagem. Se nao aceitou, a falha e local e sincrona, e o debito e **estornado**
  (`TRANSFERENCIA_ESTORNADA`, HTTP 503) - coisa que no Sprint 1 nao dava para fazer com seguranca.

**O que continua em aberto** - "a mensagem nao se perde" nao e o mesmo que "o sistema esta
correto":

- **O dinheiro ainda pode sumir.** No teste de resiliencia, a Ana foi debitada em R$ 10 e ninguem
  foi creditado: a soma dos saldos do banco diminuiu. A mensagem estava intacta; o estado da
  agencia e que nao. Isso so se resolve com persistencia das contas e com uma transacao
  distribuida (2PC ou Saga, Sprint 4) que desfaca o debito quando o credito nao for possivel.
- **O 200 mudou de sentido.** Agora ele significa "publicada", nao "creditada". A origem nao fica
  sabendo se o credito foi aplicado; nao ha confirmacao de volta nem compensacao automatica.
- **Entrega pelo menos uma vez.** O ack e enviado depois de aplicar o credito. Se a agencia cair
  entre aplicar e confirmar, o RabbitMQ reentrega e o credito seria aplicado duas vezes. A
  mensagem ja carrega um `idMensagem` unico, que e o que permitiria um consumidor idempotente.
- **Caso ambiguo na publicacao.** Se a confirmacao do broker nao chegar a tempo (timeout), o
  codigo estorna, mas a mensagem pode ter sido gravada mesmo assim.

### 3. O consumidor processa creditos sem verificar JWT. Isso e um problema de seguranca?

**Sim, em principio.** A fronteira de confianca mudou de lugar. No Sprint 1, a rota
`/contas/{id}/creditar-remoto` so aceitava um JWT de servico (`tipo: servico`); quem nao tivesse a
chave nao conseguia creditar conta nenhuma. Com a mensageria essa rota deixou de existir, e o
consumidor aplica **qualquer** mensagem que chegue na fila da agencia.

Hoje, quem consegue publicar na exchange e quem tem a URL AMQP da instancia - usuario e senha do
vhost do CloudAMQP. No meu ambiente de desenvolvimento, isso e so eu: a URL fica em `agencia/.env`,
que esta fora do Git. Mas as 3 agencias usam o **mesmo** usuario, com permissao total no vhost.
Quem obtiver essa URL publica `agencia.1.creditar` com qualquer valor e credita qualquer conta, sem
passar por login nem por autorizacao de dono da conta. A validacao do schema `MensagemCredito`
barra mensagens malformadas, mas nao mensagens forjadas.

O que eu faria num sistema real:

- **Um usuario do broker por agencia, com permissoes restritas:** cada agencia so le a propria fila
  e so escreve em `iceibank.eventos`. Isso limita o estrago se uma credencial vazar.
- **Assinar a mensagem** (HMAC ou JWT de servico) e verificar no consumidor. Um detalhe observado
  aqui: o token de servico do Sprint 1 expirava em 30 s, e isso nao serve para mensageria, porque
  uma mensagem pode ficar horas na fila enquanto a agencia esta fora do ar. A validade precisa ser
  longa, e o `idMensagem` passa a ser necessario para impedir que a mesma mensagem assinada seja
  reenviada (replay).
- Manter TLS na conexao, o que ja acontece hoje (`amqps://`).

---

## Parte D - Linha do tempo causal (secao 8.3)

### 1. O que, no relogio vetorial, torna possivel a comparacao confiavel?

O vetor guarda **um contador por agencia**: a posicao `i` diz quantos eventos da agencia `i` o
evento "conhece", seja porque aconteceram antes dele na mesma agencia, seja porque chegaram por
mensagem. Por isso a comparacao vale nos **dois sentidos**:

- a aconteceu-antes de b **se e somente se** V(a) <= V(b) posicao a posicao (e V(a) != V(b));
- se nenhum domina o outro, os eventos sao comprovadamente concorrentes.

O Lamport so garante a ida (a -> b implica L(a) < L(b)). Ele resume tudo num numero e perde a
informacao de **qual** agencia contribuiu para aquele valor, entao dois numeros diferentes nao
dizem se houve relacao causal.

### 2. Um par classificado como concorrente no meu teste faz sentido?

Do `linha-do-tempo-causal.png`:

```
agencia-2 CRIAR_CONTA [0,0,1]  x  agencia-0 TRANSFERENCIA_ENVIADA [3,0,0]
```

Faz sentido. A Carla criou a conta 2 na Agencia 2 enquanto a Ana transferia para o Bruno a partir
da Agencia 0. Nessa execucao nenhuma mensagem trafegou entre a Agencia 0 e a Agencia 2. O vetor da
Agencia 2 tem 0 na posicao da Agencia 0 (ela nao sabia de nada que a Agencia 0 fez), e o vetor da
Agencia 0 tem 0 na posicao da Agencia 2. Nenhum dos eventos poderia ter influenciado o outro.

A mesma saida mostra o contraste: `agencia-0 TRANSFERENCIA_ENVIADA [3,0,0]` aparece como
**aconteceu-ANTES** de `agencia-1 TRANSFERENCIA_CREDITO_REMOTO [3,2,0]`, e o script confere que esse
par **nao** esta entre os 13 concorrentes. O credito so existiu porque a mensagem foi enviada.

A listagem por hora de parede colocou a criacao da conta da Carla em primeiro lugar, mas isso so
reflete qual requisicao chegou primeiro no relogio da maquina, nao uma relacao de causa.

### 3. O algoritmo O(n^2) seria um problema com milhoes de eventos? Como escalar?

Seria inviavel: um milhao de eventos da cerca de 5 x 10^11 pares, cada um com uma comparacao de
vetor. E a propria saida nao serviria para nada, porque a maioria dos pares entre agencias
diferentes seria concorrente.

Formas de tornar a analise escalavel:

- **Usar a estrutura do problema.** Os eventos de uma mesma agencia ja estao totalmente ordenados
  e os vetores so crescem. Para um evento `e` da agencia A, os eventos da agencia B concorrentes a
  ele formam um **intervalo** contiguo: comecam depois do evento de numero `V(e)[B]` e terminam
  antes do primeiro evento de B que ja conhece `e`. Esse limite sai por busca binaria. O custo cai
  para O(n log n) por par de agencias, e o resultado e representado como intervalos, nao como
  milhoes de pares.
- **Restringir a pergunta.** Em geral so interessam concorrencias que podem dar conflito, por
  exemplo operacoes sobre a **mesma conta**. Agrupar por conta antes de comparar reduz muito o n.
- **Janela de tempo e processamento incremental.** Analisar em fluxo, comparando cada evento novo
  so com os de uma janela recente, em vez de reprocessar o historico inteiro.

---

## Funcionalidade adicional - dead-letter queue (secao 2.1)

### O que ela faz

Mensagens de credito que nao podem ser processadas deixam de ser descartadas e vao para uma fila
separada, a `fila-mortas`, de onde podem ser inspecionadas e reprocessadas.

- **Topologia:** exchange `iceibank.mortas` (fanout, duravel) ligada a `fila-mortas` (duravel). As
  filas das agencias sao declaradas com o argumento `x-dead-letter-exchange: iceibank.mortas`.
- **Politica de nova tentativa** (`services/mensageria.py`): se o processamento falha na primeira
  entrega, a mensagem volta para a fila (`reject(requeue=True)`). Se falha de novo (mensagem
  marcada como `redelivered`), o consumidor a rejeita sem reenfileirar e o **proprio RabbitMQ** a
  move para a `fila-mortas`, com o cabecalho `x-death` dizendo de qual fila veio e por que.
- **O que conta como falha:** conta de destino inexistente (o cenario do teste de resiliencia) e
  mensagem malformada. O controller levanta `CreditoNaoAplicado` e registra
  `CREDITO_REMOTO_FALHOU` com `tentativa` e `destino`.
- **Ferramenta de operacao:** `python mensagens_mortas.py` lista a fila-mortas sem remover nada;
  `python mensagens_mortas.py --reprocessar` republica cada mensagem na routing key original.
- **Migracao:** filas criadas antes desta funcionalidade nao tem o argumento, e o RabbitMQ nao
  deixa alterar argumentos de uma fila existente. Ao subir, a agencia recria essas filas
  automaticamente, **somente se estiverem vazias**, para nao perder credito.

### Por que escolhi implementa-la

Ela ataca diretamente o problema que o teste de resiliencia expos. Sem ela, o credito para a conta
perdida era registrado como falha e a mensagem era confirmada (ack): o valor saia da conta da Ana e
desaparecia. Com ela, o credito fica guardado e recuperavel, e o sistema passa a distinguir falha
temporaria (vale tentar de novo) de falha que precisa de intervencao.

### Evidencia

`evidencias/sprint2/funcionalidade-adicional.png`: transferencia de R$ 30 para a conta 1
inexistente -> duas tentativas no log da Agencia 1 -> mensagem na `fila-mortas` com motivo
`rejected` -> conta 1 recriada e mensagem reprocessada -> saldo da conta 1 passa de 50 para
**80** e a fila-mortas volta a 0. O vetor do credito final (`[3, 4, 0]`) mostra que o
reprocessamento preservou a causalidade original: o `vetorEnvio` continua sendo `[3, 0, 0]`.

---

## Decisoes de design do Sprint 2

### Cliente RabbitMQ: aio-pika em vez de pika

O roteiro sugere o `pika`, mas ele e bloqueante: em FastAPI, o consumidor teria de rodar numa
thread separada. Ai `contas` e o relogio passariam a ser acessados por duas threads, o
`asyncio.Lock` do relogio nao protegeria entre elas, e a garantia do Sprint 1 (sem `await` entre a
checagem de saldo e o debito, o trecho e atomico no event loop) deixaria de valer. Com o
`aio-pika`, o consumidor e iniciado no `lifespan` do FastAPI e roda no **mesmo event loop** do
uvicorn, entao o modelo de concorrencia continua o mesmo. O `connect_robust` tambem reconecta
sozinho se o broker cair, o que foi observado nos testes.

### Toda agencia declara a topologia inteira

Se cada agencia declarasse so a propria fila, uma agencia que nunca subiu naquele broker nao teria
fila, e o RabbitMQ descartaria em silencio uma mensagem com a routing key dela. Por isso cada
agencia declara a exchange, as 3 filas e os bindings (a declaracao e idempotente), e a publicacao
usa `mandatory=True` com *publisher confirms*, para que uma falha de roteamento vire excecao.

### Debito antes de qualquer `await`

Com o consumidor dividindo o event loop com as requisicoes HTTP, passou a importar ainda mais que
nao haja ponto de suspensao entre a checagem de saldo e o debito. Nas transferencias e no saque, o
debito agora e aplicado **antes** de `await relogio.evento_local()`.

### `idMensagem` e evento `TRANSFERENCIA_ENVIADA`

Cada transferencia entre agencias gera um UUID que vai na mensagem e no log das duas pontas. E ele
que permite ao `mesclar_logs.py` casar envio e recebimento (e provar o par causal), a
`fila-mortas` identificar o credito, e, no futuro, deduplicar reentregas.

### Token de servico removido

A rota `creditar-remoto` e o token de servico do Sprint 1 viraram codigo morto e foram removidos.
O que substitui essa protecao e discutido na pergunta 3 da Parte C.

### Credenciais do broker fora do Git

A `RABBITMQ_URL` carrega usuario e senha, e o repositorio e publico. Ela e lida de
`agencia/.env` (python-dotenv), que esta no `.gitignore`; o repositorio traz so um
`agencia/.env.example`.

### Instancia CloudAMQP

O plano gratis que o CloudAMQP oferece por padrao hoje ("Loyal Lemming") e LavinMQ, nao RabbitMQ.
Usei o **Little Lemur**, que e RabbitMQ, para seguir o roteiro.

---

## Regressao do Sprint 1 (verificada, nao presumida)

Com as agencias rodando contra o CloudAMQP, em 29/09/2026:

| Verificacao | Resultado |
|---|---|
| Login pelo frontend (bruno na Agencia 1, ana na Agencia 0) | ok |
| Criar conta pelo frontend | "Conta 1 criada na Agencia 1" / "Conta 0 criada na Agencia 0" |
| Transferencia 0 -> 1 pelo frontend | "publicada para a Agencia 1; o credito sera aplicado de forma assincrona", vetor `[3, 0, 0]` |
| Saldo da conta 1 depois da transferencia | 80 (50 + 30), credito aplicado pela fila |
| `GET /contas/0` sem token | 401 |
| `GET /contas/0` com token invalido | 401 |
| bruno consultando a conta 0 (da ana) | 403 (autorizacao por dono da conta continua valendo) |
| `POST /contas/1/creditar-remoto` (rota do Sprint 1) | 404 (removida, como pede o roteiro) |
| Testes do relogio vetorial (`python -m pytest tests/`) | 14 passaram |

---

## Declaracao de uso de IA

Usei o Claude (Anthropic) como assistente neste sprint, no chat e no Claude Code: para discutir a arquitetura (escolha do
aio-pika, topologia de filas, dead-letter), gerar e revisar o codigo, escrever os testes e o script
de captura de evidencias, e redigir a primeira versao destas respostas. Executei todos os cenarios
na minha maquina contra a minha instancia do CloudAMQP, conferi os resultados nos prints e sou
capaz de explicar e defender cada trecho entregue.

---

# Sprint 1 - API REST/MVC e relogio de Lamport

## Parte B - Relogio de Lamport e registro de eventos (secao 6.4)

### 1. Por que o relogio de Lamport usa `max(contador_local, timestampRecebido) + 1` ao receber uma mensagem, em vez de simplesmente adotar o timestamp recebido diretamente?

Porque adotar o timestamp recebido diretamente permitiria que o relogio **retrocedesse**, e um
relogio que anda para tras quebra a propriedade que justifica o algoritmo inteiro.

Suponha que a Agencia 1 ja processou 20 eventos proprios (contador 20) e recebe uma mensagem
carimbada com 5. Se ela simplesmente adotasse 5, o proximo evento local dela receberia timestamp 6 -
menor que o timestamp 20 de um evento que ja tinha acontecido antes dele *na propria agencia*.
A relacao "aconteceu-antes" dentro de um mesmo processo, que e a mais obvia de todas, ficaria
invertida na linha do tempo.

O `max` garante que o relogio nunca anda para tras: ele fica no maior valor entre o que a agencia ja
sabia e o que o remetente informou. E o `+ 1` garante a desigualdade **estrita**: o evento de
recebimento precisa ser estritamente maior que o envio, senao os dois ficariam empatados e a
ordem causal entre eles - que existe de verdade, porque nao se recebe algo antes de ser enviado -
se perderia.

Na pratica, isso apareceu no nosso log. A Agencia 0 enviou um credito remoto com `ao_enviar()` = 8;
a Agencia 1, que estava no contador 1, aplicou `max(1, 8) + 1 = 9`:

```
[Lamport 8] agencia-0 - TRANSFERENCIA_DEBITO {"idOrigem": 0, "idDestino": 1, "agenciaDestino": 1}
[Lamport 9] agencia-1 - TRANSFERENCIA_CREDITO_REMOTO {"timestampRecebido": 8, "chamadaPor": "agencia-0"}
```

O credito ficou com timestamp maior que o envio, que e exatamente o que se espera de dois eventos
causalmente ligados.

### 2. Se a Agencia 0 esta no evento de contador 10 e recebe uma mensagem com timestamp 3, qual o novo valor do contador? O que isso implica sobre agencias rapidas versus lentas?

O novo valor e **11**: `max(10, 3) + 1 = 11`. A mensagem "atrasada" nao puxa o relogio para tras;
ela so consome um tique, como qualquer outro evento.

A implicacao e que **os contadores das agencias nao sao comparaveis como medida de tempo ou de
volume de trabalho**. Uma agencia que processa muitos eventos sobe o contador rapidamente por conta
propria; uma agencia ociosa fica com contador baixo. Quando a lenta recebe uma mensagem da rapida,
ela da um salto e se alinha (`max`); quando acontece o contrario, a rapida praticamente ignora o
valor recebido.

Ou seja, o relogio logico so sincroniza na direcao "para cima", e apenas quando ha troca de
mensagem. Duas agencias que nunca conversam podem ficar arbitrariamente distantes em contador sem
que isso signifique nada sobre a ordem real dos seus eventos. Foi o que aconteceu nos nossos testes:
a Agencia 0 chegou ao contador 21 enquanto a Agencia 2 estava em 8, simplesmente porque recebeu mais
operacoes - nao porque seus eventos sejam "mais recentes".

---

## Parte D - Transferencias (secao 8.3)

### 1. Por que a transferencia local nao precisa de `ao_enviar()` / `ao_receber()`, enquanto a transferencia entre agencias precisa?

Porque as regras 2 e 3 de Lamport existem para sincronizar **processos diferentes**, e na
transferencia local nao ha dois processos: o debito e o credito acontecem na memoria da mesma
agencia, no mesmo processo, sem nenhuma mensagem trocada.

O relogio logico serve para estabelecer ordem causal entre eventos que, de outra forma, nao teriam
como ser comparados - eventos em maquinas distintas, sem relogio fisico comum. Dentro de um unico
processo esse problema nao existe: os eventos ja sao naturalmente sequenciais, e dois
`evento_local()` consecutivos (regra 1) bastam para registrar que o debito veio antes do credito.

Na transferencia entre agencias, sim: a Agencia de origem faz `ao_enviar()` e anexa o valor no corpo
da requisicao; a Agencia de destino faz `ao_receber(timestamp)` e ajusta seu proprio contador. Sem
isso, os relogios das duas agencias evoluiriam de forma completamente independente e a linha do
tempo unificada nao teria como colocar o credito depois do debito.

### 2. Reproduza a falha conhecida e observe o saldo da conta de origem depois do erro. Ele foi revertido?

**Nao foi revertido.** Com a Agencia 1 derrubada, a conta 0 tinha saldo 50,00. Apos a tentativa de
transferir 25,00 para a conta 1, a API respondeu HTTP 502 e o saldo da conta 0 ficou em **25,00** -
o dinheiro saiu da origem e nunca chegou ao destino. A Agencia 0 registrou a inconsistencia:

```json
{"agencia": "agencia-0", "tipo": "TRANSFERENCIA_FALHOU", "timestampLamport": 15,
 "detalhes": {"idOrigem": 0, "idDestino": 1, "valor": 25.0, "agenciaDestino": 1,
 "erro": "ConnectError: All connection attempts failed",
 "inconsistencia": "debito aplicado sem credito correspondente"}}
```

Em termos de consistencia, o sistema violou a **atomicidade**: a transferencia e conceitualmente uma
operacao unica ("debita aqui E credita la"), mas foi executada como duas operacoes independentes, e
a segunda falhou depois que a primeira ja tinha efeito. O sistema ficou em um estado que nenhuma
sequencia valida de operacoes bancarias poderia produzir - a soma dos saldos das 3 agencias diminuiu
sem que ninguem sacasse.

Vale notar o que o sistema **acertou**: ele nao escondeu o problema. Devolveu 502 em vez de fingir
sucesso, informou o valor em transito na resposta, e deixou o rastro no log. Um operador humano
consegue detectar e corrigir manualmente. O que falta e a correcao ser automatica.

### 3. Duas formas possiveis de corrigir isso no Sprint 4

**Two-Phase Commit (2PC).** Um coordenador conduz a operacao em duas fases. Na fase de preparacao,
ele pergunta as duas agencias se elas conseguem executar sua parte e as duas reservam os recursos
(a origem bloqueia o valor sem debitar de fato) e respondem "pronto". So se todas responderem
positivamente o coordenador emite o commit na fase 2. Se qualquer uma falhar ou nao responder, ele
emite abort e ninguem aplica nada. A vantagem e a atomicidade forte; o custo e que os recursos ficam
bloqueados durante o protocolo e a queda do coordenador entre as fases trava os participantes.

**Saga com transacao compensatoria.** Cada etapa e aplicada e confirmada localmente na hora, mas
toda etapa tem uma etapa inversa registrada. Se o credito no destino falhar, a Saga dispara
automaticamente a compensacao "estornar debito na origem", que devolve o valor. Nao ha bloqueio e o
sistema escala melhor, mas a consistencia e eventual: existe uma janela real em que o dinheiro esta
faltando, e a compensacao precisa ser idempotente e sobreviver a reinicializacoes - o que se
encaixa bem com a chave de idempotencia ja implementada neste sprint.

---

## Parte E - Linha do tempo unificada (secao 10.3)

### Observacao do passo 3 da tarefa

Rodando `mesclar_logs.py` apos gerar operacoes simultaneas nas 3 agencias, apareceram varios
empates. Dois casos ilustram bem a diferenca:

**Caso A - eventos genuinamente concorrentes.** No Lamport 4:

```
[Lamport 4] (21:03:55.096) agencia-0 - SAQUE     {"id": 0, "valor": 15.0}
[Lamport 4] (21:07:33.537) agencia-2 - DEPOSITO  {"id": 2, "valor": 5.0}
[Lamport 4] (21:07:33.552) agencia-1 - DEPOSITO  {"id": 1, "valor": 5.0}
```

Sao tres eventos **concorrentes**: nenhum influenciou o outro. Cada agencia chegou ao contador 4
contando os proprios eventos, sem nunca ter trocado mensagem com as outras ate ali. O empate nao
significa simultaneidade - significa ausencia de relacao causal. E a hora de parede confirma que
nao houve simultaneidade nenhuma: o saque da Agencia 0 aconteceu quase 4 minutos antes dos outros
dois.

**Caso B - empate entre eventos de historias diferentes.** No Lamport 9:

```
[Lamport 9] (21:04:14.075) agencia-1 - TRANSFERENCIA_CREDITO_REMOTO {"timestampRecebido": 8}
[Lamport 9] (21:04:14.098) agencia-0 - TRANSFERENCIA_DEBITO {"idOrigem": 0, "idDestino": 1}
```

Aqui o credito remoto da Agencia 1 tem relacao causal com o *envio* da Agencia 0 (timestamp 8), mas
**nao** com o debito da Agencia 0 que empatou com ele - esse debito e de uma transferencia
posterior, disparada depois. Os dois eventos de Lamport 9 sao concorrentes entre si, apesar de um
deles pertencer a uma cadeia causal que passa pela outra agencia.

**A ordem por hora de parede bate com a ordem por Lamport?** Nao, e nem deveria. Nos empates do
Lamport 4, 5 e 6, a ordem por hora fisica coloca a Agencia 0 primeiro (21:03/21:04) e as demais
minutos depois (21:07), enquanto o Lamport nao os ordena de forma alguma. E no Lamport 1 ha eventos
separados por quase 4 minutos de relogio fisico. Isso reforca o ponto do algoritmo: o relogio logico
nao esta medindo tempo, esta medindo **dependencia causal**. A hora de parede so foi guardada para
essa comparacao - nenhuma decisao do sistema depende dela.

### 1. Lamport garante ida mas nao a volta. O que isso significa ao ver dois eventos com timestamps diferentes?

Significa que `ts(A) < ts(B)` **nao prova** que A influenciou B. A garantia so vale em uma direcao:
se A aconteceu-antes de B causalmente, entao com certeza `ts(A) < ts(B)`. Lendo a linha do tempo de
tras para frente, a inferencia nao se sustenta.

Concretamente: ver `TRANSFERENCIA_DEBITO` no Lamport 7 e `DEPOSITO` no Lamport 16 nao autoriza dizer
que o debito influenciou o deposito. Pode ser que sim, pode ser que sejam completamente
independentes e a diferenca venha so de quantos eventos locais cada agencia processou pelo caminho.
O que a ordem por Lamport permite afirmar com seguranca e o **contrapositivo**: se `ts(A) >= ts(B)`,
entao A definitivamente *nao* causou B.

Na pratica, a linha do tempo unificada e uma ordem total valida (nunca contradiz a causalidade), mas
que inventa ordem onde nao havia nenhuma.

### 2. Lamport sozinho distingue "concorrentes" de "A antes de B"? Por que isso motiva o relogio vetorial?

Nao distingue. Olhando so os inteiros do log, e impossivel dizer se os dois eventos do Lamport 9
sao concorrentes ou se um causou o outro - a informacao simplesmente nao esta la. Um unico contador
colapsa toda a historia do sistema em um numero, e nesse achatamento a informacao de *quais*
processos contribuiram para aquele estado se perde.

O relogio vetorial resolve isso guardando um contador **por processo**: cada agencia carrega
`[c0, c1, c2]`, o que ela sabe do progresso de cada uma das tres. A comparacao passa a ser
componente a componente: A aconteceu-antes de B se todo componente de A e menor ou igual ao de B e
pelo menos um e estritamente menor; se nenhum dos dois domina o outro, eles sao **provadamente
concorrentes**. Isso da a volta que falta no relogio de Lamport, e e por isso que ele e o tema do
Sprint 2 - onde a comunicacao passa a ser indireta (pub/sub) e saber quem viu o que fica ainda mais
critico.

---

## Parte F - Autenticacao JWT (secao 11.3)

### 1. Autenticacao vs autorizacao. Sua implementacao verifica so uma, ou as duas?

**Autenticacao** responde "quem e voce" - validar credenciais e confirmar identidade.
**Autorizacao** responde "voce pode fazer isso" - decidir se a identidade ja confirmada tem
permissao para a operacao pedida.

Esta implementacao faz **as duas**, e foi por isso que escolhi o modelo de credencial "usuario dono
de contas" em vez de um operador generico:

- **Autenticacao:** `POST /auth/login` valida usuario e senha e emite um JWT assinado. A dependencia
  `usuario_autenticado` rejeita com 401 qualquer requisicao sem token, com token invalido ou expirado.
- **Autorizacao:** o token carrega a claim `contas` com os ids que aquele usuario possui, e a funcao
  `exigir_dono_da_conta` compara essa lista com a conta que a requisicao quer operar. Se nao bater,
  responde **403 Forbidden** - status diferente do 401 de proposito, porque o problema nao e a
  identidade, e a permissao.

**Um usuario autenticado consegue sacar de uma conta que nao e dele?** Nao. Testado:

```
$ curl -s http://localhost:4001/contas/1 -H "Authorization: Bearer $TOKEN_ANA"
{"detail":{"erro":"Usuario 'ana' nao e dono da conta 1."}}   [HTTP 403]
```

A verificacao cobre consulta, deposito, saque, criacao de conta e a origem da transferencia. A
**conta de destino** de uma transferencia deliberadamente nao exige propriedade - transferir para
terceiros e justamente o caso de uso normal de um banco.

### 2. Por que o servidor nao precisa consultar um banco para validar a assinatura? O que isso implica sobre escalabilidade?

Porque o JWT e **auto-contido e assinado**. O token carrega os proprios dados (usuario, contas,
expiracao) e um HMAC-SHA256 calculado sobre eles com a chave secreta. Para validar, a agencia
recalcula o HMAC com a mesma chave e compara: se bater, o conteudo nao foi adulterado e veio de quem
tem a chave. A verificacao e puramente local e criptografica - nao ha nada para consultar.

Sessao em memoria no servidor funciona de forma oposta: o cliente manda um id opaco e o servidor
precisa procurar o que aquele id significa. Isso cria **estado compartilhado**, e estado compartilhado
e o inimigo da escalabilidade horizontal. Com sessoes, ou todas as instancias consultam um repositorio
central (que vira gargalo e ponto unico de falha), ou o balanceador precisa amarrar cada usuario
sempre a mesma instancia (sticky sessions, que atrapalha failover e rebalanceamento).

No ICEIBank isso e visivel: as 3 agencias compartilham a chave secreta, entao **um token emitido
pela Agencia 0 e aceito pelas Agencias 1 e 2** sem que elas troquem uma unica mensagem entre si -
o que e essencial, porque o frontend pode usar qualquer agencia como porta de entrada.

O preco e a revogacao. Como nao ha consulta, nao ha onde marcar "este token nao vale mais": um token
roubado continua valido ate expirar. E por isso que a expiracao e curta (15 minutos).

### 3. O que aconteceria se a chave secreta vazasse?

Seria comprometimento total da autenticacao. Com HS256 a mesma chave assina e verifica, entao quem
tem a chave **forja qualquer token**: bastaria montar um payload com `"sub": "ana"` e
`"contas": [0,1,2,3,4,5]`, assinar, e operar todas as contas do banco. As 3 agencias aceitariam,
porque a assinatura seria matematicamente valida - do ponto de vista delas, nada distingue um token
forjado de um legitimo.

E pior neste sistema por dois motivos. Primeiro, a chave e compartilhada pelas 3 agencias: vazar em
uma compromete as tres. Segundo, o atacante tambem forjaria **tokens de servico** (`tipo: servico`),
chamando `creditar-remoto` diretamente e creditando qualquer conta com qualquer valor, se passando
por outra agencia.

Como a validacao nao consulta estado, nao ha lista de revogacao para conter o estrago: a unica
resposta e trocar a chave, o que invalida de uma vez todos os tokens em circulacao e forca todo
mundo a logar de novo. Por isso a chave e lida de variavel de ambiente (`JWT_SEGREDO`) e nao fica
fixa no codigo - em producao ela viria de um cofre de segredos, com rotacao periodica. Uma alternativa
estrutural seria assinatura assimetrica (RS256): as agencias so precisariam da chave publica para
verificar, e a chave privada de assinatura ficaria em um unico servico de autenticacao, reduzindo
bastante a superficie de exposicao.

---

## Parte G - Frontend (secao 12.3)

### 1. Como o frontend "lembra" de reenviar o token em cada requisicao?

O token e guardado no `localStorage` logo apos o login e reanexado automaticamente por um ponto
unico de saida de rede.

O mecanismo tem duas pecas, ambas na camada Model:

1. **`model/sessao.ts`** e o unico modulo do app que toca no `localStorage` (leitura e escrita
   envolvidas em `try/catch`, porque navegador em modo privado pode bloquear o acesso).
2. **`model/api.ts`** expoe uma funcao interna `requisicao()` pela qual **toda** chamada a API passa.
   Antes de disparar o `fetch`, ela le o token da sessao e injeta o cabecalho
   `Authorization: Bearer <token>`.

Nenhum componente de tela monta cabecalho por conta propria. Isso significa que nao existe a
possibilidade de um botao novo "esquecer" de mandar o token: quem quiser falar com a API
obrigatoriamente passa por esse funil. E o mesmo motivo pelo qual o tratamento de erro tambem e
uniforme - a traducao do corpo de erro da API em mensagem exibivel acontece no mesmo lugar.

### 2. Se o token expirar no meio de uma operacao, o que acontece?

A pessoa e avisada explicitamente; nao ve um erro generico.

O fluxo e: a agencia responde 401 com `{"erro": "Token expirado. Faca login novamente."}`; a
`requisicao()` detecta o 401 e marca o erro com a flag `expirado`; o controller `useSessao.tratarFalha`
limpa a sessao e devolve a pessoa para a tela de login com a mensagem:

> *"Sua sessao expirou durante a operacao. Faca login novamente - a operacao NAO foi concluida."*

A segunda frase e deliberada. Em um app bancario, a duvida imediata de quem foi interrompido no meio
de uma transferencia e "o dinheiro saiu ou nao?". Como o 401 e barrado pela dependencia de
autenticacao **antes** de o controller tocar em qualquer saldo, nada foi aplicado - e a interface
diz isso, em vez de deixar a pessoa no escuro.

Distingo tambem "token expirado" de "token invalido/ausente", que produz uma mensagem diferente
("Sua sessao nao e mais valida"). O caso de rede indisponivel tem seu proprio texto, indicando qual
agencia nao respondeu.

### 3. Onde ficam o "M", o "V" e o "C" no seu frontend?

Existem de forma clara - a separacao e o proprio layout de pastas, escolhida justamente para
espelhar o MVC do backend:

| Camada | Pasta | Conteudo | Responsabilidade |
|--------|-------|----------|------------------|
| **Model** | `src/model/` | `tipos.ts`, `api.ts`, `sessao.ts` | Formato dos dados, comunicacao com as agencias, persistencia do token. Nao conhece React. |
| **View** | `src/view/` | `LoginView.tsx`, `PainelView.tsx` | Renderizacao e captura de input. Recebe tudo por props e nao chama a API diretamente. |
| **Controller** | `src/controller/` | `useSessao.ts`, `useBanco.ts` | Traduz acao da interface em chamada do Model, e resultado do Model em estado de tela. |

O `App.tsx` faz a amarracao: decide qual View mostrar conforme o estado da sessao e injeta nela as
acoes vindas dos Controllers.

**Sendo honesto sobre onde a separacao nao e perfeita:** as Views guardam o estado dos proprios
campos de formulario com `useState` local (o texto digitado no campo "valor", por exemplo). Em um
MVC de livro, isso seria estado de Model. Deixei assim porque e input transitorio, que so vira dado
de dominio no momento em que o botao e clicado - centralizar cada tecla no controller adicionaria
indirecao sem beneficio real. A fronteira que importa foi mantida: **nenhuma View chama `fetch`, e
nenhum modulo do Model importa React**.

Vale registrar que o MVC do React nao e o MVC classico do backend: nao ha um Controller recebendo a
requisicao e escolhendo a View. O que existe e uma separacao analoga de responsabilidades, com hooks
no papel de Controller.

---

## Funcionalidade adicional (secao 2.1)

**Funcionalidade escolhida:** idempotencia de transferencias via cabecalho `Idempotency-Key`.

### O que ela faz

O cliente pode enviar um cabecalho `Idempotency-Key` junto com `POST /transferencias`. A agencia
guarda o resultado da operacao associado aquela chave. Se a **mesma chave** chegar de novo:

- a transferencia **nao** e reexecutada - nenhum debito adicional acontece;
- a resposta original e devolvida, marcada com `"repetida": true`;
- um evento `TRANSFERENCIA_REPETIDA_IGNORADA` e gravado no log, com o timestamp de Lamport, para que
  a repeticao fique visivel na linha do tempo em vez de silenciosa.

Ha ainda o tratamento de duas chamadas simultaneas com a mesma chave: enquanto a primeira esta em
andamento a chave fica marcada, e a segunda recebe **409 Conflict** em vez de duplicar a operacao.
E se a transferencia falhar, a chave e liberada - retentar depois de um erro precisa continuar
funcionando, senao a idempotencia viraria um bloqueio permanente.

Evidencia do comportamento (a mesma transferencia de R$ 10,00 enviada 3 vezes):

```
envio 1: {"mensagem":"Transferencia concluida (entre agencias).","saldoOrigem":50.0,"timestampLamport":10}
envio 2: {"mensagem":"Transferencia concluida (entre agencias).","saldoOrigem":50.0,"repetida":true}
envio 3: {"mensagem":"Transferencia concluida (entre agencias).","saldoOrigem":50.0,"repetida":true}

saldo da origem: 60.0 -> 50.0   (debitou 10, nao 30)
saldo do destino: 40.0 -> 50.0  (creditou 10, nao 30)
```

### Por que escolhi implementa-la

Porque ela ataca um problema que **este sprint cria e nao resolve**, e prepara o terreno para o
Sprint 4.

A Parte D termina com uma inconsistencia conhecida: quando a chamada entre agencias falha, o cliente
recebe 502 sem saber se o credito foi aplicado ou nao. A reacao natural de qualquer cliente diante
de um erro de rede e **tentar de novo** - e sem idempotencia, se a falha tiver ocorrido *depois* de a
agencia de destino processar o credito (por exemplo, um timeout na resposta de volta), essa
retentativa aplicaria a transferencia uma segunda vez. O erro de rede vira dinheiro duplicado.

Alem disso, a chave de idempotencia e pre-requisito pratico das duas solucoes do Sprint 4: tanto o
commit de um 2PC quanto a compensacao de uma Saga precisam ser reexecutaveis com seguranca, porque
podem ser reenviados apos falha do coordenador. Implementar isso agora significa que o Sprint 4 vai
construir sobre uma base que ja tolera reentrega, em vez de ter que voltar e adicionar.

Escolhi essa em vez de um health-check ou de um limite de saque porque as outras seriam validacoes
locais, sem relacao com os problemas de sistemas distribuidos que a disciplina esta tratando.

### Evidencia

`evidencias/sprint1/funcionalidade-adicional.png`

---

## Decisoes de design

### Modelo de credenciais adotado na autenticacao (Parte F, requisito 1)

**Decisao:** login por **usuario e senha**, onde cada usuario e dono de um conjunto de contas, e o
token carrega esse conjunto na claim `contas`.

```json
{"sub": "ana", "tipo": "usuario", "contas": [0, 3], "iat": ..., "exp": ...}
```

**Justificativa.** Considerei tres modelos:

1. **Operador unico do banco** - um login generico que libera tudo. Rejeitado: sem nocao de dono, o
   sistema so teria autenticacao, e qualquer pessoa logada poderia sacar de qualquer conta. Seria o
   minimo para cumprir o requisito, mas nao permitiria implementar autorizacao de verdade.
2. **Id da conta + senha** - cada conta e uma credencial. Rejeitado: uma pessoa com contas em
   agencias diferentes precisaria de um login por conta, e a transferencia ficaria estranha (o token
   valeria para uma conta so).
3. **Usuario dono de contas** (escolhido) - modela o banco como ele funciona de fato: uma pessoa,
   varias contas, possivelmente em agencias diferentes.

O modelo escolhido tambem exercita melhor o proprio conceito de particao: a usuaria `ana` e dona das
contas 0 e 3, ambas na Agencia 0, enquanto seus pares tem contas em outras agencias - e a claim
`contas` viaja no token, entao **qualquer** agencia consegue decidir sobre autorizacao sem consultar
nenhuma base central. Isso e coerente com o argumento de escalabilidade da questao 11.3.2.

As senhas nao sao guardadas em texto puro: `config.py` armazena SHA-256. Em producao usaria bcrypt
ou Argon2 (com salt e custo configuravel); SHA-256 puro foi suficiente aqui porque o foco do sprint
e o mecanismo de token, nao o armazenamento de credenciais.

**Expiracao: 15 minutos.** Curta o bastante para limitar a janela de uso de um token vazado (nao ha
revogacao possivel, conforme discutido em 11.3.2), e longa o bastante para uma sessao de uso normal.
Configuravel por `EXPIRACAO_TOKEN_MINUTOS`. Para gerar a evidencia do cenario de token expirado sem
esperar 15 minutos, ha o script `gerar_token_expirado.py`, que emite um token ja vencido usando a
mesma chave - preferi um script separado a colocar um atalho de teste dentro da API.

### Tratamento da chamada interna entre agencias (Parte F, requisito 5)

**Decisao:** a rota `creditar-remoto` **e protegida**, mas por uma credencial de tipo diferente. A
agencia de origem emite um **token de servico** de vida curta (30 segundos) e o envia no
`Authorization`. A rota so aceita tokens com `"tipo": "servico"`, e rejeita tokens de usuario com 401.

**Justificativa.** Havia tres caminhos:

1. **Deixar a rota aberta**, tratando a rede interna como confiavel. Rejeitado: seria um endpoint sem
   autenticacao capaz de creditar qualquer conta com qualquer valor. "Esta na rede interna" nao e
   controle de acesso - e exatamente o tipo de suposicao que a arquitetura de confianca zero abandonou.
   Alem disso, contradiz o requisito 3 da Parte F, que manda proteger tudo que modifica contas.
2. **Repassar o token do usuario** que iniciou a transferencia. Rejeitado por dois motivos. Semantico:
   quem chama `creditar-remoto` **nao e** a usuaria Ana, e a Agencia 0 - e o destinatario do credito
   normalmente nem pertence a ela, entao a claim `contas` do token dela nao autoriza nada util ali.
   Pratico: amarraria uma operacao interna do sistema ao ciclo de vida da sessao de uma pessoa, e
   propagaria credencial de usuario entre servicos, ampliando o estrago de um vazamento.
3. **Token de servico proprio** (escolhido). Cada agencia se identifica como `agencia-N`, com
   `"tipo": "servico"`. A distincao de tipo importa: impede tanto que um usuario chame a rota interna
   diretamente quanto que um token de servico seja usado para operar contas pela API publica. A
   validade de 30 segundos cobre a duracao de uma unica chamada - se vazar, e praticamente inutil.

O log registra qual agencia fez a chamada (campo `chamadaPor`), o que deixa rastro de autoria na
linha do tempo:

```json
{"tipo": "TRANSFERENCIA_CREDITO_REMOTO", "timestampLamport": 9,
 "detalhes": {"idConta": 1, "valor": 30.0, "origemAgencia": 0,
 "timestampRecebido": 8, "chamadaPor": "agencia-0"}}
```

**Limitacao assumida:** como a chave secreta e compartilhada pelas 3 agencias, qualquer uma delas
pode emitir um token se passando por outra. Para este sprint e aceitavel - as 3 agencias sao o mesmo
codigo, sob o mesmo controle. Um sistema real usaria uma chave por agencia com assinatura assimetrica,
de forma que a Agencia 1 pudesse verificar a assinatura da Agencia 0 sem ser capaz de produzi-la.

### Escolha do framework de frontend (Parte G)

**Decisao:** Vite + React + TypeScript.

**Justificativa.** O requisito de plataforma era apenas "web". Escolhi React por familiaridade e
Vite por ser o build mais leve para uma aplicacao de tela unica, sem o peso de SSR ou roteamento de
servidor que nao teriam uso aqui. TypeScript entrou porque a unidade trata de arquitetura em
camadas, e tipos explicitos (`Conta`, `RespostaLogin`, `ResultadoTransferencia`) tornam a fronteira
entre Model e View verificavel pelo compilador em vez de ser so convencao de pasta.

Considerei HTML/CSS/JS puro, que teria zero dependencias, mas o tratamento de erro exigido pelo
requisito 5 e a troca de agencia do requisito 6 pedem estado de interface que ficaria verboso de
manter na mao.

O frontend nao sabe distinguir transferencia local de transferencia entre agencias - envia o pedido
para a agencia de origem e exibe o que o backend responde, o que respeita o requisito 4. Ele calcula
`id % 3` apenas para **orientar** quem usa a tela sobre qual agencia e dona de cada conta; a decisao
real continua sendo do backend.
