# Spec Delta

## Purpose

Define a fundação do plugin Hermes para Azure DevOps: como o plugin é
declarado, como a organização e as settings são obtidas, como o PAT é resolvido
pelo mecanismo de segredo do Hermes, e qual o contrato (JSON, erros,
paginação, host) que toda tool do plugin deve obedecer.

## ADDED Requirements

### Requirement: Manifesto declara a identidade e as superfícies do plugin
O plugin SHALL ser um plugin nativo Python com `plugin.yaml` na raiz do pacote,
`manifest_version: 2`, `name`, `version`, `description`, `requires_hermes`
com piso SemVer válido e `requires_env` declarando `AZURE_DEVOPS_PAT_TOKEN`
em UPPER_SNAKE_CASE (formato rico, com `secret: true`).

#### Scenario: Manifesto é aceito pelo validador
- **WHEN** o pacote é submetido a `hermes plugins validate`
- **THEN** nenhuma complains é emitida sobre campos do manifesto, `requires_env`
  ou `requires_hermes`

#### Scenario: Piso de versão do Hermes é declarado nos dois lugares
- **WHEN** o manifesto é lido
- **THEN** `requires_hermes` está presente em `plugin.yaml` e é um piso SemVer
  (ex.: `>=0.23`), nunca uma data nem uma versão acima da release suportada

### Requirement: O manifesto e o registro de tools não divergem
A lista `provides_tools` do manifesto SHALL ser derivada do registro único de
tools do plugin, e o sistema SHALL falhar de forma explícita (teste automatizado)
quando as duas listas divergirem.

#### Scenario: Divergência é detectada antes do merge
- **WHEN** uma tool é adicionada ao registro e esquecida no manifesto
- **THEN** o teste de consistência falha indicando o nome da tool faltante

### Requirement: As settings do plugin são lidas do config do Hermes
As settings `organization`, `base_url`, `api_version`, `default_project` e
`http_timeout_ms` SHALL ser lidas das settings do plugin no `config.yaml` do
perfil, com defaults `https://dev.azure.com`, `7.1`, string vazia e `30000`;
`organization` SHALL ser obrigatória e sem default (o plugin é genérico).

#### Scenario: Organização é obrigatória
- **WHEN** uma tool é chamada e `organization` não está configurada
- **THEN** a resposta é `{"ok": false, "error": {"code": "not_configured", ...}}`
  com indicação de qual setting falta, e nenhuma requisição é feita

#### Scenario: Defaults são aplicados
- **WHEN** apenas `organization` está configurada
- **THEN** as requisições vão para `https://dev.azure.com` com
  `api-version=7.1` e timeout de 30 segundos

### Requirement: O PAT é resolvido pelo mecanismo de segredo do Hermes
O token SHALL ser obtido exclusivamente por `agent.secret_scope.get_secret`
com o nome `AZURE_DEVOPS_PAT_TOKEN` resolvido no perfil ativo; o plugin SHALL
NOT ler `.env`, `auth.json` nem o ambiente do processo.

#### Scenario: Segredo ausente
- **WHEN** o PAT não está disponível para o perfil ativo
- **THEN** a tool responde `{"ok": false, "error": {"code": "missing_credential", ...}}`
  explicando como definir `AZURE_DEVOPS_PAT_TOKEN`, sem stack trace

#### Scenario: Segredo nunca aparece em log ou resposta
- **WHEN** uma requisição falha e o erro é registrado ou devolvido
- **THEN** o header `Authorization` e o valor do PAT não aparecem em nenhum dos dois

### Requirement: Requisições usam o esquema de autenticação oficial do Azure DevOps
O cliente SHALL enviar o PAT como Basic (`base64(":" + pat)`), o header
`Accept: application/json`, o parâmetro `api-version` e um timeout explícito
derivado de `http_timeout_ms`.

#### Scenario: Header de autorização no formato esperado
- **WHEN** o cliente envia uma requisição com PAT `abc`
- **THEN** o header `Authorization` é `Basic <base64(":abc")>`

#### Scenario: Timeout expira
- **WHEN** a API não responde dentro de `http_timeout_ms`
- **THEN** a tool responde `{"ok": false, "error": {"code": "timeout", ...}}`

### Requirement: Toda resposta de tool é uma JSON string
Toda tool SHALL devolver uma JSON string, com `ok: true` e `data` no caminho
feliz e `ok: false` com `error` (código, mensagem e contexto mínimo) no
caminho infeliz; nenhuma exceção SHALL escapar do handler.

#### Scenario: Handler nunca levanta
- **WHEN** a API devolve HTML em vez de JSON ou o cliente falha de forma
  inesperada
- **THEN** a tool devolve `{"ok": false, "error": {"code": "upstream_error", ...}}`
  em vez de propagar a exceção

#### Scenario: Payloads de sucesso são previsíveis
- **WHEN** uma tool de listagem do plugin tem sucesso
- **THEN** a resposta é `{"ok": true, "data": {...}}` decodificável como JSON

### Requirement: Falhas da API são traduzidas em códigos acionáveis
O cliente SHALL mapear falhas HTTP para códigos estáveis: `unauthorized` (401),
`forbidden` (403), `not_found` (404), `rate_limited` (429) e
`upstream_error` (5xx e falhas de parse), preservando `message` e
`typeKey` do corpo de erro quando existirem; SHALL NOT repetir requisições.

#### Scenario: 403 sugere escopo de PAT
- **WHEN** a API responde 403
- **THEN** o erro é `forbidden` e a mensagem indica que o PAT pode não ter o
  escopo exigido pela operação

#### Scenario: Sem retry
- **WHEN** a API responde 500
- **THEN** o plugin faz exatamente uma requisição e devolve `upstream_error`

### Requirement: A versão de API e o parâmetro de paginação são os que a API espera
O cliente SHALL usar, por endpoint, a versão de API que aquele endpoint aceita
(`7.1` por padrão; versão `-preview` para os endpoints que exigem), e SHALL
enviar o parâmetro de paginação no formato com cifrão (`$top`), expondo nas
tools apenas `top`.

#### Scenario: Endpoint que exige versão preview
- **WHEN** o plugin chama um endpoint que só responde em versão preview
- **THEN** a requisição usa a versão preview específica e tem sucesso, em vez de
  falhar com erro de versão

#### Scenario: Paginação com o parâmetro certo
- **WHEN** o modelo pede `top` numa listagem paginada
- **THEN** o parâmetro é enviado com cifrão (`%24top`), a API pagina de fato e
  a resposta traz o token de continuação

### Requirement: Paginação é exposta de forma uniforme
Toda listagem paginada SHALL devolver um único campo `continuationToken`
(vazio quando não há mais páginas), obtido do header
`x-ms-continuationtoken` (builds) ou do corpo (demais APIs), e o token
devolvido SHALL ser aceito como entrada da próxima página.

#### Scenario: Builds devolvem o token do header
- **WHEN** a API de builds responde com `x-ms-continuationtoken`
- **THEN** a resposta traz esse valor em `continuationToken`

#### Scenario: Token de continuação é utilizável
- **WHEN** o modelo repete a chamada passando o `continuationToken` recebido
- **THEN** a API devolve a página seguinte

### Requirement: Release Management é atendido no host correto
Requisições cujo path contenha `/_apis/release/` SHALL ir para
`https://vsrm.dev.azure.com`; todas as demais SHALL ir para o `base_url`
configurado. O host de release não é uma setting.

#### Scenario: Path de release é roteado
- **WHEN** o plugin chama a API de release definitions
- **THEN** a requisição é feita para `vsrm.dev.azure.com` com o segmento da
  organização e do projeto no path

#### Scenario: Demais rotas usam o host configurado
- **WHEN** o plugin chama a API de builds
- **THEN** a requisição é feita para o `base_url` configurado

### Requirement: O registro não executa I/O
`register(ctx)` SHALL NOT fazer requisição de rede, ler segredo ou bloquear;
toda comunicação com a API ocorre dentro do handler da tool.

#### Scenario: Doctor passa sem rede
- **WHEN** `hermes plugins doctor . --ci` roda (que bloqueia socket durante o
  registro)
- **THEN** o plugin é registrado sem erro

### Requirement: O comportamento é testável offline
O pacote SHALL expor um ponto de injeção de transporte HTTP para que os testes
rodem sem rede e sem PAT, e a suíte SHALL passar sem credencial configurada.

#### Scenario: Teste de tool sem credencial
- **WHEN** a suíte roda em uma máquina sem `AZURE_DEVOPS_PAT_TOKEN`
- **THEN** os testes passam usando o transporte falso e o segredo falso
