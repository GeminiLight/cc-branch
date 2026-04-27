import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
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
      config_path: '/tmp/demo/.cc-branch.yaml',
      state_path: '/tmp/demo/.cc-branch.state.toml',
      slots: [
        {
          name: 'dev',
          backend: 'tmux',
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

function renderDashboard() {
  return render(
    <I18nProvider>
      <ToastProvider>
        <Dashboard projectPath="/tmp/demo" />
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
            capabilities: ['open_project'],
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
        ],
      },
    }
    mocks.mutateAsync.mockReset()
    mocks.mutateAsync.mockResolvedValue({ success: true, message: 'ok' })
    mocks.refetch.mockReset()
  })

  it('opens the workspace dashboard from the primary toolbar button', async () => {
    renderDashboard()

    fireEvent.click(screen.getByRole('button', { name: 'Open workspace in terminal' }))

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

  it('opens the project folder with the selected editor opener', async () => {
    renderDashboard()

    fireEvent.click(screen.getByRole('button', { name: 'Open with System Terminal' }))
    fireEvent.click(screen.getByRole('option', { name: 'VS Code' }))
    fireEvent.click(screen.getByRole('button', { name: 'Open project in VS Code' }))

    await waitFor(() => {
      expect(mocks.mutateAsync).toHaveBeenCalledWith({
        action: 'open',
        target: undefined,
        opener: 'vscode',
        intent: 'project_folder',
        projectPath: '/tmp/demo',
      })
    })
  })

  it('remembers the selected opener from localStorage', async () => {
    window.localStorage.setItem('cc-branch.open.default./tmp/demo', 'vscode')
    renderDashboard()

    fireEvent.click(screen.getByRole('button', { name: 'Open project in VS Code' }))

    await waitFor(() => {
      expect(mocks.mutateAsync).toHaveBeenCalledWith({
        action: 'open',
        target: undefined,
        opener: 'vscode',
        intent: 'project_folder',
        projectPath: '/tmp/demo',
      })
    })
  })

  it('does not select unavailable openers', () => {
    renderDashboard()

    fireEvent.click(screen.getByRole('button', { name: 'Open with System Terminal' }))
    expect(screen.getByRole('option', { name: 'Cursor' })).toBeDisabled()
    fireEvent.click(screen.getByRole('option', { name: 'Cursor' }))

    expect(screen.getByRole('button', { name: 'Open workspace in terminal' })).toBeInTheDocument()
  })

  it('uses a terminal opener for slot attach when the selected opener is an editor', async () => {
    renderDashboard()

    fireEvent.click(screen.getByRole('button', { name: 'Open with System Terminal' }))
    fireEvent.click(screen.getByRole('option', { name: 'VS Code' }))
    fireEvent.click(screen.getByRole('button', { name: 'Open terminal dev' }))

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

  it('can still start the workspace without opening a terminal', async () => {
    renderDashboard()

    fireEvent.click(screen.getByRole('button', { name: 'Start in background' }))

    await waitFor(() => {
      expect(mocks.mutateAsync).toHaveBeenCalledWith({
        action: 'launch',
        target: undefined,
        projectPath: '/tmp/demo',
      })
    })
  })

  it('opens a running slot in a terminal', async () => {
    renderDashboard()

    fireEvent.click(screen.getByRole('button', { name: 'Open terminal dev' }))

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
    renderDashboard()

    fireEvent.click(screen.getByRole('button', { name: 'Open terminal dev:planner' }))

    await waitFor(() => {
      expect(mocks.mutateAsync).toHaveBeenCalledWith({
        action: 'open',
        target: 'dev:planner',
        opener: 'auto-terminal',
        intent: 'attach_target',
        projectPath: '/tmp/demo',
      })
    })
  })

  it('opens a stopped slot in a terminal instead of hiding the terminal side effect behind launch copy', async () => {
    mocks.workspaceResult.current = stoppedWorkspaceResult()
    renderDashboard()

    fireEvent.click(screen.getByRole('button', { name: 'Open terminal dev' }))

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

  it('runs slot restart from the slot card button', async () => {
    renderDashboard()

    fireEvent.click(screen.getByRole('button', { name: 'Restart dev' }))

    await waitFor(() => {
      expect(mocks.mutateAsync).toHaveBeenCalledWith({
        action: 'restart',
        target: 'dev',
        projectPath: '/tmp/demo',
      })
    })
  })

  it('confirms workspace stop before running the action', async () => {
    renderDashboard()

    fireEvent.click(screen.getByRole('button', { name: 'Stop workspace' }))
    fireEvent.click(screen.getByRole('button', { name: 'Stop' }))

    await waitFor(() => {
      expect(mocks.mutateAsync).toHaveBeenCalledWith({
        action: 'stop',
        target: undefined,
        projectPath: '/tmp/demo',
      })
    })
  })

  it('renders web-first setup when the backend reports needs_init', () => {
    mocks.workspaceResult.current = {
      data: {
        status: 'needs_init',
        project_path: '/tmp/demo',
        config_path: '/tmp/demo/.cc-branch.yaml',
        state_path: '/tmp/demo/.cc-branch.state.toml',
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

    expect(screen.getByText('No workspace config found')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Create from a starter profile' })).toBeInTheDocument()
    expect(screen.queryByText(/Run cc-branch init/)).not.toBeInTheDocument()
    expect(screen.queryByText('No slots configured')).not.toBeInTheDocument()
  })
})
