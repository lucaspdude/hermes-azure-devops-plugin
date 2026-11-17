# Tasks

## 1. Esqueleto do pacote

- [ ] 1.1 Criar `plugin.yaml` na raiz do repo com `manifest_version: 2`, `name: azure-devops`, `version`, `description`, `requires_hermes: ">=0.23"` e `requires_env` no formato rico para `AZURE_DEVOPS_PAT_TOKEN` (com `secret: true`, `description` e `url` da Microsoft) — verificar com `hermes plugins validate .` que não há complains sobre manifesto/`requires_env`/`requires_hermes`
- [ ] 1.2 Criar `__init__.py` com `register(ctx)` que itera o registro de tools e registra o comando/skill (deixando o esqueleto pronto, sem I/O) — verificar com `hermes plugins doctor . --ci` que o plugin carrega sem erro
- [ ] 1.3 Declarar no manifesto o `config_schema` com `organization` (obrigatória, sem default), `base_url` (default `https://dev.azure.com`), `api_version` (default `7.1`), `default_project` (default vazio) e `http_timeout_ms` (default `30000`) — verificar que `hermes plugins validate .` aceita o schema e que as settings aparecem no `config.yaml` do perfil

## 2. Configuração e credencial

- [ ] 2.1 Implementar `config.py` lendo as settings via `ctx.get_config` e devolvendo um objeto `PluginConfig` com os defaults do manifesto — verificar por teste unitário que `organization` ausente resulta em `not_configured`
- [ ] 2.2 Implementar `auth.py` resolvendo o PAT via `agent.secret_scope.get_secret("AZURE_DEVOPS_PAT_TOKEN")`, com `check_fn` reutilizável para marcar "needs auth" — verificar por teste que a ausência do segredo produz `missing_credential` e que o valor do PAT não aparece na mensagem

## 3. Cliente HTTP, erros e paginação

- [ ] 3.1 Implementar `errors.py` com a taxonomia fechada (`not_configured`, `missing_credential`, `invalid_input`, `unauthorized`, `forbidden`, `not_found`, `rate_limited`, `timeout`, `upstream_error`) — verificar por teste unitário o mapeamento de 401/403/404/429/500 e de corpo não-JSON
- [ ] 3.2 Implementar `client.py` (`httpx`) com Basic `base64(":" + pat)`, header `Accept`, parâmetro `api-version`, timeout de `http_timeout_ms`, criação do client dentro do handler e `transport` injetável — verificar por teste com `httpx.MockTransport` que o header de autorização e a query `api-version` saem corretos
- [ ] 3.3 Implementar em `client.py` o roteamento de host: path com `/_apis/release/` → `https://vsrm.dev.azure.com`, demais → `base_url` — verificar por teste que as duas rotas são chamadas nos hosts corretos
- [ ] 3.4 Implementar `pagination.py` extraindo `continuationToken` do header `x-ms-continuationtoken` e do corpo, e verificar que o token devolvido é aceito como entrada da próxima página — verificar por teste com `MockTransport`

## 4. Registro único de tools

- [ ] 4.1 Criar `registry.py` com `TOOLS` (nome, toolset, schema, handler, `check_fn`) e o gerador do bloco `provides_tools` do manifesto — verificar que o gerador produz uma lista determinística e estável
- [ ] 4.2 Escrever o teste de consistência manifesto ↔ registro (compara `provides_tools` do `plugin.yaml` com `TOOLS`) — verificar que o teste falha ao remover uma tool do manifesto e passa com a lista em sincronia

## 5. Harness de testes

- [ ] 5.1 Criar o helper de teste com `httpx.MockTransport` e segredo falso injetado (sem `AZURE_DEVOPS_PAT_TOKEN` na máquina) — verificar que a suíte roda e passa em uma máquina sem PAT
- [ ] 5.2 Escrever os testes do envelope de resposta (sucesso `{"ok": true, "data": ...}`, erro `{"ok": false, "error": {...}}`) e que nenhuma exceção escapa do handler — verificar que a suíte passa

## 6. Validação final no host alvo

O host alvo é `hostgator` (VPS, alias SSH `hostgator`), com **Hermes Agent
v0.23.2** instalado em `/root/.hermes/hermes-agent` (CLI em
`/root/.local/bin/hermes`) e interpretador gerenciado **Python 3.14.9** em
`/root/.hermes/tools/python-3.14.9+20261021-linux-x64/bin/python3`. É no host
alvo que a verificação canônica acontece (o `python3` do sistema lá é 3.9 e
não serve para rodar o plugin).

- [ ] 6.1 Rodar `hermes plugins validate . --install-deps` e `hermes plugins doctor . --ci` localmente **e no hostgator** (pacote copiado para `/root/.hermes/plugins/azure-devops`) e corrigir tudo que aparecer — verificar que ambos terminam limpos nos dois lugares
- [ ] 6.2 Instalar o plugin no hostgator pelo repo (`hermes plugins install owner/hermes-azure-devops-plugin`), habilitar em `plugins.enabled` e confirmar que o PAT chega pelo perfil do host (nada de token no config) — verificar com `hermes plugins list` mostrando o plugin habilitado e com uma tool devolvendo `missing_credential` quando o PAT não está no perfil
- [ ] 6.3 Rodar a suíte no hostgator **com o interpretador do Hermes** (`/root/.hermes/tools/python-3.14.9*/bin/python3`), nunca com o `python3` do sistema — verificar que a suíte passa no 3.14 e que nenhum teste depende de rede ou de credencial
