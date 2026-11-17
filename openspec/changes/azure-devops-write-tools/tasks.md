# Tasks

## 1. Pull requests — criação, comentários e labels

- [x] 1.1 Implementar `azure_devops_create_pull_request` (source/target/title/description/isDraft/reviewerIds) — verificar com `MockTransport` o payload enviado e o id/url devolvidos
- [x] 1.2 Implementar `azure_devops_add_pull_request_comment` (nova thread ou resposta com `threadId`/`status`) — verificar com `MockTransport` o corpo do POST e o id do comentário devolvido
- [x] 1.3 Implementar `azure_devops_add_pull_request_label` e `azure_devops_remove_pull_request_label` — verificar com `MockTransport` as rotas de POST e DELETE e a confirmação da label

## 2. Pull requests — votos, abandono e conclusão

- [x] 2.1 Implementar a resolução da identidade autenticada via `/_apis/connectionData` reutilizável pelas tools de voto — verificar com `MockTransport` que a identidade é buscada a cada chamada
- [x] 2.2 Implementar `azure_devops_approve_pull_request`, `azure_devops_reject_pull_request` e `azure_devops_reset_pull_request_vote` (votos 10/5/0) — verificar com `MockTransport` o `reviewerId` usado e o voto enviado
- [x] 2.3 Implementar `azure_devops_abandon_pull_request` e `azure_devops_complete_pull_request` (`deleteSourceBranch`, `squashMerge`) — verificar com `MockTransport` o PATCH enviado e o status devolvido
- [x] 2.4 Testar o caminho de `forbidden` (PAT sem permissão de escrita/voto) garantindo que a mensagem original da API aparece no erro — verificar com `MockTransport` simulando 403

## 3. Work items e wiki

- [x] 3.1 Implementar `azure_devops_update_work_item` com operações JSON Patch e retorno do work item atualizado — verificar com `MockTransport` o corpo do PATCH e o campo alterado
- [x] 3.2 Implementar `azure_devops_create_wiki_page` e `azure_devops_update_wiki_page` — verificar com `MockTransport` o caminho, o conteúdo e a versão devolvidos

## 4. Builds

- [x] 4.1 Implementar `azure_devops_queue_build` resolvendo a definition por nome ou id e aceitando branch e variáveis — verificar com `MockTransport` o payload do POST e o id/status do build enfileirado

## 5. Registro, manifesto e validação

- [x] 5.1 Agregar os módulos de escrita em `registry.py` e atualizar `provides_tools` no manifesto — verificar que o teste de consistência passa
- [x] 5.2 Escrever as descrições das tools de escrita, deixando explícito que são ações que alteram estado — verificar que toda tool nova tem `check_fn` e descrição
- [x] 5.3 Conferir a paridade das escritas com o MCP (`src/tools.ts`) e registrar diferenças deliberadas — verificar com a lista comparada anexada ao PR
- [x] 5.4 Rodar a suíte, `hermes plugins validate . --install-deps` e `hermes plugins doctor . --ci` **no hostgator** — verificar que tudo termina limpo no host alvo
- [ ] 5.5 Fazer o smoke de escrita no hostgator contra um projeto de teste da organização (criar PR, comentar, rotular, votar, abandonar/concluir, atualizar work item, enfileirar build) — verificar que cada escrita devolve o id do objeto afetado e que o evento de invalidação é emitido **BLOCKED (parcial)**: mesmo motivo da task 8.5 da change de leitura — o PAT ainda não está no perfil do hostgator (`pat_presente: False` no secret scope). **Parcialmente executado**: a leitura com PAT real esta verde (ver change read-tools). As 13 escritas ainda nao foram exercitadas contra a organizacao real — executar contra um projeto de teste antes de arquivar.
