import { useState, useEffect, useCallback } from 'react'
import { jsx, jsxs } from 'react/jsx-runtime'
import { ROUTES_AREA, SIDEBAR_NAV_AREA, STATUSBAR_AREAS, host } from '@hermes/plugin-sdk'

const PLUGIN_ID = 'azure-devops'
const PAGE_PATH = '/azure-devops'
const POLL_MS = 15000

const styles = {
  page: { padding: '16px', overflowY: 'auto', height: '100%', boxSizing: 'border-box' },
  sectionTitle: {
    fontSize: '11px',
    fontWeight: 600,
    color: 'var(--ui-text-secondary)',
    textTransform: 'uppercase',
    letterSpacing: '0.04em',
    margin: '12px 0 6px',
  },
  empty: { color: 'var(--ui-text-secondary)', fontSize: '12px', padding: '2px 0' },
  row: {
    display: 'flex',
    justifyContent: 'space-between',
    gap: '8px',
    padding: '4px 0',
    fontSize: '13px',
  },
  rowPrimary: { overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' },
  rowSecondary: { color: 'var(--ui-text-secondary)', flexShrink: 0 },
  warning: {
    padding: '8px',
    marginBottom: '12px',
    border: '1px solid var(--ui-warning, var(--ui-border))',
    borderRadius: '6px',
    fontSize: '12px',
  },
  footer: { color: 'var(--ui-text-secondary)', fontSize: '11px', marginTop: '8px' },
}

function Section({ title, rows, emptyText }) {
  return jsxs('div', {
    children: [
      jsx('div', { style: styles.sectionTitle, children: title }),
      rows.length === 0
        ? jsx('div', { style: styles.empty, children: emptyText })
        : jsxs('div', {
            children: rows.map((r, i) =>
              jsx(
                'div',
                {
                  style: styles.row,
                  onClick: r.href ? () => host?.os?.openExternal?.(r.href) : undefined,
                  children: [
                    jsx('span', { key: 'p', style: styles.rowPrimary, children: r.primary }),
                    jsx('span', { key: 's', style: styles.rowSecondary, children: r.secondary }),
                  ],
                },
                String(i),
              ),
            ),
          }),
    ],
  })
}

function Panel({ ctx }) {
  const [state, setState] = useState({ status: 'loading', data: null, message: null })

  const load = useCallback(async () => {
    try {
      const data = await ctx.rest('/overview')
      setState({ status: 'ready', data, message: null })
    } catch (err) {
      const message = String(err && err.message ? err.message : err)
      const notMounted = message.includes('404') || message.toLowerCase().includes('not found')
      setState({
        status: 'error',
        data: null,
        message: notMounted
          ? 'The panel backend is not mounted: enable the plugin (plugins.enabled), then Reload desktop plugins (⌘K). (' + message + ')'
          : 'The panel failed: ' + message,
      })
    }
  }, [])

  useEffect(() => {
    load()
    const disposer = ctx.setInterval(load, POLL_MS)
    const offEvent = ctx.onEvent('plugin.' + PLUGIN_ID + '.changed', () => {
      load()
    })
    return () => {
      if (typeof disposer === 'function') disposer()
      if (typeof offEvent === 'function') offEvent()
    }
  }, [load])

  if (state.status === 'error') {
    return jsx('div', { style: { ...styles.page, color: 'var(--ui-text)' }, children: state.message })
  }
  const data = state.data || {}
  const prs = data.pullRequests || []
  const wis = data.workItems || []
  const builds = data.builds || []
  return jsxs('div', {
    style: styles.page,
    children: [
      data.identityWarning ? jsx('div', { style: styles.warning, children: data.identityWarning }) : null,
      jsx(Section, {
        title: 'Pull requests',
        rows: prs.map((pr) => ({
          primary: '#' + pr.id + '  ' + (pr.title || ''),
          secondary: (pr.repository || '') + (pr.isDraft ? ' (draft)' : ''),
          href: pr.url,
        })),
        emptyText: 'No open pull request of yours.',
      }),
      jsx(Section, {
        title: 'Work items assigned to you',
        rows: wis.map((wi) => ({ primary: '#' + wi.id + '  ' + (wi.title || ''), secondary: wi.state || '' })),
        emptyText: 'Nothing assigned to you.',
      }),
      jsx(Section, {
        title: 'Your recent builds',
        rows: builds.map((b) => ({
          primary: (b.buildNumber || '#' + b.id) + '  ' + (b.definition || ''),
          secondary: b.result || b.status || '',
          href: b.url,
        })),
        emptyText: 'No recent build of yours.',
      }),
      jsx('div', { style: styles.footer, children: 'Read-only panel — changes go through the agent.' }),
    ],
  })
}

function Chip({ ctx, onOpen }) {
  const [count, setCount] = useState(null)
  const load = useCallback(async () => {
    try {
      const data = await ctx.rest('/overview')
      const n = (data.pullRequests?.length || 0) + (data.builds?.filter((b) => b.result === 'failed').length || 0)
      setCount(n)
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

export default {
  id: PLUGIN_ID,
  name: 'Azure DevOps',
  description: 'Panel of your own Azure DevOps activity: pull requests, work items assigned to you and your recent builds. Read-only; writes go through the agent.',
  defaultEnabled: true,
  register(ctx) {
    ctx.registerMany([
      {
        id: 'page',
        area: ROUTES_AREA,
        data: { path: PAGE_PATH },
        render: () => jsx(Panel, { ctx }),
      },
      {
        id: 'nav',
        area: SIDEBAR_NAV_AREA,
        data: { path: PAGE_PATH, label: 'Azure DevOps', codicon: 'azure-devops' },
      },
      {
        id: 'chip',
        area: STATUSBAR_AREAS.right,
        render: () => jsx(Chip, { ctx, onOpen: () => host?.navigate?.(PAGE_PATH) }),
      },
    ])
  },
}
