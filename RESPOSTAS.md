# ICEIBank - Sprint 1: Respostas e decisoes de design

Disciplina de Sistemas Distribuidos - PUC Minas
Backend em Python + FastAPI | Frontend em Vite + React + TypeScript

---

## Parte B - Relogio de Lamport e registro de eventos (secao 6.4)

### 1. Por que o relogio de Lamport usa `max(contador_local, timestampRecebido) + 1` ao receber uma mensagem, em vez de simplesmente adotar o timestamp recebido diretamente?

_(a responder)_

### 2. Se a Agencia 0 esta no evento de contador 10 e recebe uma mensagem com timestamp 3 (de uma agencia mais "atrasada"), qual o novo valor do contador da Agencia 0? O que isso implica sobre agencias que processam muitos eventos rapidamente versus agencias mais lentas?

_(a responder)_

---

## Parte D - Transferencias (secao 8.3)

### 1. No trecho `agenciaDestino === idAgencia`, por que a transferencia local nao precisa da logica de `aoEnviar()` / `aoReceber()` do relogio de Lamport, enquanto a transferencia entre agencias precisa?

_(a responder)_

### 2. Reproduza a falha conhecida e observe o saldo da conta de origem depois do erro. Ele foi revertido? O que isso significa em termos de consistencia do sistema bancario?

_(a responder)_

### 3. Pensando a frente para o Sprint 4: cite, em alto nivel, duas formas possiveis de corrigir esse problema.

_(a responder)_

---

## Parte E - Linha do tempo unificada (secao 10.3)

### Observacao do passo 3 da tarefa (par de eventos com o mesmo timestamp de Lamport)

_(a responder: os eventos empatados eram causalmente relacionados ou concorrentes? A ordem por `horaParede` bate com a ordem por Lamport?)_

### 1. O relogio de Lamport garante que, se A aconteceu antes de B causalmente, entao `timestamp(A) < timestamp(B)`. Ele nao garante a volta. O que isso significa na pratica quando voce ve dois eventos com timestamps diferentes na linha do tempo, mas sem saber se um realmente influenciou o outro?

_(a responder)_

### 2. Baseado no que voce observou: o relogio de Lamport, sozinho, seria suficiente para um sistema que precisa distinguir com certeza "A e B sao concorrentes" de "A aconteceu antes de B"? Por que isso motiva o relogio vetorial do Sprint 2?

_(a responder)_

---

## Parte F - Autenticacao JWT (secao 11.3)

### 1. Qual a diferenca entre autenticacao e autorizacao? Sua implementacao verifica so uma das duas, ou as duas? Um usuario autenticado consegue sacar de uma conta que nao e dele?

_(a responder)_

### 2. Por que o servidor nao precisa consultar um banco de dados para validar a assinatura de um JWT a cada requisicao? O que isso implica sobre escalabilidade, comparado a guardar sessoes em memoria no servidor?

_(a responder)_

### 3. O que aconteceria com a seguranca do sistema se a chave secreta usada para assinar o JWT vazasse?

_(a responder)_

---

## Parte G - Frontend (secao 12.3)

### 1. Como o frontend "lembra" de reenviar o token em cada requisicao depois do login? Descreva, em alto nivel, o mecanismo implementado.

_(a responder)_

### 2. Se o token expirar enquanto alguem esta usando o frontend no meio de uma operacao, o que acontece? A interface avisa a pessoa usuaria, ou ela so ve um erro generico?

_(a responder)_

### 3. Esta unidade da disciplina trata de arquitetura MVC. No seu frontend, onde fica o "M" (Model), o "V" (View) e o "C" (Controller)? Eles existem de forma clara, ou o codigo ficou mais misturado do que o padrao sugere?

_(a responder)_

---

## Funcionalidade adicional (secao 2.1)

**Funcionalidade escolhida:** idempotencia de transferencias

### O que ela faz

_(a responder)_

### Por que escolhi implementa-la

_(a responder)_

### Evidencia

`evidencias/sprint1/funcionalidade-adicional.png`

---

## Decisoes de design

### Modelo de credenciais adotado na autenticacao (exigido pela Parte F, requisito 1)

_(a responder: qual formato de credencial foi escolhido, qual o tempo de expiracao do token e por que)_

### Tratamento da chamada interna entre agencias (exigido pela Parte F, requisito 5)

_(a responder: a chamada `creditar-remoto` de agencia para agencia carrega um token igual ao das chamadas vindas do frontend, ou e tratada de forma diferente? Justificativa.)_

### Escolha do framework de frontend (exigido pela Parte G)

_(a responder)_
