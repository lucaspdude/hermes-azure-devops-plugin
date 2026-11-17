# Tasks

## 1. Conteúdo da ajuda

- [x] 1.1 Escrever `help.py` com `render_help(topic=None)` e o conteúdo em Markdown: escopo de PAT por família de operação, paginação, códigos de erro e armadilhas — verificar renderizando o guia e conferindo que as quatro seções existem
- [x] 1.2 Registrar o slash command `/ado-help` (alias `azure-devops help`) e o subcomando CLI `hermes azure-devops help`, ambos consumindo `render_help` — verificar `hermes plugins doctor . --ci` e executando os dois comandos
- [x] 1.3 Suportar `/ado-help <topico>` destacando a seção pedida sem perder o resto — verificar com o argumento `pull requests`
- [x] 1.4 Embarcar a skill `skills/azure-devops-usage/SKILL.md` com o conteúdo essencial e registrá-la via `ctx.register_skill` — verificar que a skill é carregável pelo namespace do plugin e não aparece no índice global

## 2. Documentação do repositório

- [x] 2.1 Escrever o `README.md`: o que faz, tools, instalação
  (`hermes plugins install`), configuração (`config_schema`), troubleshooting e a seção **Disclosure** (rede para `dev.azure.com`/`vsrm.dev.azure.com`, credencial lida de `AZURE_DEVOPS_PAT_TOKEN` via `agent.secret_scope`, PAT com escopos de escrita, plugin habilitado manualmente) — verificar que o README cita o nome de cada env var e cada setting
- [x] 2.2 Inserir no README a lista de tools gerada a partir do registro e a mesma ajuda do plugin — verificar que a lista gerada bate com `provides_tools` do manifesto
- [x] 2.3 Adicionar `LICENSE` (MIT) e os campos `license`, `homepage` e `tags` no manifesto — verificar com `hermes plugins validate .` que o SPDX é aceito

## 3. CI e gate de catálogo

- [x] 3.1 Criar `.github/workflows/ci.yml` rodando a suíte, `hermes plugins validate . --install-deps` e `hermes plugins doctor . --ci` em push e PR — verificar com um PR de teste que os três passos passam
- [x] 3.2 Preparar `docs/catalog-entry.yaml` no formato `plugin-catalog/<name>.yaml` (nome, repo, `sha` a preencher, descrição, maintainer, tier `community`, categoria `tools`, `requires_hermes`, capabilities) — verificar que o arquivo tem todos os campos obrigatórios do schema
- [x] 3.3 Escrever o texto de descrição do PR de catálogo com o disclosure da regra 13 — verificar que rede, credencial e escopos de PAT estão declarados
- [x] 3.4 Publicar o repo **público** no GitHub (pré-requisito da instalação no hostgator por `hermes plugins install owner/repo`) e confirmar a instalação a partir do hostgator — verificar que o comando instala e habilita o plugin no host alvo

## 4. Validação final

- [x] 4.1 Rodar `hermes plugins validate . --install-deps`, `hermes plugins doctor . --ci` e a suíte — verificar que tudo termina limpo
- [ ] 4.2 Fazer o smoke manual com PAT real **no hostgator**: `/ado-help`, uma leitura, uma escrita e um erro 403 — verificar que a ajuda aparece no chat daquele host, a leitura funciona e o 403 traz a dica de escopo **BLOCKED (parcial)**: o smoke com PAT real exige `AZURE_DEVOPS_PAT_TOKEN` no perfil do host (`pat_presente: False` no secret scope). A renderização do `/ado-help` foi verificada no host (5573 chars, seções e tabela de escopos presentes).
