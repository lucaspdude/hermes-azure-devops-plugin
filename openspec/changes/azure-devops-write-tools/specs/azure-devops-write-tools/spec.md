# Spec Delta

## Purpose

Especificar a superfície de **escrita** do Azure DevOps: quais tools existem,
o que cada uma altera, qual identidade é usada (o dono do PAT), o que é
devolvido e como falhas de autorização e de política da organização são
reportadas — sempre no envelope definido em `azure-devops-plugin-core`.

## ADDED Requirements

### Requirement: O agente cria pull requests
O plugin SHALL expor `azure_devops_create_pull_request` com
`sourceRefName`, `targetRefName`, `title`, `description` opcional,
`isDraft` opcional e `reviewerIds` opcional; SHALL devolver o id e a url do
PR criado.

#### Scenario: PR criado
- **WHEN** o modelo cria um PR de `feature/x` para `main`
- **THEN** a resposta traz o id e a url do PR criado

#### Scenario: Fonte ou destino inválido
- **WHEN** a branch de origem não existe
- **THEN** a resposta é `not_found` ou `forbidden` conforme o erro da API, sem
  stack trace

### Requirement: O agente comenta e rotula pull requests
O plugin SHALL expor `azure_devops_add_pull_request_comment` (com `comment`
e opcionalmente `threadId`/`status` para responder uma thread),
`azure_devops_list_pull_request_labels` já existente,
`azure_devops_add_pull_request_label` (por nome ou id) e
`azure_devops_remove_pull_request_label`.

#### Scenario: Comentário em thread existente
- **WHEN** o modelo responde uma threadinformando `threadId`
- **THEN** o comentário entra na thread indicada e a resposta traz o id do
  comentário

#### Scenario: Label adicionada
- **WHEN** o modelo adiciona a label `review-em-andamento`
- **THEN** a resposta confirma a label e seu id

### Requirement: O agente vota em pull requests com a própria identidade
O plugin SHALL expor `azure_devops_approve_pull_request` (voto 10),
`azure_devops_reject_pull_request` (voto 5) e
`azure_devops_reset_pull_request_vote` (voto 0); o voto SHALL ser aplicado
sempre no `reviewerId` do usuário autenticado (dono do PAT), resolvido no
momento da chamada.

#### Scenario: Voto aplicado
- **WHEN** o modelo aprova um PR
- **THEN** a resposta confirma o voto 10 no reviewer do usuário autenticado

#### Scenario: PAT de outra pessoa
- **WHEN** o PAT pertence a um usuário que não é reviewer do PR
- **THEN** a resposta é `forbidden`, com a mensagem de que o PAT não pode votar
  nesse PR

### Requirement: O agente conclui ou abandona pull requests
O plugin SHALL expor `azure_devops_complete_pull_request` (status
`completed`, com opção `deleteSourceBranch` e `squashMerge`) e
`azure_devops_abandon_pull_request` (status `abandoned`).

#### Scenario: PR concluído com squash
- **WHEN** o modelo conclui o PR com `squashMerge: true`
- **THEN** a resposta traz o PR com status `completed` e o commit de squash

#### Scenario: Política de branch bloqueia a conclusão
- **WHEN** a política da organização exige reviewers e o PR não tem
- **THEN** a resposta é `forbidden` com a mensagem original da API, sem contornar
  a política

### Requirement: O agente atualiza work items
O plugin SHALL expor `azure_devops_update_work_item` com o id do work item e
uma lista de operações JSON Patch (`op`, `path`, `value`), devolvendo o
work item atualizado.

#### Scenario: Campo alterado
- **WHEN** o modelo muda o estado de um work item
- **THEN** a resposta traz o work item com o novo valor

#### Scenario: Caminho inválido no patch
- **WHEN** o `path` do patch não existe no work item
- **THEN** a resposta é `invalid_input` ou `upstream_error` conforme a API,
  sem aplicar outras operações do lote

### Requirement: O agent edita páginas de wiki
O plugin SHALL expor `azure_devops_create_wiki_page` (wiki, caminho, conteúdo)
e `azure_devops_update_wiki_page` (wiki, caminho, conteúdo), devolvendo o
caminho e a versão da página resultante.

#### Scenario: Página criada
- **WHEN** o modelo cria a página `/Runbooks/Deploy`
- **THEN** a resposta traz o caminho e a versão da página criada

#### Scenario: Página inexistente no update
- **WHEN** o modelo atualiza uma página que não existe
- **THEN** a resposta é `not_found`

### Requirement: O agente enfileira builds
O plugin SHALL expor `azure_devops_queue_build` (definition por id ou nome,
branch opcional, variáveis opcionais), devolvendo o id do build enfileirado e
seu status inicial.

#### Scenario: Build enfileirado
- **WHEN** o modelo enfileira a pipeline `ci-main` na branch `main`
- **THEN** a resposta traz o id e o status do build enfileirado

#### Scenario: Definition inexistente
- **WHEN** a pipeline informada não existe
- **THEN** a resposta é `not_found`

### Requirement: Toda escrita confirma o objeto afetado
Toda tool de escrita SHALL devolver, no campo `data`, o identificador do
objeto criado ou alterado e, quando existir, sua url, para que o modelo
confirme sem nova chamada.

#### Scenario: Resposta de escrita é conferível
- **WHEN** qualquer tool de escrita tem sucesso
- **THEN** o campo `data` contém o id do objeto afetado

### Requirement: Conflito de versão é reportado, não contornado
Quando a API recusar uma alteração por conflito de versão (precondição/ETag
desatualizada, objeto alterado por outra pessoa entre a leitura e a escrita), o
plugin SHALL reportar o erro com a mensagem original da API e SHALL NOT repetir
a operação automaticamente.

#### Scenario: Objeto alterado por outra pessoa
- **WHEN** o modelo atualiza um work item que foi alterado por outra pessoa
  depois da última leitura
- **THEN** a resposta é um erro com a mensagem da API sobre o conflito, sem nova
  tentativa automática e sem alteração parcial

### Requirement: Falhas de escrita não deixam estado parcial
O plugin SHALL reportar falhas de escrita com o código de erro da API, sem
retentar a operação automaticamente e sem mascarar a mensagem original.

#### Scenario: Erro de escrita reportado
- **WHEN** a API recusa a operação
- **THEN** a resposta é `{"ok": false, "error": {...}}` com `message` da API e
  nenhuma nova tentativa automática
