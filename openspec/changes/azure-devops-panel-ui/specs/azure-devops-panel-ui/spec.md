# Spec Delta

## Purpose

Definir a experiência da página `/azure-devops`: abas por domínio com contadores,
presets de período, seletor de projetos ignorados, busca por texto, links que abrem o
item no Azure DevOps, datas relativas, badges de estado, refresh manual, notificação
nativa de build falho e estados vazios acionáveis.

## ADDED Requirements

### Requirement: Abas organizam as seções
A página SHALL apresentar quatro abas — **Pull Requests**, **Work Items**, **Builds**
e **Releases** — cada uma com contador no título, mostrando uma seção por vez.

#### Scenario: Alternar de aba
- **WHEN** o usuário clica na aba Builds
- **THEN** somente a lista de builds é exibida, com o contador no título da aba

#### Scenario: Aba Releases
- **WHEN** o usuário clica na aba Releases
- **THEN** as releases do usuário (das change de read-tools) são listadas com o mesmo
  padrão das demais abas

### Requirement: Presets de período com default 7 dias
A página SHALL oferecer presets de período **7 / 30 / 90 dias** com default **7**, e
refazer a busca do backend com o período escolhido (parâmetro `days`).

#### Scenario: Default ao abrir
- **WHEN** a página abre pela primeira vez
- **THEN** o preset de 7 dias está selecionado e os dados são do período

#### Scenario: Trocar para 90 dias
- **WHEN** o usuário seleciona o preset de 90 dias
- **THEN** a busca é refeita com `days=90` e o painel mostra itens do período

### Requirement: Projetos ignorados editáveis na UI
A página SHALL oferecer um seletor de projetos com checkbox que grava a lista de
projetos ignorados na setting `ignored_projects` do perfil, e SHALL refletir o estado
atual da setting ao abrir.

#### Scenario: Marcar projeto como ignorado
- **WHEN** o usuário desmarca um projeto no seletor
- **THEN** a setting `ignored_projects` é atualizada no perfil e o projeto sai da
  varredura do painel no próximo ciclo

#### Scenario: Configuração feita por fora é refletida
- **WHEN** a setting `ignored_projects` é editada fora da UI (`hermes config set`)
- **THEN** o seletor reflete o novo estado no próximo load

### Requirement: Links clicáveis para o Azure DevOps
Cada linha de PR, work item, build e release SHALL abrir o item no Azure DevOps no
navegador padrão quando clicada, usando `ctx.os.openExternal(url)` com a URL devolvida
pelo backend.

#### Scenario: Abrir um pull request
- **WHEN** o usuário clica em uma linha de pull request
- **THEN** o PR abre no navegador padrão

#### Scenario: Linha sem url não quebra
- **WHEN** um item não carrega url
- **THEN** a linha é exibida sem comportamento de clique e sem erro

### Requirement: Datas relativas
A página SHALL exibir a data de cada item como tempo relativo ("há 2 dias", "há 3
horas"), calculada dos ISO 8601 devolvidos pelo backend.

#### Scenario: Idade visível
- **WHEN** a página lista itens
- **THEN** cada linha mostra o tempo relativo correspondente à data ISO do item

### Requirement: Badges de estado
A página SHALL exibir badge visual com cor por estado (verde sucesso, vermelho falha,
amarelo em andamento, cinza rascunho/inativo) usando `var(--ui-*)`.

#### Scenario: Build falho tem badge vermelho
- **WHEN** a aba Builds lista um build com resultado `failed`
- **THEN** o badge do item é vermelho com o texto do resultado

#### Scenario: PR rascunho tem badge neutro
- **WHEN** a aba Pull Requests lista um PR em draft
- **THEN** o badge do item é cinza com o texto "draft"

### Requirement: Busca por texto na aba ativa
A página SHALL oferecer um campo de busca que filtra por título as linhas da aba ativa,
sem chamada ao backend.

#### Scenario: Busca filtra localmente
- **WHEN** o usuário digita "deploy" com a aba Builds ativa
- **THEN** somente builds cujo título/número contém "deploy" permanecem visíveis

### Requirement: Refresh manual com idade da atualização
A página SHALL oferecer botão de refresh que força a busca imediata (limpando o cache
do backend quando possível) e SHALL exibir "atualizado há Xs" desde o último dado,
atualizado a cada segundo.

#### Scenario: Refresh manual
- **WHEN** o usuário clica em refresh
- **THEN** a busca é refeita imediatamente e o "atualizado há" volta a 0s

#### Scenario: Polling continua como fallback
- **WHEN** o usuário não interage
- **THEN** o ciclo automático de 15s continua atualizando normalmente

### Requirement: Notificação nativa de build falho
Quando um build do usuário termina com resultado `failed` e o usuário está away, o
plugin SHALL emitir uma notificação nativa (`ctx.os.notify`) com o build number e o
título, com dedupe por build id (cada build notificado no máximo uma vez).

#### Scenario: Build falha enquanto o usuário está away
- **WHEN** um build do usuário termina `failed` e o usuário está away
- **THEN** uma notificação nativa com o build number é exibida uma única vez

#### Scenario: O mesmo build não notifica duas vezes
- **WHEN** o mesmo build falho aparece em dois ciclos seguidos
- **THEN** a notificação não é repetida

### Requirement: Estados vazios acionáveis
Quando uma aba não tem itens, a página SHALL exibir mensagem de estado vazio com ação
acionável ("abrir no Azure DevOps" via `ctx.os.openExternal`) quando a seção tem
destino natural.

#### Scenario: Aba vazia com ação
- **WHEN** a aba Pull Requests não tem itens
- **THEN** a página mostra "nenhum PR aberto" com botão que abre a página de PRs da
  organização no navegador
