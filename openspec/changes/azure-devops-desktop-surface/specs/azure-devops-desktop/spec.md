# Spec Delta

## Purpose

Especificar a surface do plugin Azure DevOps dentro do app Hermes Desktop: o
que o painel mostra (a atividade do usuário autenticado), como ele é
servido (rotas REST sobre o mesmo cliente do agente), como se mantém atualizado
(cache, evento, polling) e como degrada de forma acionável quando o backend
não está montado.

## ADDED Requirements

### Requirement: O painel mostra a atividade do usuário autenticado
O plugin SHALL expor uma página `/azure-devops` que mostra, do usuário
autenticado pelo PAT: pull requests em que ele é autor ou reviewer, work items
atribuídos a ele e as últimas builds por ele disparadas. O painel SHALL
funcionar sem `default_project` configurado, por não depender de projeto
padrão.

#### Scenario: Painel carregado com PAT válido
- **WHEN** o usuário abre a página `/azure-devops`
- **THEN** ela lista os pull requests em que o dono do PAT participa, os work
  items atribuídos a ele e as builds recentes disparadas por ele

#### Scenario: Projeto padrão não configurado
- **WHEN** `default_project` está vazio
- **THEN** o painel continua funcionando, porque o recorte é por identidade e
  não por projeto

### Requirement: O painel é estritamente de leitura
Todas as rotas do painel SHALL ser de leitura (`GET`); o backend SHALL NOT
expor mutação de pull request, work item, wiki ou build. A escrita continua
sendo feita pelas tools do agente.

#### Scenario: Tentativa de mutação
- **WHEN** uma requisição `POST` é feita a uma rota do painel
- **THEN** a resposta é `405` e nenhum objeto é alterado

### Requirement: O painel é servido pelo mesmo cliente do agente
O backend do painel SHALL reutilizar o cliente HTTP e a resolução de credencial
do plugin (mesmo PAT, mesma configuração, mesma taxonomia de erro), sem
armazenar credencial ou configuração em outro lugar.

#### Scenario: Mesmo PAT nos dois lados
- **WHEN** o agente e o painel são usados na mesma sessão
- **THEN** ambos Talk to Azure DevOps with the same credential, and neither one
  reads a separate copy

#### Scenario: Erro do painel tem o mesmo código do agente
- **WHEN** a API responde 403 para uma chamada do painel
- **THEN** o painel devolve o código `forbidden` com a mesma mensagem que a
  tool correspondente devolveria

### Requirement: O polling é limitado por cache
O backend SHALL manter cache em memória de ~15 segundos por escopo consultado,
de modo que requisições repetidas dentro da janela não gerem chamadas
adicionais à API do Azure DevOps.

#### Scenario: Duas leituras dentro da janela
- **WHEN** o painel é consultado duas vezes em menos de 15 segundos
- **THEN** a segunda devolve o mesmo payload e nenhuma requisição extra é feita
  à API do Azure DevOps

#### Scenario: Cache expira
- **WHEN** a consulta ocorre depois da janela de cache
- **THEN** o backend consulta a API novamente

### Requirement: Escritas do agente invalidam o painel
Quando uma tool de escrita do agente conclui com sucesso, o plugin SHALL
emitir um evento de invalidação para o app, e a UI SHALL re-buscar o estado
canônico por REST ao recebê-lo. A entrega do evento é fire-and-forget: a UI
SHALL reconciliar por polling mesmo sem evento.

#### Scenario: Agente cria um pull request
- **WHEN** a tool de criação de pull request tem sucesso
- **THEN** um evento de invalidação é emitido e o painel aberto passa a listar
  o pull request novo

#### Scenario: Evento perdido
- **WHEN** o evento não chega na janela do Desktop
- **THEN** o painel se corrige no próximo polling, sem estado local divergente

### Requirement: Entradas de navegação no app
O plugin SHALL registrar uma linha na sidebar do app (róta `/azure-devops`,
com `codicon` e `label`) e um chip no status bar com a contagem da atividade
do usuário, navigando para a página quando clicado.

#### Scenario: Linha da sidebar
- **WHEN** o app é aberto
- **THEN** a sidebar mostra a entrada do plugin e ela leva para
  `/azure-devops`

#### Scenario: Chip do status bar
- **WHEN** há pull requests ou builds do usuário
- **THEN** o status bar mostra a contagem e o clique abre a página

### Requirement: A ausência do backend é explicada, não silenciosa
Quando o backend do plugin não estiver montado (plugin ausente de
`plugins.enabled`), a página SHALL exibir uma mensagem acionável explicando
que o plugin precisa estar habilitado, em vez de uma tela vazia.

#### Scenario: Backend não montado
- **WHEN** a página é aberta e a rota do painel responde 404
- **THEN** a página informa que o plugin precisa estar habilitado em
  `plugins.enabled` e aponta a documentação

### Requirement: A identidade do usuário é resolvida com aviso
Quando o PAT não tiver o escopo de leitura de identidade, o painel SHALL
degradar de forma explícita: exibir a parte da atividade que não depende da
identidade e sinalizar que a parte que depende dela exige o escopo
correspondente.

#### Scenario: PAT sem escopo de identidade
- **WHEN** a resolução da identidade autenticada é recusada pela API
- **THEN** o painel mostra o que consegue e sinaliza que o escopo de identidade
  é necessário para a visão completa
