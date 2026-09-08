# Respostas — Roteiro de Laboratório de Redes

**Aluno:** Vitor Augusto Viana Azevedo — matrícula 892281 · Turma T1
**Ambiente:** macOS 26.5.2 · Apple M4 · Java 21.0.9 · Python 3.13 · OFFSET = 81

> As respostas abaixo referem-se ao comportamento observado ao executar os
> programas deste repositório. Os prints correspondentes estão em `evidencias/`.

---

## Parte A — TCP

### 1. O que acontece se você iniciar o cliente antes do servidor? Por que isso ocorre, considerando o funcionamento do TCP?

**O que observei:**

_(rodar o cliente sem o servidor no ar e colar aqui a mensagem de erro exata,
tanto em Java quanto em Python)_

**Explicação:**

_(escrever)_

---

### 2. O TCP garante que as mensagens cheguem na ordem em que foram enviadas. Qual mecanismo do protocolo é responsável por isso?

_(escrever)_

---

### 3. Na sua implementação, o que aconteceria se dois clientes tentassem se conectar ao mesmo tempo? O código atual suporta isso? Justifique observando o código do servidor.

**O que observei:**

_(abrir um segundo cliente enquanto o primeiro está conectado e descrever o que
acontece)_

**Justificativa no código:**

_(apontar a linha do servidor que explica o comportamento)_

---

## Parte B — UDP

### 1. No passo 2 da tarefa, o que aconteceu quando você enviou uma mensagem com o servidor desligado? Compare com o que aconteceria em TCP e explique a diferença observada, relacionando com o conceito de "sem conexão".

**O que observei em Java:**

_(descrever: travou? deu erro? seguiu normalmente?)_

**O que observei em Python:**

_(descrever)_

**Comparação com TCP e explicação:**

_(escrever)_

---

### 2. Cite dois exemplos de aplicações reais que usam UDP e explique, para cada uma, por que a confiabilidade do TCP não é essencial (ou até atrapalharia).

_(escrever)_

---

### 3. No código, o servidor UDP não mantém nenhum registro de "quem está conectado". Isso seria possível de implementar? O que mudaria na arquitetura da aplicação?

_(escrever)_

---

## Parte C — Multicast

> **Nota de ambiente:** _(descrever aqui qual `NetworkInterface` funcionou no
> macOS e o que precisou ser ajustado em relação ao código original do roteiro)_

### 1. Qual é a diferença fundamental entre enviar a mesma mensagem para 3 clientes usando unicast repetido 3 vezes e enviar uma única vez via multicast? Pense em termos de tráfego de rede.

_(escrever)_

---

### 2. O que é o TTL (time-to-live) configurado no socket multicast e por que ele é importante para controlar o alcance dos pacotes na rede?

_(escrever)_

---

### 3. Se um dos clientes ficar temporariamente offline e voltar depois, ele recebe os avisos que perdeu? Por quê? Relacione com a arquitetura de comunicação em grupo.

**O que observei:**

_(derrubar um cliente durante o envio dos 5 avisos, subir de novo e verificar se
ele recebe os que perdeu)_

**Explicação:**

_(escrever)_

---

## Parte D — WebSocket

### 1. O WebSocket começa com uma requisição HTTP contendo o cabeçalho `Upgrade: websocket`. O que exatamente "muda" na conexão depois que esse handshake é concluído?

_(escrever)_

---

### 2. Compare o mural via WebSocket (Parte D) com o aviso via Multicast (Parte C). Ambos entregam uma mensagem a vários destinatários — qual a diferença na forma como cada um descobre e alcança os destinatários?

_(escrever — dica: comparar o `getConnections()` do servidor Java da Parte D com
o `joinGroup()` do cliente da Parte C. Quem mantém a lista de destinatários em
cada caso?)_

---

### 3. Por que o WebSocket é mais adequado do que TCP "cru" (como o da Parte A) para este cenário de mural em tempo real, mesmo os dois sendo, no fundo, conexões TCP contínuas?

_(escrever)_

---

## Exercícios extras realizados

_(opcional — registrar aqui o teste cruzado da Parte C, Java↔Python, se funcionar)_
