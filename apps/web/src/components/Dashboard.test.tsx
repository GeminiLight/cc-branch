import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import type { ComponentProps } from 'react'
import Dashboard from './Dashboard'
import { I18nProvider } from '../i18n'
import { ToastProvider } from './ui/Toast'

const mocks = vi.hoisted(() => ({
  mutateAsync: vi.fn(),
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
    mutateAsync: vi.fn(),
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

    expect(screen.getByText(/Session bound/)).toBeInTheDocument()
  })

  it('shows agent windows without a session as new-session-on-start', () => {
    const result = readyWorkspaceResult()
    ;(result.data.slots[0].windows[0] as Record<string, unknown>).session_id = null
    mocks.workspaceResult.current = result

    renderDashboard()

    expect(screen.getByText(/New session on start/)).toBeInTheDocument()
  })

  it('does not show a session badge for command-only windows', () => {
    const result = readyWorkspaceResult()
    ;(result.data.slots[0].windows[0] as Record<string, unknown>).agent = null
    ;(result.data.slots[0].windows[0] as Record<string, unknown>).session_id = null
    result.data.slots[0].windows[0].command = 'npm test'
    mocks.workspaceResult.current = result

    renderDashboard()

    expect(screen.queryByText('Session bound')).not.toBeInTheDocument()
    expect(screen.queryByText('New session on start')).not.toBeInTheDocument()
  })

  it('flattens terminal runtime slots into one task card without a repeated child window', async () => {
    mocks.workspaceResult.current = terminalWorkspaceResult()

    renderDashboard()

    expect(screen.getByLabelText('Codex')).toBeInTheDocument()
    expect(screen.getByText('Session bound')).toBeInTheDocument()
    expect(screen.queryByText('1 window')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Open codex-ui:codex-ui' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Edit window codex-ui:codex-ui' })).not.toBeInTheDocument()

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

  it('expands only tmux slots and uses natural child window summaries', () => {
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
    expect(screen.getAllByText('2 windows').length).toBeGreaterThan(0)
    expect(screen.getAllByLabelText('Codex').length).toBeGreaterThanOrEqual(2)
    expect(screen.getByText('Session bound')).toBeInTheDocument()
    expect(screen.getByText('New session on start')).toBeInTheDocument()
    expect(screen.queryByText('tmux window group')).not.toBeInTheDocument()
  })

  it('uses edit actions instead of copy buttons for slots and windows', () => {
    const onEditTarget = vi.fn()

    renderDashboard({ onEditTarget })

    expect(screen.queryByRole('button', { name: 'Copy target dev' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Copy attach command dev:planner' })).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Edit slot dev' }))
    fireEvent.click(screen.getByRole('button', { name: 'Edit window dev:planner' }))

    expect(onEditTarget).toHaveBeenCalledWith({ slotName: 'dev' })
    expect(onEditTarget).toHaveBeenCalledWith({ slotName: 'dev', windowName: 'planner' })
  })

  it('explains missing tmux windows as not running, not config drift', () => {
    const result = readyWorkspaceResult()
    ;(result.data as Record<string, unknown>).runtime_sync = {
      summary: { current: 0, changed: 0, missing: 2, extra: 0, orphaned: 0, untracked: 0, external: 0 },
      slots: [],
      orphaned_state: [],
      historical_sessions: [],
    }
    mocks.workspaceResult.current = result

    renderDashboard()

    expect(screen.getByText('2 configured tmux window(s) are not running.')).toBeInTheDocument()
    expect(screen.queryByText(/do not match the current config/)).not.toBeInTheDocument()
  })

  it('labels missing window status as not running', () => {
    const result = readyWorkspaceResult()
    ;(result.data.slots[0].windows[0] as Record<string, unknown>).sync_status = 'missing'
    mocks.workspaceResult.current = result

    renderDashboard()

    expect(screen.getByText('not running')).toBeInTheDocument()
  })

  it('explains changed running windows separately from missing windows', () => {
    const result = readyWorkspaceResult()
    ;(result.data as Record<string, unknown>).runtime_sync = {
      summary: { current: 0, changed: 1, missing: 2, extra: 0, orphaned: 0, untracked: 0, external: 0 },
      slots: [],
      orphaned_state: [],
      historical_sessions: [],
    }
    mocks.workspaceResult.current = result

    renderDashboard()

    expect(screen.getByText('1 running tmux window(s) use an older launch command.')).toBeInTheDocument()
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

    expect(screen.getByText('1 running tmux window(s) use an older launch command.')).toBeInTheDocument()
    expect(screen.getByText('2 configured tmux window(s) are not running.')).toBeInTheDocument()
    expect(screen.getByText('4 running window(s) were not launched from the current config.')).toBeInTheDocument()
    expect(screen.getByText('3 extra tmux window(s) are running outside the config.')).toBeInTheDocument()
  })

  it('summarizes extra tmux windows without exposing a destructive header action', () => {
    const result = readyWorkspaceResult()
    ;(result.data as Record<string, unknown>).runtime_sync = {
      summary: { current: 0, changed: 0, missing: 0, extra: 2, orphaned: 0, untracked: 0, external: 0 },
      slots: [],
      orphaned_state: [],
      historical_sessions: [],
    }
    mocks.workspaceResult.current = result

    renderDashboard()

    expect(screen.getByText('2 extra tmux window(s) are running outside the config.')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Stop extra windows' })).not.toBeInTheDocument()
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

    expect(screen.getByText('tmux is not available on this machine. Tmux slots cannot start here.')).toBeInTheDocument()
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

  it('does not expose per-slot lifecycle buttons on the slot card', () => {
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
    expect(screen.getByRole('button', { name: 'Edit slot dev' })).toBeInTheDocument()
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

    expect(screen.getByText('Set up demo.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Create from a starter template' })).toBeInTheDocument()
    expect(screen.queryByText(/Run cc-branch init/)).not.toBeInTheDocument()
    expect(screen.queryByText('No slots configured')).not.toBeInTheDocument()
  })
})
