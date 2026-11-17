# Design

## Context

Ver [proposal.md](./proposal.md). As changes anteriores entregaram fundação,
leitura e escrita. Falta a camada de **uso** (ajuda + skill) e a de
**distribuição** (README, licença, CI, entrada de catálogo).

A pesquisa (§8) já decidiu: a ajuda é **comando**, não tool — um tool de ajuda
consome contexto do modelo à toa; o comando é acionado pelo usuário. O prefixo
do comando é `/ado-help` (curto para digitar) com alias
`azure-devops help`.

O repositório já tem `.github/workflows/release.yml` (tag e GitHub Release a
partir dos Conventional Commits) e `AGENTS.md` com as regras de branch/commit.

## Goals / Non-Goals

**Goals:**
- O usuário descobre, em um comando, o escopo de PAT que precisa e como usar a
  paginação.
- O repositório passa no gate do catálogo (`validate` + `doctor` + `ci`) e
  tem disclosure completo.
- O PR de catálogo é um diff de um arquivo.

**Non-Goals:**
- Meia desktop (página, status bar) — o plugin é agent-side.
- Publicar de fato no catálogo (PR no repo do Hermes, feito à parte).
- Tutorial de Git/Gitflow.

## Decisions

### Duas skills, e elas são a fonte do conteúdo
O conhecimento que o agente precisa vem em **duas skills embarcadas**:
`azure-devops-usage` (o contrato: escopo de PAT por operação, paginação, os 9
códigos de erro, id vs nome, a armadilha do `vsrm`) e `azure-devops-workflows`
(as receitas: PR com build vermelho, investigar build falho, work item atribuído
a mim, votar/concluir PR, criar PR a partir de branch, enfileirar build).

Os arquivos `SKILL.md` são a **fonte do conteúdo**: `help.py` os lê e compõe o
`/ado-help` (e o `hermes azure-devops help`) a partir deles. Divergência entre
a ajuda, as skills e o README passa a ser estruturalmente difícil.

*Alternativa*: uma skill só (uso + receitas) — rejeitada: o agente paga o
preço inteiro quando quer só uma parte.

*Alternativa*: replicar o conteúdo da skill na descrição de cada uma das 44
tools — rejeitada: 44 descrições longas em todo contexto é caro, e a
descrição tem que ser curta ("o que faz e quando usar"), com a profundidade na
skill.

### As descrições das tools ficam curtas e precisas
A descrição de cada tool responde **o que faz e quando usar** — nada mais. O
contrato (escopos, paginação, erros) vive nas skills; repetir isso no schema
de 44 tools seria o mesmo texto 44 vezes no contexto do modelo.

### Ajuda como comando, não tool
A pesquisa já cerró isso: tool de ajuda polui o contexto do modelo. O comando
roda no gateway e **retorna texto** (`print()` não chega ao usuário).

### Escopo de PAT por família de operação
O guia é organizado por família (o que o usuário precisa habilitar no PAT), e
cada seção traz: escopo necessário, sintoma da falta, exemplo de chamada.

Os nomes oficiais dos escopos (tabela "Available scopes" da documentação de
OAuth do Azure DevOps) e o que cada família exige:

| Família | Leitura | Escrita |
|---|---|---|
| Code (repos, PRs, labels, threads) | `vso.code` | `vso.code_write` |
| Build (pipelines, builds, artifacts) | `vso.build` | `vso.build_execute` |
| Work items (WIQL, work item) | `vso.work` | `vso.work_write` |
| Project and team (projetos, repos) | `vso.project` | `vso.project_write` |
| Release (definitions, releases) | `vso.release` | `vso.release_execute` |
| Wiki (wikis, páginas) | `vso.wiki` | `vso.wiki_write` |
| Identity (usuário autenticado, votos) | `vso.identity` | `vso.identity_manage` |

Duas regras da documentação de PAT que o guia precisa dizer:

1. **PAT organization-scoped**: a documentação oficial passou a exigir PAT
   vinculado à organização ("create only organization-scoped PATs").
2. **PAT global deixa de funcionar em 1º de dezembro de 2026** — um PAT global
   usado hoje quebra em quinze dias. O guia alerta sobre isso.

O guia diz "escopo mínimo típico" por família e manda o usuário conferir a
página oficial do PAT, com o link.

### CI: `validate` + `doctor` + suíte
Workflow `.github/workflows/ci.yml` em push/PR: instala as dependências de
teste, roda a suíte, roda `hermes plugins validate . --install-deps` e
`hermes plugins doctor . --ci`. O mesmo gate do catálogo, rodando em todo
push.

### Entrada de catálogo como artefato do repo
`docs/catalog-entry.yaml` guarda a entrada no formato
`plugin-catalog/<name>.yaml` (com `sha` a preencher no momento do PR), para
o PR no repo do Hermes ser um arquivo colado.

### README com disclosure explícito
A regra 13 exige declarar: chamadas de rede a terceiros, credenciais
guardadas/lidas, e o escopo do que o plugin faz. O README tem uma seção
**Disclosure** dedicada, referenciada também pela descrição do PR de catálogo.

### Nome do plugin e chave do catálogo
O `name:` do manifesto é `azure-devops` — é ele que o usuário digita
(`hermes plugins enable azure-devops`) e é ele que será a **chave do catálogo**
(`plugin-catalog/azure-devops.yaml`), porque a chave do catálogo e o `name:` do
manifesto são a mesma identidade para o usuário. O README do catálogo usa
`title: "Azure DevOps"` e `tier: community`, com o `maintainer` explícito —
para não parecer plugin oficial da Microsoft. Não há entrada de Azure no
catálogo hoje, então o nome está livre.

A instalação por repositório (`hermes plugins install owner/hermes-azure-devops-plugin`)
continua disponível e é a forma principal de instalar antes da listagem no
catálogo.

### Licença MIT
`LICENSE` + `license: MIT` no manifesto (campo SPDX aceito pelo manifesto).

## Risks / Trade-offs

- [Escopos de PAT desatualizados pelo Azure DevOps] → a ajuda diz "escopo
  mínimo típico" e manda o usuário conferir a página oficial do PAT; link
  incluso.
- [CI depende de uma instalação do Hermes no runner] → a CI instala o Hermes
  via pip/uv antes de rodar `validate`/`doctor`; se o pin ficar instável, a
  CI usa a mesma versão declarada em `requires_hermes`.
- [Divergência entre a ajuda e as tools] → a lista de tools do README é gerada
  do registro (mesma fonte do manifesto) por um script simples.
- [Divergência entre a ajuda e o README] → o conteúdo vem de `help.py`; o
  README embute o mesmo texto.

## Migration Plan

Nenhuma. Rollback: reverter os commits da change.

## Open Questions

(nenhuma que afete specs ou tasks)
