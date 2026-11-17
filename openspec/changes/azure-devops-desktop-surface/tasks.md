# Tasks

## 1. Spikes de superfície do Desktop SDK

- [ ] 1.1 Verificar no SDK o que a página, a linha da sidebar e o chip do status bar aceitam de fato (campos do `data`, assinatura do `render`, `ctx.rest`, `ctx.onEvent`, `ctx.setInterval`) e registrar em `design.md` do plugin qualquer diferença em relação ao esperado — verificar com um `desktop/plugin.js` mínimo carregado no app
- [ ] 1.2 Verificar se a correspondência entre a sessão da linha (`durable stored id`) e a conversa do agente (`conversation_id`/`session_id`) é obtenível; se não for, registrar a decisão de não entregar badge de linha e manter o sinal na página — verificar com um spike que registra um id em cada lado e compara

## 2. Backend do painel

- [ ] 2.1 Criar `dashboard/manifest.json` (`{"name": "azure-devops", "api": "plugin_api.py"}`) e `dashboard/plugin_api.py` com `router = APIRouter()` importando o mesmo cliente do agente — verificar que as rotas montam em `/api/plugins/azure-devops/` e que o erro 404 do backend ausente é distinguível do 404 do Azure DevOps
- [ ] 2.2 Implementar a rota `GET /overview` (PRs do usuário, work items atribuídos, builds recentes do usuário) usando a identidade de `/_apis/connectionData` e degradando com aviso quando o escopo de identidade faltar — verificar com `httpx.MockTransport` o payload agregado e o caminho de degradação
- [ ] 2.3 Implementar o cache em memória de ~15s por escopo, invalidado por evento — verificar com `MockTransport` que duas leituras dentro da janela geram **uma** chamada à API
- [ ] 2.4 Implementar as rotas de detalhe (`GET /pull-requests/{id}`, `GET /builds/{id}`) reaproveitando as tools/módulos existentes — verificar com `MockTransport` que o payload é o mesmo que o das tools

## 3. Invalidação por evento

- [ ] 3.1 Fazer as tools de escrita emitirem o evento de invalidação após sucesso (sem alterar o contrato de retorno das tools) — verificar que o envelope `{"ok": true, "data": ...}` continua idêntico e que o evento é emitido
- [ ] 3.2 Fazer a página re-buscar o estado por REST ao receber o evento e manter o polling como reconciliação — verificar que, sem evento, a página ainda converge no próximo ciclo

## 4. UI do Desktop

- [ ] 4.1 Implementar a página `/azure-devops` em `desktop/plugin.js` (ESM, sem JSX, `jsx()`, cores `var(--ui-*)`) com as três seções (PRs, work items, builds) e estado de carregamento/erro — verificar no app que a página renderiza com dados do `MockTransport`
- [ ] 4.2 Registrar a linha da sidebar (label, codicon, rota) e o chip do status bar com a contagem, com clique navigating para a página — verificar no app que a linha acende na rota e que o chip abre a página
- [ ] 4.3 Tratar o 404 do backend ausente com mensagem acionável e tratar o erro de escopo de identidade com aviso visível na seção afetada — verificar simulando 404 e 403
- [ ] 4.4 Implementar o polling com `ctx.setInterval` (nunca `window.setInterval`) e limpeza do timer no disable — verificar que nenhum timer sobrevive ao disable do plugin
- [ ] 4.5 Modelar o `dashboard/manifest.json` no formato em uso pelo plugin vivo de referencia (`name`, `label`, `description`, `icon`, `version`, `api: plugin_api.py`) e o `plugin_api.py` com `router = APIRouter()` e rotas `@router.get(...)` — verificar que as rotas montam em `/api/plugins/azure-devops/...` no hostgator

## 5. Documentação e gates

- [ ] 5.1 Documentar no README os dois gates (plugin em `plugins.enabled` + toggle da meia desktop em Capabilities → Plugins), o 404 silencioso e o fluxo de desenvolvimento (symlink + Rescan / cópia stale) — verificar que o README cita os dois gates e o sintoma de cada um
- [ ] 5.2 Registrar no README que o painel é read-only e que a visão por projeto fica nas tools do agente — verificar que o texto diz onde buscar cada informação

## 6. Validação final

- [ ] 6.1 Rodar `hermes plugins validate . --install-deps` e `hermes plugins doctor . --ci` **no hostgator** (o doctor cobre a superfície desktop e a cópia stale) — verificar que ambos terminam limpos no host alvo
- [ ] 6.2 Verificar as rotas do painel **no hostgator** (é lá que roda o backend `plugin_api.py` do gateway) e a UI no app Desktop conectado a esse host (o host já tem `desktop-ssh` configurado): abrir o painel, ver PRs/work items/builds do usuário e provoque um 403 — verificar que `/api/plugins/azure-devops/overview` responde no host e que a página lista a atividade com erro acionável
- [ ] 6.3 Confirmar no hostgator que a metade desktop foi materializada (`/root/.hermes/desktop-plugins/azure-devops/plugin.js`) depois da instalacao do plugin e que o `doctor` nao acusa copia stale — verificar com `hermes plugins doctor . --ci` no host e com o arquivo presente no host
- [ ] 6.4 Verificar que o backend do painel roda no perfil ativo do gateway (o host serve `default` e `hub-documentador`) e que o `ctx.rest` do app atravessa a conexao SSH sem cair em 404 — verificar abrindo o painel pelo app Desktop conectado ao hostgator
