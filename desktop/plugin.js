import { useState, useEffect, useCallback, useMemo } from 'react'
import { jsx, jsxs } from 'react/jsx-runtime'
import { ROUTES_AREA, SIDEBAR_NAV_AREA, STATUSBAR_AREAS, host } from '@hermes/plugin-sdk'

const PLUGIN_ID = 'azure-devops'
const PAGE_PATH = '/azure-devops'
const POLL_MS = 15000
const PRESETS = [
  { label: '7 dias', days: 7 },
  { label: '30 dias', days: 30 },
  { label: '90 dias', days: 90 },
]
const TABS = [
  { id: 'prs', label: 'Pull Requests' },
  { id: 'wis', label: 'Work Items' },
  { id: 'builds', label: 'Builds' },
  { id: 'releases', label: 'Releases' },
]

const styles = {
  page: { padding: '16px', overflowY: 'auto', height: '100%', boxSizing: 'border-box' },
  bar: { display: 'flex', gap: '8px', alignItems: 'center', marginBottom: '12px', flexWrap: 'wrap' },
  preset: (active) => ({
    padding: '4px 10px',
    fontSize: '12px',
    borderRadius: '12px',
    cursor: 'pointer',
    border: '1px solid ' + (active ? 'var(--ui-accent)' : 'var(--ui-border)'),
    color: active ? 'var(--ui-accent)' : 'var(--ui-text-secondary)',
  }),
  search: {
    flex: '1 1 160px',
    minWidth: '140px',
    padding: '4px 8px',
    fontSize: '12px',
    border: '1px solid var(--ui-border)',
    borderRadius: '6px',
    background: 'var(--ui-input-bg, transparent)',
    color: 'var(--ui-text)',
  },
  updated: { color: 'var(--ui-text-secondary)', fontSize: '11px' },
  tabs: { display: 'flex', gap: '4px', borderBottom: '1px solid var(--ui-border)', marginBottom: '12px' },
  tab: (active) => ({
    padding: '6px 12px',
    fontSize: '13px',
    cursor: 'pointer',
    borderBottom: active ? '2px solid var(--ui-accent)' : '2px solid transparent',
    fontWeight: active ? 600 : 400,
    color: active ? 'var(--ui-text)' : 'var(--ui-text-secondary)',
  }),
  badge: (color) => ({
    padding: '2px 8px',
    borderRadius: '10px',
    fontSize: '11px',
    background: color + '22',
    color,
    flexShrink: 0,
    minWidth: '86px',
    textAlign: 'center',
    boxSizing: 'border-box',
  }),
  sectionTitle: { fontSize: '12px', color: 'var(--ui-text-secondary)', marginBottom: '6px' },
  row: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: '8px',
    padding: '6px 4px',
    fontSize: '13px',
    borderBottom: '1px solid var(--ui-border)',
    cursor: 'pointer',
  },
  rowPrimary: { overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: '1 1 auto', minWidth: 0 },
  rowSecondary: { color: 'var(--ui-text-secondary)', fontSize: '12px', flexShrink: 0, minWidth: '64px', textAlign: 'right' },
  empty: { color: 'var(--ui-text-secondary)', fontSize: '13px', padding: '12px 0' },
  warning: {
    padding: '8px',
    marginBottom: '12px',
    border: '1px solid var(--ui-warning, var(--ui-border))',
    borderRadius: '6px',
    fontSize: '12px',
  },
  footer: { color: 'var(--ui-text-secondary)', fontSize: '11px', marginTop: '12px' },
  ignoredZone: { margin: '12px 0', padding: '10px', border: '1px solid var(--ui-border)', borderRadius: '6px' },
  ignoredRow: { display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', padding: '3px 0' },
}

const STATE_COLORS = {
  succeeded: 'var(--ui-success, #3fb950)',
  failed: 'var(--ui-danger, #f85149)',
  canceled: 'var(--ui-text-secondary)',
  inProgress: 'var(--ui-warning, #d29922)',
  notStarted: 'var(--ui-text-secondary)',
  active: 'var(--ui-success, #3fb950)',
  abandoned: 'var(--ui-text-secondary)',
  draft: 'var(--ui-text-secondary)',
  merged: 'var(--ui-accent, var(--ui-text))',
  completed: 'var(--ui-success, #3fb950)',
  'To Do': 'var(--ui-text-secondary)',
  Done: 'var(--ui-success, #3fb950)',
}

function stateColor(value) {
  if (!value) return 'var(--ui-text-secondary)'
  return STATE_COLORS[value] || 'var(--ui-text-secondary)'
}

function relativeTime(iso) {
  if (!iso) return ''
  const then = new Date(iso).getTime()
  if (Number.isNaN(then)) return ''
  const seconds = Math.max(0, Math.floor((Date.now() - then) / 1000))
  if (seconds < 60) return 'agora'
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return 'há ' + minutes + ' min'
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return 'há ' + hours + ' h'
  const days = Math.floor(hours / 24)
  return 'há ' + days + ' d'
}

function Badge({ value, colorOverride }) {
  const color = colorOverride || stateColor(value)
  return jsx('span', { style: styles.badge(color), children: value || '' })
}

function EmptyState({ text, url, urlLabel }) {
  return jsxs('div', { style: styles.empty, children: [
    text + ' ',
    url
      ? jsx('span', {
          style: { color: 'var(--ui-accent)', cursor: 'pointer' },
          onClick: () => ctx_host_open(url),
          children: urlLabel || 'abrir no Azure DevOps',
        })
      : null,
  ] })
}

let _ctx = null
function ctx_host_open(url) {
  if (_ctx && _ctx.os && _ctx.os.openExternal) _ctx.os.openExternal(url)
  else if (host && host.os && host.os.openExternal) host.os.openExternal(url)
}

function Panel({ ctx }) {
  _ctx = ctx
  const [days, setDays] = useState(() => {
    try { return Number(localStorage.getItem('azure-devops.days')) || 7 } catch { return 7 }
  })
  const [activeTab, setActiveTab] = useState(() => {
    try { return localStorage.getItem('azure-devops.tab') || 'prs' } catch { return 'prs' }
  })
  const [search, setSearch] = useState('')
  const [ignored, setIgnored] = useState(() => {
    try { return JSON.parse(localStorage.getItem('azure-devops.ignored') || '[]') } catch { return [] }
  })
  const [ignoredOpen, setIgnoredOpen] = useState(false)
  const [data, setData] = useState(null)
  const [releaseData, setReleaseData] = useState(null)
  const [status, setStatus] = useState({ state: 'loading', message: null })
  const [updatedAt, setUpdatedAt] = useState(null)

  const load = useCallback(async () => {
    try {
      const payload = await ctx.rest('/overview?days=' + days)
      setData(payload)
      setStatus({ state: 'ready', message: null })
      setUpdatedAt(Date.now())
    } catch (err) {
      const message = String(err && err.message ? err.message : err)
      const notMounted = message.includes('404') || message.toLowerCase().includes('not found') || message.includes('Plugin not found')
      setStatus({
        state: 'error',
        data: null,
        message: notMounted
          ? 'O backend do painel não está montado: habilite o plugin (plugins.enabled) e faça Reload desktop plugins (⌘K). Detalhe: ' + message
          : 'O painel falhou: ' + message,
      })
    }
  }, [days])

  useEffect(() => { load() }, [days, load])

  // A rota /releases é separada: busca quando a aba fica ativa (ou o período muda).
  useEffect(() => {
    if (activeTab !== 'releases') return
    let alive = true
    ctx.rest('/releases?days=' + days)
      .then((payload) => { if (alive) setReleaseData(payload) })
      .catch(() => {})
    return () => { alive = false }
  }, [activeTab, days, ctx])

  useEffect(() => {
    const disposer = ctx.setInterval(load, POLL_MS)
    const offEvent = ctx.onEvent('plugin.' + PLUGIN_ID + '.changed', () => load())
    return () => {
      if (typeof disposer === 'function') disposer()
      if (typeof offEvent === 'function') offEvent()
    }
  }, [load])

  // Notificação nativa de build falho (dedupe por build id)
  const notifiedBuilds = useMemo(() => new Set(), [])
  useEffect(() => {
    if (!data || !data.builds) return
    for (const build of data.builds) {
      if (build.result === 'failed' && !notifiedBuilds.has(build.id)) {
        notifiedBuilds.add(build.id)
        if (ctx.os && ctx.os.notify) {
          ctx.os.notify({
            title: 'Build falhou: ' + (build.definition || ''),
            body: (build.buildNumber || '') + ' — ' + (build.status || ''),
          })
        }
      }
    }
  }, [data, ctx])

  const q = search.trim().toLowerCase()
  const match = (text) => !q || String(text || '').toLowerCase().includes(q)

  const prRows = (data?.pullRequests || [])
    .filter((pr) => match(pr.title) || match('#' + pr.id))
    .map((pr) => ({
      key: 'pr-' + pr.id,
      primary: '#' + pr.id + '  ' + (pr.title || ''),
      secondary: (pr.repository || '') + ' · ' + relativeTime(pr.createdAt),
      badge: pr.isDraft ? 'draft' : 'open',
      color: pr.isDraft ? 'var(--ui-text-secondary)' : 'var(--ui-success, #3fb950)',
      url: pr.url,
    }))
  const wiRows = (data?.workItems || [])
    .filter((wi) => match(wi.title) || match('#' + wi.id))
    .map((wi) => ({
      key: 'wi-' + wi.id,
      primary: '#' + wi.id + '  ' + (wi.title || ''),
      secondary: (wi.type || '') + ' · ' + relativeTime(wi.changed),
      badge: wi.state,
      color: stateColor(wi.state),
      url: wi.url,
    }))
  const buildRows = (data?.builds || [])
    .filter((b) => match(b.buildNumber) || match(b.definition))
    .map((b) => ({
      key: 'b-' + b.id,
      primary: (b.buildNumber || '#' + b.id) + '  ' + (b.definition || ''),
      secondary: relativeTime(b.finishedAt || b.queuedAt),
      badge: b.result || b.status,
      color: stateColor(b.result || b.status),
      url: b.url,
    }))
  const releaseRows = (releaseData?.releases || [])
    .filter((r) => match(r.name) || match(r.project))
    .map((r) => ({
      key: 'r-' + r.id,
      primary: r.name || '#' + r.id,
      secondary: (r.project || '') + ' · ' + relativeTime(r.created),
      badge: r.status,
      color: stateColor(r.status),
      url: r.url,
    }))

  const tabData = {
    prs: { rows: prRows, empty: 'Nenhum pull request aberto seu no período.' },
    wis: { rows: wiRows, empty: 'Nenhum work item atribuído a você.' },
    builds: { rows: buildRows, empty: 'Nenhum build seu no período.' },
    releases: { rows: releaseRows, empty: 'Nenhuma release no período.' },
  }
  const current = tabData[activeTab] || tabData.prs

  if (status.state === 'error') {
    return jsx('div', { style: { ...styles.page, color: 'var(--ui-text)' }, children: status.message })
  }

  const projectsSeen = new Map()
  for (const pr of data?.pullRequests || []) {
    if (pr.project && !projectsSeen.has(pr.project)) projectsSeen.set(pr.project, pr.project)
  }

  return jsxs('div', { style: styles.page, children: [
    data?.identityWarning ? jsx('div', { style: styles.warning, children: data.identityWarning }) : null,
    jsxs('div', { style: styles.bar, children: [
      PRESETS.map((preset) =>
        jsx('span', {
          key: preset.days,
          style: styles.preset(preset.days === days),
          onClick: () => setDays(preset.days),
          children: preset.label,
        }, preset.days)
      ),
      jsx('input', {
        style: styles.search,
        placeholder: 'Buscar…',
        value: search,
        onInput: (ev) => setSearch(ev.target.value),
      }),
      jsx('span', { style: styles.updated, children: updatedAt ? 'atualizado há ' + Math.max(0, Math.floor((Date.now() - updatedAt) / 1000)) + 's' : '' }),
      jsx('span', {
        style: { ...styles.updated, cursor: 'pointer' },
        onClick: () => load(),
        children: '↻',
      }),
    ]}),
    data && data.projects && Array.isArray(data.projects) && data.projects.length && ignoredOpen
      ? jsxs('div', { style: styles.ignoredZone, children: [
          jsx('div', { style: styles.sectionTitle, children: 'Projetos ignorados (não aparecem no painel)' }),
          data.projects.map((p) =>
            jsx('label', { key: p.id || p.name, style: styles.ignoredRow },
              jsx('input', {
                type: 'checkbox',
                checked: (ignored.includes(p.id) || ignored.includes(p.name) || p.ignored),
                onChange: () => {
                  const next = (ignored.includes(p.id) || ignored.includes(p.name) || p.ignored)
                    ? ignored.filter((x) => x !== p.id && x !== p.name)
                    : [...ignored, p.id]
                  setIgnored(next)
                  try { localStorage.setItem('azure-devops.ignored', JSON.stringify(next)) } catch {}
                  if (ctx.rest) {
                    ctx.rest('/settings/ignored-projects', { method: 'POST', body: { ignored_projects: next } })
                      .then(() => load())
                  }
                },
              }),
              p.name,
            )
          ),
        ] })
      : null,
    ignoredOpen
      ? jsx('div', { style: { ...styles.empty, cursor: 'pointer' }, onClick: () => setIgnoredOpen(false), children: 'fechar seletor de projetos' })
      : jsx('div', { style: { ...styles.empty, cursor: 'pointer' }, onClick: () => setIgnoredOpen(true), children: '⚙ gerenciar projetos ignorados' }),
    jsxs('div', { style: styles.tabs, children:
      TABS.map((tab) => {
        const count = {
          prs: prRows.length,
          wis: wiRows.length,
          builds: buildRows.length,
          releases: releaseRows.length,
        }[tab.id]
        return jsx('div', {
          key: tab.id,
          style: styles.tab(activeTab === tab.id),
          onClick: () => { setActiveTab(tab.id); try { localStorage.setItem('azure-devops.tab', tab.id) } catch {} },
          children: tab.label + ' (' + count + ')',
        }, tab.id)
      })
    }),
    current.rows.length === 0
      ? jsxs('div', { style: styles.empty, children: [
          current.empty,
          ' ',
          jsx('span', {
            style: { color: 'var(--ui-accent)', cursor: 'pointer' },
            onClick: () => ctx_host_open('https://dev.azure.com/'),
            children: 'abrir no Azure DevOps',
          }),
        ] })
      : jsx('div', { children: current.rows.map((row) =>
          jsx('div', {
            key: row.key,
            style: styles.row,
            onClick: row.url ? () => ctx_host_open(row.url) : undefined,
            children: [
              jsx('span', { key: 'p', style: styles.rowPrimary, children: row.primary }),
              jsx('span', { key: 's', style: styles.rowSecondary, children: row.secondary }),
              jsx(Badge, { key: 'b', value: row.badge, colorOverride: row.color }),
            ],
          }, row.key)
        ) }),
    jsx('div', { style: styles.footer, children: 'Painel somente leitura — alterações seguem pelo agente. Projetos ignorados: ' + (ignored.length || 'nenhum') + '.' }),
  ]})
}

export default {
  id: PLUGIN_ID,
  name: 'Azure DevOps',
  description: 'Panel of your own Azure DevOps activity: pull requests, work items assigned to you, your recent builds and releases, with period presets and ignored projects. Read-only; writes go through the agent.',
  defaultEnabled: true,
  register(ctx) {
    ctx.registerMany([
      { id: 'page', area: ROUTES_AREA, data: { path: PAGE_PATH }, render: () => jsx(Panel, { ctx }) },
      { id: 'nav', area: SIDEBAR_NAV_AREA, data: { path: PAGE_PATH, label: 'Azure DevOps', codicon: 'azure-devops' } },
      {
        id: 'chip',
        area: STATUSBAR_AREAS.right,
        render: () => jsx(Chip, { ctx, onOpen: () => host.navigate(PAGE_PATH) }),
      },
    ])
  },
}

function Chip({ ctx, onOpen }) {
  const [count, setCount] = useState(null)
  const load = useCallback(async () => {
    try {
      const data = await ctx.rest('/overview')
      const failed = data.builds?.filter((b) => b.result === 'failed').length || 0
      const open = data.pullRequests?.length || 0
      setCount(open + failed)
    } catch {
      setCount(null)
    }
  }, [])
  useEffect(() => {
    load()
    const disposer = ctx.setInterval(load, POLL_MS)
    const offEvent = ctx.onEvent('plugin.' + PLUGIN_ID + '.changed', () => load())
    return () => {
      if (typeof disposer === 'function') disposer()
      if (typeof offEvent === 'function') offEvent()
    }
  }, [load])
  return jsx('div', {
    style: { fontSize: '11px', color: 'var(--ui-text-secondary)', cursor: 'pointer', padding: '0 8px' },
    onClick: onOpen,
    children: count === null ? 'Azure DevOps' : 'ADO ' + count,
  })
}
