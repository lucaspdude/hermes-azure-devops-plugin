import { jsx, jsxs } from 'react/jsx-runtime'
import {
  ROUTES_AREA,
  SIDEBAR_NAV_AREA,
  STATUSBAR_AREAS,
  host,
} from '@hermes/plugin-sdk'

const PLUGIN_ID = 'azure-devops'
const PAGE_PATH = '/azure-devops'
const POLL_MS = 15000

const e = jsx
const section = (title, rows, emptyText) =>
  jsxs('div', {
    style: { marginBottom: '16px' },
    children: [
      jsx('div', {
        style: {
          fontSize: '11px',
          fontWeight: 600,
          color: 'var(--ui-text-secondary)',
          textTransform: 'uppercase',
          letterSpacing: '0.04em',
          marginBottom: '6px',
        },
        children: title,
      }),
      rows.length === 0
        ? jsx('div', { style: { color: 'var(--ui-text-secondary)', fontSize: '12px' }, children: emptyText })
        : jsx('div', { children: rows }),
    ],
  })

const row = (primary, secondary, href) =>
  jsx(
    'div',
    {
      style: {
        display: 'flex',
        justifyContent: 'space-between',
        gap: '8px',
        padding: '4px 0',
        fontSize: '13px',
        cursor: href ? 'pointer' : 'default',
      },
      onClick: () => {
        if (href && host?.openUrl) host.openUrl(href)
      },
    },
    jsx('span', { style: { overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }, children: primary }),
    jsx('span', { style: { color: 'var(--ui-text-secondary)', flexShrink: 0 }, children: secondary }),
  )

const Panel = (props) => {
  const state = props.state
  if (state.status === 'error') {
    return jsx('div', { style: { padding: '16px', color: 'var(--ui-danger, var(--ui-text))' }, children: state.message })
  }
  if (state.status === 'loading') {
    return jsx('div', { style: { padding: '16px', color: 'var(--ui-text-secondary)' }, children: 'Loading your Azure DevOps activity…' })
  }
  const data = state.data || {}
  const prs = data.pullRequests || []
  const wis = data.workItems || []
  const builds = data.builds || []
  return jsxs('div', {
    style: { padding: '16px', overflowY: 'auto', height: '100%', boxSizing: 'border-box' },
    children: [
      data.identityWarning
        ? jsx('div', {
            style: {
              padding: '8px',
              marginBottom: '12px',
              border: '1px solid var(--ui-warning, var(--ui-border))',
              borderRadius: '6px',
              fontSize: '12px',
            },
            children: data.identityWarning,
          })
        : null,
      section(
        'Pull requests',
        prs.map((pr) => row('#' + pr.id + '  ' + (pr.title || ''), (pr.repository || '') + (pr.isDraft ? ' (draft)' : ''), pr.url)),
        'No open pull request of yours.',
      ),
      section(
        'Work items assigned to you',
        wis.map((wi) => row('#' + wi.id + '  ' + (wi.title || ''), wi.state || '', null)),
        'Nothing assigned to you.',
      ),
      section(
        'Your recent builds',
        builds.map((b) => row((b.buildNumber || '#' + b.id) + '  ' + (b.definition || ''), b.result || b.status || '', b.url)),
        'No recent build of yours.',
      ),
      jsx('div', {
        style: { color: 'var(--ui-text-secondary)', fontSize: '11px', marginTop: '8px' },
        children: 'Read-only panel — changes go through the agent.',
      }),
    ],
  })
}

export default {
  id: PLUGIN_ID,
  name: 'Azure DevOps',
  description: 'Panel of your own Azure DevOps activity: pull requests, work items assigned to you and your recent builds. Read-only; writes go through the agent.',
  defaultEnabled: true,
  register(ctx) {
    const state = { status: 'loading', data: null, message: null }

    const load = async () => {
      try {
        const data = await ctx.rest('/overview')
        state.status = 'ready'
        state.data = data
        state.message = null
      } catch (err) {
        const message = String(err && err.message ? err.message : err)
        state.status = 'error'
        state.message = message.includes('404') || message.includes('not mounted')
          ? 'The Azure DevOps panel backend is not mounted: enable the plugin (plugins.enabled) and reload the desktop plugins. ' + message
          : 'The panel failed: ' + message
      }
      if (props_rerender) props_rerender()
    }

    let props_rerender = null
    let timer = null

    ctx.registerMany([
      {
        id: 'page',
        area: ROUTES_AREA,
        data: { path: PAGE_PATH },
        render: () => {
          if (timer === null) {
            load()
            timer = ctx.setInterval(load, POLL_MS)
          }
          props_rerender = () => {} // the host re-renders on state.set
          return jsx(Panel, { state })
        },
      },
      {
        id: 'nav',
        area: SIDEBAR_NAV_AREA,
        data: { path: PAGE_PATH, label: 'Azure DevOps', codicon: 'azure-devops' },
      },
      {
        id: 'chip',
        area: STATUSBAR_AREAS.right,
        render: () =>
          jsx(
            'div',
            {
              style: { fontSize: '11px', color: 'var(--ui-text-secondary)', cursor: 'pointer' },
              onClick: () => host?.navigate?.(PAGE_PATH),
              children: 'Azure DevOps',
            },
          ),
      },
    ])

    ctx.onEvent('plugin.' + PLUGIN_ID + '.changed', () => {
      load()
    })

    ctx.onDispose(() => {
      if (timer !== null) {
        ctx.clearInterval(timer)
        timer = null
      }
    })
  },
}
