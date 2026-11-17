# Design

## Context

O repositório não tem código de plugin ainda; o Hermes v0.23.1 é a referência de
contrato (manifesto, `register(ctx)`, handler de tool, `get_secret`, validação).
Duas restrições da plataforma moldam o desenho:

- o loader do Hermes importa `__init__.py` como pacote e pré-carrega os
  `*.py` irmãos da raiz do plugin — módulos irmãos são relativos resolvidos,
  subpacotes exigem import próprio;
- `hermes plugins doctor` bloqueia socket durante o registro, e o manifesto
  precisa de `provides_tools` **exatamente** igual às tools registradas.

Ver [proposal.md](./proposal.md) para a motivação.

## Goals / Non-Goals

**Goals:**
- Uma base única (config, credencial, cliente HTTP, erro, paginação) que as
  tools das changes seguintes só precisam consumir.
- Manifesto coerente com o registro, verificado por teste.
- Suíte de testes que roda offline e sem PAT.

**Non-Goals:**
- Implementar qualquer tool (changes 2 e 3).
- UI no Desktop, skills, comandos `/ado-help` (change 4).
- Publicação no catálogo oficial do Hermes (change 4).
- Retry/backoff, cache de PAT, suporte a nuvens soberanas além de `base_url`.

## Decisions

### Plugin nativo Python, layout flat na raiz do repo
O pacote do plugin **é** a raiz do repositório (`plugin.yaml` + `__init__.py`
+`*.py` siblings + `skills/`). O loader pré-carrega apenas `*.py` da raiz;
subpacotes (`tools/`) dependeriam de import normal em tempo de registro e
duplicariam módulos (o loader também registra siblings como
`<pkg>.<stem>`).

*Alternativa*: pacote `hermes_azure_devops/` com subpastas — rejeitada por
quebrar o layout de descoberta e o carregamento siblings.

O pacote ganha depois as pastas `dashboard/` e `desktop/` (a metade do app,
change `azure-devops-desktop-surface`). Elas **não** colidem com os módulos
siblings: o loader carrega `*.py` da raiz, e `dashboard/manifest.json` +
`desktop/plugin.js` são lidos por caminhos próprios.

### `httpx` como cliente HTTP, sem `python_dependencies`
`httpx` já é dependência do core do Hermes e o manifesto fica sem
`python_dependencies` (evita consentimento de instalação e o scanner de
segurança). Para cloud soberano/on-prem basta `base_url`.

*Alternativa*: `urllib` da stdlib — rejeitada (sem suporte a PATCH e sem
`MockTransport` para os testes).

### Registro único de tools (`registry.py`) como fonte de verdade
`registry.py` expõe `TOOLS: list[ToolSpec]` (nome, toolset, schema,
handler, `check_fn`). `register(ctx)` itera a lista; `plugin.yaml` é gerado a
partir dela por um script simples e um teste falha se a lista do manifesto
divergir do registro. Divergência é tratada como problema de segurança pela
admissão — não pode ser corrigida à mão.

*Alternativa*: escrever `provides_tools` à mão — rejeitada (divergência
silenciosa).

### `check_fn` declarando "needs auth"
Cada tool registra `check_fn` que verifica a presença do PAT, alimentando a UX
de "needs auth" do Hermes (`hermes auth <name>`).

### Credencial só via `agent.secret_scope.get_secret`
Resolve por perfil ativo, com fail-closed no caso multiplexado sem escopo.
Nada de `os.environ`, `.env` ou `auth.json` (regra 11 do catálogo).

### Cliente criado dentro do handler, nunca no `register()`
O `httpx.Client` é construído por chamada (o `doctor` bloqueia socket no
registro e um client persistente abriria conexão). Sem keep-alive: o custo é
irrelevante diante do custo de rede da API.

### Host único com exceção fixa para Release Management
`base_url` (default `https://dev.azure.com`) atende tudo; paths com
`/_apis/release/` vão para `https://vsrm.dev.azure.com` — verificado na
pesquisa (a rota de release não existe no host `dev`). O host de release é
fixo no código, não setting, porque a exceção é da API, não do usuário.

### Taxonomia de erro fechada
`errors.py` define `AdoError(code, message, status=None, type_key=None)` com
códigos: `not_configured`, `missing_credential`, `invalid_input`,
`unauthorized`, `forbidden`, `not_found`, `rate_limited`, `timeout`,
`upstream_error`. O handler de tool converte `AdoError` (e qualquer exceção
inesperada) no envelope `{"ok": false, "error": {...}}`.

### Versão de API por endpoint (tabela de override)
A `api_version` das settings (default `7.1`) é o default, mas alguns
endpoints exigem versão `-preview`: `/_apis/connectionData` devolve **400**
com `api-version=7.1` e responde 200 com `7.0-preview.1` nesta organização. O
cliente mantém uma **tabela de override por endpoint** (default `7.1`,
`connectionData` → `7.0-preview.1`), e a tabela é a fonte da verdade — não o
handler de cada tool.

*Alternativa*: detectar o 400 e repetir com `-preview` — rejeitada (segunda
requisição, e o erro 400 seria indistinguível de outros).

### Parâmetros com cifrão (`$top`, `$skip`)
A API do Azure DevOps usa `$top`/`$skip` para paginação; o parâmetro `top`
sem cifrão é **ignorado silenciosamente** (a resposta vem completa e sem token
de continuação — paginação quebrada sem erro visível). O cliente codifica
`$top` como `%24top` e o `$top` é o único parâmetro de paginação exposto
pelas tools.

### Paginação normalizada em um campo
`pagination.py` extrai `continuationToken` do header
`x-ms-continuationtoken` e, na ausência dele, do corpo (`continuationToken`,
`nextPage`). Nenhuma tool expõe a forma original do token.

### Transporte injetável via `httpx.MockTransport`
O cliente recebe o `transport` por parâmetro; a suíte usa
`httpx.MockTransport` (stdlib do `httpx`) para simular 200/401/403/404/429/500,
paginação e corpo não-JSON. Nenhuma dependência nova de teste.

### Segredo falso no ambiente de teste
O teste injeta um `get_secret` falso no ponto de resolução, em vez de
depender de `AZURE_DEVOPS_PAT_TOKEN` na máquina.

## Contratos verificados contra a API real (2026-11-17)

Verificação de leitura na organização de referência (PAT de produção + PAT
temporário de escopo total). Detalhes por rota na seção
"Endpoints verificados" do design da change `azure-devops-read-tools`. O que
impacta a base:

- `connectionData` exige `api-version` preview (`7.0-preview.1`); com
  `7.1` devolve 400.
- Paging de builds usa `$top` + header `x-ms-continuationtoken`; `top` sem
  cifrão é ignorado.
- WIQL é POST-only (GET devolve 405; POST sem corpo devolve 411).
- `/_apis/policies/repositories/{repoId}` não é alcançável com PAT clássico
  (401/404); `/_apis/policy/configurations` responde 200.
- Releases exigem `vsrm.dev.azure.com` **e** o segmento do projeto no path.

## Risks / Trade-offs

- [`httpx` deixar de ser dependência do core em uma release futura] → o
  manifesto declara `python_dependencies: ["httpx>=0.27,<1"]` no momento em que
  a dependência passar a ser declarada; até lá, zero dependências extras.
- [Divergência entre manifesto e registro escapar do teste] → o teste compara
  as duas listas nominalmente e a CI roda `hermes plugins validate` + `doctor`.
- [Erro de mapeamento HTTP virar mensagem genérica] → cada status tem código
  próprio e o 403 sempre carrega a dica de escopo de PAT.
- [`MockTransport` não cobrir o comportamento real de TLS/proxy] → aceito: a
  validação de ponta a ponta é feita no smoke manual com PAT real, no change 4.
- [Tokenizer de PAT não escopado por organização] → erro 403 vira `forbidden`
  com dica; não há tentativa de renegociar token.

## Migration Plan

Não há migração: projeto novo, sem base instalada. Rollback = remover o
pacote (`hermes plugins remove azure-devops`).

## Open Questions

- Quais escopos de PAT cada família de operação exige (work items, wiki,
  releases) — affects apenas o texto do `/ado-help`, resolvido na change 4.
