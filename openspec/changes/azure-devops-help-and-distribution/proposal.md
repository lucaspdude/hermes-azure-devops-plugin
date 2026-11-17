# Proposal

## Why

O plugin terá tools, mas o usuário ainda vai errar: PAT sem o escopo certo,
paginação não entendida, erro 403 sem explicação. E o plugin, mesmo pronto,
não é instalável por um terceiro sem README, licença e CI — o catálogo oficial
do Hermes exige disclosure explícito (rede para `dev.azure.com`, credencial
lida de `AZURE_DEVOPS_PAT_TOKEN`) e validação automatizada.

## What Changes

- Registra o comando de ajuda do plugin: `/ado-help` na conversa e
  `hermes azure-devops help` no terminal, com o mesmo conteúdo — escopo de PAT
  exigido por cada família de operação, como usar a paginação, os códigos de
  erro e as armadilhas conhecidas.
- Embarca **duas skills**: `azure-devops-usage` (o contrato: escopo de PAT por
  operação, paginação, códigos de erro, id vs nome, armadilhas) e
  `azure-devops-workflows` (as receitas: PR com build vermelho, investigar build
  falho, work item atribuído a mim, votar/concluir PR, criar PR a partir de
  branch, enfileirar build).
- Escreve o `README.md` do plugin: o que faz, disclosure (rede para
  `dev.azure.com`/`vsrm.dev.azure.com`, credencial lida via
  `agent.secret_scope`, PAT em mãos do Hermes), instalação, configuração,
  troubleshooting e a lista de tools.
- Adiciona `LICENSE` (MIT) e o campo `license` no manifesto.
- Adiciona CI de validação (`hermes plugins validate` + `doctor --ci` +
  suíte de testes) em todo push/PR, ao lado do workflow de release já existente.
- Prepara a entrada do catálogo oficial do Hermes (`plugin-catalog/azure-devops.yaml`
  no repo do Hermes) como artefato do repo, para o PR de catálogo ser um diff
  pequeno e revisável. A chave do catálogo é `azure-devops`, igual ao `name:`
  do manifesto, com `title: "Azure DevOps"` e `tier: community`.

## Capabilities

### New Capabilities
- `azure-devops-help`: a ajuda operacional do plugin — comando `/ado-help`,
  subcomando CLI `hermes azure-devops help` e skill embarcada — cobrindo escopo
  de PAT por operação, paginação, códigos de erro e armadilhas.

### Modified Capabilities

(nenhuma)

## Impact

- **Depende de**: `azure-devops-plugin-foundation` (manifesto, comando e skills) e das changes de leitura e escrita (a ajuda documenta as tools que existem).
- **Novo código**: `help.py` (conteúdo da ajuda, renderizado em Markdown
  para slash command e para CLI), `skills/azure-devops-usage/SKILL.md`,
  `README.md`, `LICENSE`, `.github/workflows/ci.yml`,
  `docs/catalog-entry.yaml`.
- **Manifesto**: campos `license`, `homepage`, `tags` e o registro do
  comando/skill.
- **Sistemas externos**: nenhum novo; o CI roda as ferramentas do Hermes
  (`validate`, `doctor`) no runner.
- **Fora de escopo**: a listagem no catálogo oficial depende de PR no repo do
  Hermes (fora deste repositório) — esta change entrega o arquivo pronto.
