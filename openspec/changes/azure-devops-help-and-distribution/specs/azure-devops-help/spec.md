# Spec Delta

## Purpose

Especificar a ajuda operacional do plugin Azure DevOps: o que o comando
`/ado-help`, o subcomando `hermes azure-devops help` e a skill embarcada
informam ao usuário — escopo de PAT por operação, paginação, códigos de erro e
armadilhas — de forma acessível sem sair da conversa ou do terminal.

## ADDED Requirements

### Requirement: O comando /ado-help responde dentro da conversa
O plugin SHALL registrar o slash command `/ado-help` (e `azure-devops help`
como alias) que devolve, em texto, o guia de uso: escopo de PAT exigido por
cada família de operação, como usar a paginação, o catálogo de códigos de erro
e as armadilhas conhecidas.

#### Scenario: Usuário pede a ajuda
- **WHEN** o usuário digita `/ado-help` na conversa
- **THEN** a resposta contém as quatro seções do guia

#### Scenario: Ajuda com argumento é aceito
- **WHEN** o usuário digita `/ado-help pull requests`
- **THEN** a resposta destaca a seção de pull requests, mantendo o resto do guia

### Requirement: O subcomando CLI devolve o mesmo conteúdo
O plugin SHALL registrar o subcomando `hermes azure-devops help`, que
imprime o mesmo guia no terminal.

#### Scenario: Ajuda pelo terminal
- **WHEN** o usuário roda `hermes azure-devops help`
- **THEN** o conteúdo impresso é equivalente ao do `/ado-help`

### Requirement: A ajuda informa o escopo de PAT por operação
O guia SHALL listar, por família de operação (projetos/repos, builds, pull
requests, work items, wiki, releases, artefatos, identidades, políticas), o
escopo de PAT necessário e o sintoma quando o escopo falta.

#### Scenario: Escopo ausente é explicado
- **WHEN** o usuário lê a seção de work items
- **THEN** ela diz qual escopo habilitar e que a ausência produz erro 403

### Requirement: A ajuda explica paginação e erros
O guia SHALL explicar que listagens devolvem `continuationToken` e que o
token precisa ser reenviado, e SHALL listar os códigos de erro
(`not_configured`, `missing_credential`, `invalid_input`,
`unauthorized`, `forbidden`, `not_found`, `rate_limited`, `timeout`,
`upstream_error`) com o significado de cada um.

#### Scenario: Códigos de erro documentados
- **WHEN** o usuário procura um erro no guia
- **THEN** encontra o código com a causa provável e o que fazer

### Requirement: A ajuda é acessível como skill
O plugin SHALL embarcar a skill `azure-devops-usage` com o mesmo conteúdo
essencial, carregada sob demanda, sem aparecer no índice global de skills.

#### Scenario: Skill disponível
- **WHEN** o agente precisa do uso correto de uma tool e carrega a skill do
  plugin
- **THEN** a skill descreve escopos, paginação e armadilhas
