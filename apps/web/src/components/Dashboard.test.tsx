import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react'
import type { ComponentProps } from 'react'
import Dashboard from './Dashboard'
import { I18nProvider } from '../i18n'
import { ToastProvider } from './ui/Toast'

const mocks = vi.hoisted(() => ({
  mutateAsync: vi.fn(),
  saveConfigMutateAsync: vi.fn(),
  refetch: vi.fn(),
  workspaceResult: {
    current: null as unknown,
  },
  openersResult: {
    current: null as unknown,
  },
}))

function readyWorkspaceResult() {
  return {
    data: {
      status: 'ready',
      project: 'demo',
      config_path: '/tmp/demo/.cc-branch/config.yaml',
      state_path: '/tmp/demo/.cc-branch/state.yaml',
      slots: [
        {
          name: 'dev',
          runtime: 'tmux',
          status: 'running',
          session_name: 'demo-dev',
          windows: [
            {
              name: 'planner',
              agent: 'codex',
              command: 'codex',
              session_id: 'session-1234567890',
              label: 'demo/dev/planner',
              cwd: '/tmp/demo',
            },
          ],
        },
      ],
    },
    error: null,
    isLoading: false,
    isError: false,
    isFetching: false,
    refetch: mocks.refetch,
  }
}

function stoppedWorkspaceResult() {
  const result = readyWorkspaceResult()
  result.data.slots[0].status = 'stopped'
  return result
}

function terminalWorkspaceResult() {
  return {
    data: {
      status: 'ready',
      project: 'demo',
      config_path: '/tmp/demo/.cc-branch/config.yaml',
      state_path: '/tmp/demo/.cc-branch/state.yaml',
      slots: [
        {
          name: 'codex-ui',
          runtime: 'terminal',
          status: 'running',
          session_name: 'codex-ui',
          windows: [
            {
              name: 'codex-ui',
              agent: 'codex',
              command: 'codex',
              session_id: 'session-ui',
              label: 'demo/codex-ui',
              cwd: '/tmp/demo',
            },
          ],
        },
      ],
    },
    error: null,
    isLoading: false,
    isError: false,
    isFetching: false,
    refetch: mocks.refetch,
  }
}

vi.mock('../hooks', () => ({
  useWorkspace: () => mocks.workspaceResult.current,
  useOpeners: () => mocks.openersResult.current,
  useWorkspaceAction: () => ({
    mutateAsync: mocks.mutateAsync,
    isPending: false,
  }),
  useApiClient: () => ({
    getConfig: vi.fn(),
  }),
  useProfiles: () => ({
    data: [],
  }),
  useAgents: () => ({
    data: { agents: [] },
  }),
  useInitWorkspace: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
  useConfig: () => ({
    data: null,
  }),
  useSaveConfig: () => ({
    mutateAsync: mocks.saveConfigMutateAsync,
    isPending: false,
  }),
  useRelativeTime: () => 'now',
}))

function renderDashboard(props: Partial<ComponentProps<typeof Dashboard>> = {}) {
  return render(
    <I18nProvider>
      <ToastProvider>
        <Dashboard projectPath="/tmp/demo" onEditTarget={vi.fn()} {...props} />
      </ToastProvider>
    </I18nProvider>
  )
}

describe('Dashboard actions', () => {
  beforeEach(() => {
    window.localStorage.clear()
    mocks.workspaceResult.current = readyWorkspaceResult()
    mocks.openersResult.current = {
      data: {
        default: 'auto-terminal',
        openers: [
          {
            id: 'system-file-manager',
            label: 'Finder',
            kind: 'editor',
            available: true,
            capabilities: ['open_project'],
            source: 'builtin',
          },
          {
            id: 'auto-terminal',
            label: 'System Terminal',
            kind: 'terminal',
            available: true,
            capabilities: ['run_command', 'dashboard', 'attach_target'],
            source: 'builtin',
          },
          {
            id: 'vscode',
            label: 'VS Code',
            kind: 'editor',
            available: true,
            capabilities: ['open_project', 'workspace_file'],
            source: 'builtin',
          },
          {
            id: 'cursor',
            label: 'Cursor',
            kind: 'editor',
            available: false,
            capabilities: ['open_project'],
            source: 'builtin',
            reason: 'cursor CLI not found',
          },
          {
            id: 'warp',
            label: 'Warp',
            kind: 'terminal',
            available: true,
            capabilities: ['run_command', 'layout', 'dashboard', 'attach_target'],
            source: 'builtin',
          },
        ],
      },
    }
    mocks.mutateAsync.mockReset()
    mocks.mutateAsync.mockResolvedValue({ success: true, message: 'ok' })
    mocks.saveConfigMutateAsync.mockReset()
    mocks.saveConfigMutateAsync.mockResolvedValue({ success: true })
    mocks.refetch.mockReset()
  })

  it('opens the workspace dashboard from the primary toolbar button', async () => {
    renderDashboard()

    fireEvent.click(screen.getByRole('button', { name: 'Launch workspace in System Terminal' }))

    await waitFor(() => {
      expect(mocks.mutateAsync).toHaveBeenCalledWith({
        action: 'open',
        target: undefined,
        opener: 'auto-terminal',
        intent: 'workspace_dashboard',
        projectPath: '/tmp/demo',
      })
    })
  })

  it('uses the configured slot name as the dashboard tab label', () => {
    renderDashboard()

    expect(screen.getByRole('heading', { name: 'dev' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Tab 1' })).not.toBeInTheDocument()
  })

  it('opens the project directory with the system file manager', async () => {
    renderDashboard()

    fireEvent.click(screen.getByRole('button', { name: 'Open directory' }))

    await waitFor(() => {
      expect(mocks.mutateAsync).toHaveBeenCalledWith({
        action: 'open',
        target: undefined,
        opener: 'system-file-manager',
        intent: 'project_folder',
        projectPath: '/tmp/demo',
      })
    })
  })

  it('remembers the selected tool from localStorage', async () => {
    mocks.openersResult.current = {
      data: {
        default: 'auto-terminal',
        openers: [
          {
            id: 'auto-terminal',
            label: 'System Terminal',
            kind: 'terminal',
            available: true,
            capabilities: ['run_command', 'dashboard', 'attach_target'],
            source: 'builtin',
          },
          {
            id: 'warp',
            label: 'Warp',
            kind: 'terminal',
            available: true,
            capabilities: ['run_command', 'dashboard', 'attach_target', 'layout'],
            source: 'builtin',
          },
        ],
      },
    }
    window.localStorage.setItem('cc-branch.open.tool./tmp/demo', 'warp')
    renderDashboard()

    fireEvent.click(screen.getByRole('button', { name: 'Launch workspace in Warp' }))

    await waitFor(() => {
      expect(mocks.mutateAsync).toHaveBeenCalledWith({
        action: 'open',
        target: undefined,
        opener: 'warp',
        intent: 'workspace_dashboard',
        projectPath: '/tmp/demo',
      })
    })
  })

  it('lists editor tools and opens them as workspaces', async () => {
    renderDashboard()

    fireEvent.click(screen.getByRole('button', { name: 'Tool: System Terminal' }))
    fireEvent.click(screen.getByRole('option', { name: 'VS Code' }))
    fireEvent.click(screen.getByRole('button', { name: 'Launch workspace in VS Code' }))

    await waitFor(() => {
      expect(mocks.mutateAsync).toHaveBeenCalledWith({
        action: 'open',
        target: undefined,
        opener: 'vscode',
        intent: 'workspace_dashboard',
        projectPath: '/tmp/demo',
      })
    })
  })

  it('always uses the system file manager for project directory opens', async () => {
    mocks.openersResult.current = {
      data: {
        default: 'auto-terminal',
        openers: [
          {
            id: 'system-file-manager',
            label: 'Finder',
            kind: 'editor',
            available: true,
            capabilities: ['open_project'],
            source: 'builtin',
          },
          {
            id: 'auto-terminal',
            label: 'System Terminal',
            kind: 'terminal',
            available: true,
            capabilities: ['run_command', 'dashboard', 'attach_target'],
            source: 'builtin',
          },
          {
            id: 'vscode',
            label: 'VS Code',
            kind: 'editor',
            available: true,
            capabilities: ['open_project', 'workspace_file'],
            source: 'builtin',
          },
          {
            id: 'warp',
            label: 'Warp',
            kind: 'terminal',
            available: true,
            capabilities: ['run_command', 'dashboard', 'attach_target', 'open_project', 'layout'],
            source: 'builtin',
          },
        ],
      },
    }
    renderDashboard()

    fireEvent.click(screen.getByRole('button', { name: 'Tool: System Terminal' }))
    fireEvent.click(screen.getByRole('option', { name: 'Warp' }))
    fireEvent.click(screen.getByRole('button', { name: 'Open directory' }))

    await waitFor(() => {
      expect(mocks.mutateAsync).toHaveBeenCalledWith({
        action: 'open',
        target: undefined,
        opener: 'system-file-manager',
        intent: 'project_folder',
        projectPath: '/tmp/demo',
      })
    })
  })

  it('opens a Cursor project without presenting a generated workspace file', async () => {
    mocks.openersResult.current = {
      data: {
        default: 'auto-terminal',
        openers: [
          {
            id: 'auto-terminal',
            label: 'System Terminal',
            kind: 'terminal',
            available: true,
            capabilities: ['run_command', 'dashboard', 'attach_target'],
            source: 'builtin',
          },
          {
            id: 'cursor',
            label: 'Cursor',
            kind: 'editor',
            available: true,
            capabilities: ['open_project', 'workspace_file'],
            source: 'builtin',
          },
        ],
      },
    }
    renderDashboard()

    fireEvent.click(screen.getByRole('button', { name: 'Tool: System Terminal' }))
    fireEvent.click(screen.getByRole('option', { name: 'Cursor' }))
    fireEvent.click(screen.getByRole('button', { name: 'Launch workspace in Cursor' }))

    await waitFor(() => {
      expect(mocks.mutateAsync).toHaveBeenCalledWith({
        action: 'open',
        target: undefined,
        opener: 'cursor',
        intent: 'workspace_dashboard',
        projectPath: '/tmp/demo',
      })
    })
  })

  it('uses the selected opener for slot opens', async () => {
    renderDashboard()

    fireEvent.click(screen.getByRole('button', { name: 'Tool: System Terminal' }))
    fireEvent.click(screen.getByRole('option', { name: 'VS Code' }))
    fireEvent.click(screen.getByRole('button', { name: 'Open dev' }))

    await waitFor(() => {
      expect(mocks.mutateAsync).toHaveBeenCalledWith({
        action: 'open',
        target: 'dev',
        opener: 'vscode',
        intent: 'attach_target',
        projectPath: '/tmp/demo',
      })
    })
  })

  it('keeps background lifecycle actions out of the header', () => {
    renderDashboard()

    expect(screen.getByRole('button', { name: 'Launch workspace in System Terminal' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Start in background' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Restart' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Stop workspace' })).not.toBeInTheDocument()
  })

  it('uses the selected opener for workspace launch', async () => {
    renderDashboard()

    fireEvent.click(screen.getByRole('button', { name: 'Tool: System Terminal' }))
    fireEvent.click(screen.getByRole('option', { name: 'Warp' }))
    fireEvent.click(screen.getByRole('button', { name: 'Launch workspace in Warp' }))

    await waitFor(() => {
      expect(mocks.mutateAsync).toHaveBeenCalledWith({
        action: 'open',
        target: undefined,
        opener: 'warp',
        intent: 'workspace_dashboard',
        projectPath: '/tmp/demo',
      })
    })
  })

  it('does not expose restart when no tmux slots are running', () => {
    mocks.workspaceResult.current = stoppedWorkspaceResult()

    renderDashboard()

    expect(screen.getByRole('button', { name: 'Launch workspace in System Terminal' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Start in background' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Restart' })).not.toBeInTheDocument()
  })

  it('keeps workspace status stable during background polling', () => {
    const result = readyWorkspaceResult()
    result.isFetching = true
    mocks.workspaceResult.current = result

    renderDashboard()

    expect(screen.getByText('Active')).toBeInTheDocument()
    expect(screen.queryByText('Checked now')).not.toBeInTheDocument()
    expect(screen.queryByText('Refreshing')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Refresh status' })).not.toBeDisabled()
  })

  it('shows agent windows with an existing session as bound', () => {
    renderDashboard()

    expect(screen.getByText(/Bound session-/)).toBeInTheDocument()
  })

  it('shows agent windows without a session as auto-created-on-start', () => {
    const result = readyWorkspaceResult()
    ;(result.data.slots[0].windows[0] as Record<string, unknown>).session_id = null
    mocks.workspaceResult.current = result

    renderDashboard()

    expect(screen.getByText(/Will create and remember a session/)).toBeInTheDocument()
  })

  it('does not show a session badge for command-only windows', () => {
    const result = readyWorkspaceResult()
    ;(result.data.slots[0].windows[0] as Record<string, unknown>).agent = null
    ;(result.data.slots[0].windows[0] as Record<string, unknown>).session_id = null
    result.data.slots[0].windows[0].command = 'npm test'
    mocks.workspaceResult.current = result

    renderDashboard()

    expect(screen.queryByText(/Bound /)).not.toBeInTheDocument()
    expect(screen.queryByText('Will create and remember a session')).not.toBeInTheDocument()
  })

  it('flattens direct-layout tabs into one task card without a repeated child pane', async () => {
    mocks.workspaceResult.current = terminalWorkspaceResult()

    renderDashboard()

    expect(screen.getByLabelText('Codex')).toBeInTheDocument()
    expect(screen.getByText('Bound session-ui')).toBeInTheDocument()
    expect(screen.queryByText('1 pane')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Open codex-ui:codex-ui' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Edit pane codex-ui:codex-ui' })).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Open codex-ui' }))

    await waitFor(() => {
      expect(mocks.mutateAsync).toHaveBeenCalledWith({
        action: 'open',
        target: 'codex-ui',
        opener: 'auto-terminal',
        intent: 'attach_target',
        projectPath: '/tmp/demo',
      })
    })
  })

  it('renders multiple terminal panes inside one dashboard tab', async () => {
    const result = terminalWorkspaceResult()
    result.data.slots[0].name = 'codex-spec'
    ;(result.data.slots[0] as Record<string, unknown>).layout = 'horizontal'
    result.data.slots[0].windows = [
      {
        name: 'dev-backend',
        agent: 'codex',
        command: 'codex',
        session_id: 'session-backend',
        label: 'demo/codex-spec/dev-backend',
        cwd: '/tmp/demo',
      },
      {
        name: 'pane-3',
        agent: 'claude',
        command: 'claude',
        session_id: '',
        label: 'demo/codex-spec/pane-3',
        cwd: '/tmp/demo',
      },
    ]
    mocks.workspaceResult.current = result

    renderDashboard()

    expect(screen.getByRole('heading', { name: 'codex-spec' })).toBeInTheDocument()
    expect(screen.getByText('2 terminals')).toBeInTheDocument()
    expect(screen.getByText('dev-backend')).toBeInTheDocument()
    expect(screen.getByText('pane-3')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Open codex-spec:dev-backend' }))

    await waitFor(() => {
      expect(mocks.mutateAsync).toHaveBeenCalledWith({
        action: 'open',
        target: 'codex-spec:dev-backend',
        opener: 'auto-terminal',
        intent: 'attach_target',
        projectPath: '/tmp/demo',
      })
    })
  })

  it('expands only tmux-backed tabs and uses natural child pane summaries', () => {
    const result = readyWorkspaceResult()
    result.data.slots[0].windows.push({
      name: 'reviewer',
      agent: 'codex',
      command: 'codex',
      session_id: '',
      label: 'demo/dev/reviewer',
      cwd: '/tmp/demo',
    })
    mocks.workspaceResult.current = result

    renderDashboard()

    expect(screen.getByText('tmux session')).toBeInTheDocument()
    expect(screen.getByText('Tmux windows')).toBeInTheDocument()
    expect(screen.getAllByText('2 tmux windows').length).toBeGreaterThan(0)
    expect(screen.getAllByLabelText('Codex').length).toBeGreaterThanOrEqual(2)
    expect(screen.getByText(/Bound session-/)).toBeInTheDocument()
    expect(screen.getByText('Will create and remember a session')).toBeInTheDocument()
    expect(screen.queryByText('tmux pane group')).not.toBeInTheDocument()
  })

  it('uses edit actions instead of copy buttons for tabs and panes', () => {
    const onEditTarget = vi.fn()

    renderDashboard({ onEditTarget })

    expect(screen.queryByRole('button', { name: 'Copy target dev' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Copy attach command dev:planner' })).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Edit tab dev' }))
    fireEvent.click(screen.getByRole('button', { name: 'Edit pane dev:planner' }))

    expect(onEditTarget).toHaveBeenCalledWith({ slotName: 'dev' })
    expect(onEditTarget).toHaveBeenCalledWith({ slotName: 'dev', windowName: 'planner' })
  })

  it('treats not-yet-started tmux panes as normal ready state', () => {
    const result = stoppedWorkspaceResult()
    ;(result.data as Record<string, unknown>).runtime_sync = {
      summary: { current: 0, changed: 0, missing: 2, extra: 0, orphaned: 0, untracked: 0, external: 0 },
      slots: [],
      orphaned_state: [],
      historical_sessions: [],
    }
    mocks.workspaceResult.current = result

    renderDashboard()

    expect(screen.getByText('Runtime drift')).toBeInTheDocument()
    expect(screen.getByText('0')).toBeInTheDocument()
    expect(screen.queryByText(/runtime update/)).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Sync item' })).not.toBeInTheDocument()
    expect(screen.getByText('not started')).toBeInTheDocument()
    expect(screen.queryByText(/do not match the current config/)).not.toBeInTheDocument()
  })

  it('labels missing pane status as not running', () => {
    const result = readyWorkspaceResult()
    ;(result.data.slots[0].windows[0] as Record<string, unknown>).sync_status = 'missing'
    mocks.workspaceResult.current = result

    renderDashboard()

    expect(screen.getByText('not running')).toBeInTheDocument()
  })

  it('explains changed running panes separately from missing panes', () => {
    const result = readyWorkspaceResult()
    ;(result.data as Record<string, unknown>).runtime_sync = {
      summary: { current: 0, changed: 1, missing: 2, extra: 0, orphaned: 0, untracked: 0, external: 0 },
      slots: [],
      orphaned_state: [],
      historical_sessions: [],
    }
    mocks.workspaceResult.current = result

    renderDashboard()

    expect(screen.getByText('1 running tmux-managed pane(s) use an older launch command.')).toBeInTheDocument()
  })

  it('shows every runtime sync notice instead of hiding mixed states', () => {
    const result = readyWorkspaceResult()
    ;(result.data as Record<string, unknown>).runtime_sync = {
      summary: { current: 0, changed: 1, missing: 2, extra: 3, orphaned: 0, untracked: 4, external: 0 },
      slots: [],
      orphaned_state: [],
      historical_sessions: [],
    }
    mocks.workspaceResult.current = result

    renderDashboard()

    expect(screen.getByText('1 running tmux-managed pane(s) use an older launch command.')).toBeInTheDocument()
    expect(screen.getByText('4 running pane(s) were not launched from the current config.')).toBeInTheDocument()
    expect(screen.getByText('3 extra tmux-managed pane(s) are running outside the config.')).toBeInTheDocument()
  })

  it('summarizes extra tmux panes without exposing a destructive header action', () => {
    const result = readyWorkspaceResult()
    ;(result.data as Record<string, unknown>).runtime_sync = {
      summary: { current: 0, changed: 0, missing: 0, extra: 2, orphaned: 0, untracked: 0, external: 0 },
      slots: [],
      orphaned_state: [],
      historical_sessions: [],
    }
    mocks.workspaceResult.current = result

    renderDashboard()

    expect(document.body.textContent).toContain('2 extra tmux-managed pane(s) are running outside the config.')
    expect(screen.queryByRole('button', { name: 'Stop extra panes' })).not.toBeInTheDocument()
  })

  it('warns and disables tmux lifecycle actions when tmux is unavailable locally', () => {
    const result = readyWorkspaceResult()
    ;(result.data as Record<string, unknown>).runtimes = {
      tmux: { available: false, reason: 'tmux was not found on PATH' },
      terminal: { available: true },
    }
    ;(result.data as Record<string, unknown>).runtime_sync = {
      summary: { current: 0, changed: 0, missing: 1, extra: 0, orphaned: 0, untracked: 0, external: 0 },
      slots: [],
      orphaned_state: [],
      historical_sessions: [],
    }
    mocks.workspaceResult.current = result

    renderDashboard()

    expect(screen.getByText('tmux is not available on this machine. Tmux-managed panes cannot start here.')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Sync runtime' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Start in background' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Restart' })).not.toBeInTheDocument()
  })

  it('opens a running slot in a terminal', async () => {
    renderDashboard()

    fireEvent.click(screen.getByRole('button', { name: 'Open dev' }))

    await waitFor(() => {
      expect(mocks.mutateAsync).toHaveBeenCalledWith({
        action: 'open',
        target: 'dev',
        opener: 'auto-terminal',
        intent: 'attach_target',
        projectPath: '/tmp/demo',
      })
    })
  })

  it('opens a specific window in a terminal', async () => {
    mocks.openersResult.current = {
      data: {
        default: 'auto-terminal',
        openers: [
          {
            id: 'auto-terminal',
            label: 'System Terminal',
            kind: 'terminal',
            available: true,
            capabilities: ['run_command', 'dashboard', 'attach_target'],
            source: 'builtin',
          },
          {
            id: 'warp',
            label: 'Warp',
            kind: 'terminal',
            available: true,
            capabilities: ['run_command', 'dashboard', 'attach_target', 'open_project', 'layout'],
            source: 'builtin',
          },
        ],
      },
    }
    renderDashboard()

    fireEvent.click(screen.getByRole('button', { name: 'Tool: System Terminal' }))
    fireEvent.click(screen.getByRole('option', { name: 'Warp' }))
    fireEvent.click(screen.getByRole('button', { name: 'Open dev:planner' }))

    await waitFor(() => {
      expect(mocks.mutateAsync).toHaveBeenCalledWith({
        action: 'open',
        target: 'dev:planner',
        opener: 'warp',
        intent: 'attach_target',
        projectPath: '/tmp/demo',
      })
    })
  })

  it('opens a stopped slot in a terminal instead of hiding the terminal side effect behind launch copy', async () => {
    mocks.workspaceResult.current = stoppedWorkspaceResult()
    renderDashboard()

    fireEvent.click(screen.getByRole('button', { name: 'Open dev' }))

    await waitFor(() => {
      expect(mocks.mutateAsync).toHaveBeenCalledWith({
        action: 'open',
        target: 'dev',
        opener: 'auto-terminal',
        intent: 'attach_target',
        projectPath: '/tmp/demo',
      })
    })
  })

  it('does not expose per-tab lifecycle buttons on the tab card', () => {
    mocks.openersResult.current = {
      data: {
        default: 'auto-terminal',
        openers: [
          {
            id: 'auto-terminal',
            label: 'System Terminal',
            kind: 'terminal',
            available: true,
            capabilities: ['run_command', 'dashboard', 'attach_target'],
            source: 'builtin',
          },
          {
            id: 'warp',
            label: 'Warp',
            kind: 'terminal',
            available: true,
            capabilities: ['run_command', 'dashboard', 'attach_target', 'open_project', 'layout'],
            source: 'builtin',
          },
        ],
      },
    }
    renderDashboard()

    expect(screen.getByRole('button', { name: 'Open dev' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Edit tab dev' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Restart dev' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Stop dev' })).not.toBeInTheDocument()
  })

  it('does not expose workspace stop in the dashboard header', () => {
    renderDashboard()

    expect(screen.queryByRole('button', { name: 'Stop workspace' })).not.toBeInTheDocument()
  })

  it('renders web-first setup when the backend reports needs_init', () => {
    mocks.workspaceResult.current = {
      data: {
        status: 'needs_init',
        project_path: '/tmp/demo',
        config_path: '/tmp/demo/.cc-branch/config.yaml',
        state_path: '/tmp/demo/.cc-branch/state.yaml',
        project_name: 'demo',
        slots: [],
      },
      error: null,
      isLoading: false,
      isError: false,
      isFetching: false,
      refetch: mocks.refetch,
    }

    renderDashboard()

    expect(screen.getByText('Create a workspace for demo.')).toBeInTheDocument()
    expect(screen.getByText('No workspace yet')).toBeInTheDocument()
    expect(screen.getByText('Workspace → Tab → Pane')).toBeInTheDocument()
    expect(screen.queryByText('Target config')).not.toBeInTheDocument()
    expect(screen.queryByText('No auto launch')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Create workspace' })).toBeInTheDocument()
    expect(screen.queryByText(/Run cc-branch init/)).not.toBeInTheDocument()
    expect(screen.queryByText('No slots configured')).not.toBeInTheDocument()
  })

  it('opens the setup wizard with profile, agent, and target context', () => {
    mocks.workspaceResult.current = {
      data: {
        status: 'needs_init',
        project_path: '/tmp/demo',
        config_path: '/tmp/demo/.cc-branch/config.yaml',
        state_path: '/tmp/demo/.cc-branch/state.yaml',
        project_name: 'demo',
        slots: [],
      },
      error: null,
      isLoading: false,
      isError: false,
      isFetching: false,
      refetch: mocks.refetch,
    }

    renderDashboard()
    fireEvent.click(screen.getByRole('button', { name: 'Create workspace' }))

    const dialog = screen.getByRole('dialog', { name: 'Create workspace' })
    expect(dialog).toBeInTheDocument()
    expect(within(dialog).getByText('Development')).toBeInTheDocument()
    expect(within(dialog).getByText('Workspace')).toBeInTheDocument()
    expect(within(dialog).getAllByText('Tab').length).toBeGreaterThan(0)
    expect(within(dialog).getAllByText('Pane').length).toBeGreaterThan(0)
    expect(within(dialog).getByRole('button', { name: 'Create workspace' })).toBeInTheDocument()
  })

  it('keeps setup wizard preset selection, preview, and saved YAML in sync', async () => {
    mocks.workspaceResult.current = {
      data: {
        status: 'needs_init',
        project_path: '/tmp/demo',
        config_path: '/tmp/demo/.cc-branch/config.yaml',
        state_path: '/tmp/demo/.cc-branch/state.yaml',
        project_name: 'demo',
        slots: [],
      },
      error: null,
      isLoading: false,
      isError: false,
      isFetching: false,
      refetch: mocks.refetch,
    }

    renderDashboard()
    fireEvent.click(screen.getByRole('button', { name: 'Create workspace' }))
    const dialog = screen.getByRole('dialog', { name: 'Create workspace' })

    expect(within(dialog).getByDisplayValue('development')).toBeInTheDocument()
    expect(within(dialog).getByDisplayValue('frontend')).toBeInTheDocument()
    expect(within(dialog).getByDisplayValue('algorithm')).toBeInTheDocument()

    fireEvent.click(within(dialog).getByRole('button', { name: /Design/ }))
    expect(within(dialog).getByDisplayValue('product')).toBeInTheDocument()
    expect(within(dialog).getByDisplayValue('directions')).toBeInTheDocument()
    expect(within(dialog).queryByDisplayValue('algorithm')).not.toBeInTheDocument()

    fireEvent.click(within(dialog).getByRole('button', { name: /Minimal/ }))
    expect(within(dialog).getByDisplayValue('main')).toBeInTheDocument()
    expect(within(dialog).getByDisplayValue('agent')).toBeInTheDocument()
    expect(within(dialog).queryByDisplayValue('directions')).not.toBeInTheDocument()

    fireEvent.click(within(dialog).getByRole('button', { name: 'Create workspace' }))

    await waitFor(() => {
      expect(mocks.saveConfigMutateAsync).toHaveBeenCalled()
    })
    const saved = mocks.saveConfigMutateAsync.mock.calls[0][0]
    expect(saved.content).toContain('name: "main"')
    expect(saved.content).toContain('name: "agent"')
    expect(saved.content).not.toContain('name: "directions"')
    expect(saved.scope).toEqual({
      projectPath: '/tmp/demo',
      configPath: undefined,
    })
  })
})
