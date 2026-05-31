import { describe, it, expect, vi, beforeEach } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import DoctorView from './DoctorView'
import { I18nProvider } from '../i18n'

const mocks = vi.hoisted(() => ({
  doctorResult: {
    current: null as unknown,
  },
  configResult: {
    current: { data: { issues: [] } } as unknown,
  },
  workspaceResult: {
    current: { data: { runtime_sync: { summary: {} } } } as unknown,
  },
  actionMutation: {
    current: { mutateAsync: vi.fn(), isPending: false } as unknown,
  },
  apiClient: {
    current: { getDiagnosticBundle: vi.fn() } as unknown,
  },
}))

vi.mock('../hooks', () => ({
  useApiClient: () => mocks.apiClient.current,
  useDoctor: () => mocks.doctorResult.current,
  useConfig: () => mocks.configResult.current,
  useWorkspace: () => mocks.workspaceResult.current,
  useWorkspaceAction: () => mocks.actionMutation.current,
}))

function renderDoctorView() {
  return render(
    <I18nProvider>
      <DoctorView projectPath="/tmp/demo" />
    </I18nProvider>
  )
}

describe('DoctorView summary', () => {
  beforeEach(() => {
    mocks.doctorResult.current = {
      data: {
        report: [
          'Workspace:',
          '✓ config: .cc-branch/config.yaml found',
          '✗ tmux: not installed',
          '→ brew install tmux',
          '⚠ agent: codex CLI not found',
          '',
        ].join('\n'),
      },
      error: null,
      isLoading: false,
      isFetching: false,
      refetch: vi.fn(),
    }
    mocks.configResult.current = { data: { issues: [] } }
    mocks.workspaceResult.current = { data: { runtime_sync: { summary: {} } } }
    mocks.actionMutation.current = { mutateAsync: vi.fn().mockResolvedValue({ code: 'orphaned_state_pruned' }), isPending: false }
    mocks.apiClient.current = {
      getDiagnosticBundle: vi.fn().mockResolvedValue({
        kind: 'cc-branch-diagnostic-bundle',
        generated_at: '2026-05-19T00:00:00Z',
        app: { version: '0.1.3' },
        backend: { port: 5192 },
        schema: {},
        project: { path: '~/demo' },
        files: {},
        doctor: { status: 'ready', report: 'ok' },
        logs: { available: false },
      }),
    }
  })

  it('summarizes blocking issues and warnings before the detailed checks', () => {
    renderDoctorView()

    expect(screen.getByText('Workspace diagnosis')).toBeInTheDocument()
    expect(screen.getByText('Findings')).toBeInTheDocument()
    expect(screen.getByText('1 issue')).toBeInTheDocument()
    expect(screen.getByText('1 warning')).toBeInTheDocument()
    expect(screen.getByText('Action needed before this workspace is healthy.')).toBeInTheDocument()
  })

  it('shows actionable findings before passing checks', () => {
    renderDoctorView()

    const issue = screen.getByText('not installed')
    const passed = screen.getByText('.cc-branch/config.yaml found')

    expect(issue.compareDocumentPosition(passed) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(screen.getAllByText('1 passed').length).toBeGreaterThan(0)
    expect(screen.getByText('Show details')).toBeInTheDocument()
  })

  it('keeps all-clear diagnosis compact without repeating the ready message', () => {
    mocks.doctorResult.current = {
      data: { report: 'Workspace:\n✓ config: .cc-branch/config.yaml found\n' },
      error: null,
      isLoading: false,
      isFetching: false,
      refetch: vi.fn(),
    }

    renderDoctorView()

    expect(screen.queryByText('Ready to launch')).not.toBeInTheDocument()
    expect(screen.getAllByText('All checks passed')).toHaveLength(1)
    expect(screen.getAllByText('Workspace checks are clear.')).toHaveLength(1)
    expect(screen.getAllByText('1 passed').length).toBeGreaterThan(0)
    expect(screen.queryByText('0 issues')).not.toBeInTheDocument()
    expect(screen.queryByText('0 warnings')).not.toBeInTheDocument()
  })

  it('does not surface stale unknown-field warnings for canonical v2 fields', () => {
    mocks.doctorResult.current = {
      data: { report: 'Workspace:\n✓ config: .cc-branch/config.yaml found\n' },
      error: null,
      isLoading: false,
      isFetching: false,
      refetch: vi.fn(),
    }
    mocks.configResult.current = {
      data: {
        issues: [
          {
            issue_type: 'unknown_field',
            severity: 'warning',
            message: "Unknown field 'openWith'",
            target: 'config',
            context: { field: 'openWith' },
            fixable: false,
          },
          {
            issue_type: 'unknown_field',
            severity: 'warning',
            message: "Unknown field 'layoutBackend'",
            target: 'tab:dev',
            context: { field: 'layoutBackend' },
            fixable: false,
          },
          {
            issue_type: 'unknown_field',
            severity: 'warning',
            message: "Unknown field 'stillWrong'",
            target: 'config',
            context: { field: 'stillWrong' },
            fixable: false,
          },
        ],
      },
    }

    renderDoctorView()

    expect(screen.queryByText("Unknown field 'openWith'")).not.toBeInTheDocument()
    expect(screen.queryByText("Unknown field 'layoutBackend'")).not.toBeInTheDocument()
    expect(screen.getByText("Unknown field 'stillWrong'")).toBeInTheDocument()
  })

  it('lets product checks drive the overall health state', () => {
    mocks.doctorResult.current = {
      data: { report: 'Workspace:\n✓ config: .cc-branch/config.yaml found\n' },
      error: null,
      isLoading: false,
      isFetching: false,
      refetch: vi.fn(),
    }
    mocks.configResult.current = {
      data: {
        issues: [
          {
            issue_type: 'invalid_enum',
            severity: 'error',
            message: 'Invalid layout backend: docker',
            target: 'config',
            context: {},
            fixable: false,
          },
        ],
      },
    }

    renderDoctorView()

    expect(screen.getByText('Action needed before this workspace is healthy.')).toBeInTheDocument()
    expect(screen.getAllByText('Issues found').length).toBeGreaterThan(0)
    expect(screen.getByText('Invalid layout backend: docker')).toBeInTheDocument()
  })

  it('renders structured doctor issues when text is not provided', () => {
    mocks.doctorResult.current = {
      data: {
        report: {
          project: 'demo',
          has_errors: true,
          issues: [
            {
              issue_type: 'missing_tmux',
              severity: 'error',
              message: 'tmux is missing',
              target: 'tmux',
              context: { hint: 'Install tmux with brew install tmux' },
              fixable: false,
            },
          ],
        },
      },
      error: null,
      isLoading: false,
      isFetching: false,
      refetch: vi.fn(),
    }

    renderDoctorView()

    expect(screen.getByText('tmux is missing')).toBeInTheDocument()
    expect(screen.getByText('→ Install tmux with brew install tmux')).toBeInTheDocument()
    expect(screen.getByText('1 issue')).toBeInTheDocument()
  })

  it('includes missing runtime panes in the workspace diagnosis', () => {
    mocks.doctorResult.current = {
      data: { report: 'Workspace:\n✓ config: .cc-branch/config.yaml found\n' },
      error: null,
      isLoading: false,
      isFetching: false,
      refetch: vi.fn(),
    }
    mocks.workspaceResult.current = {
      data: {
        runtime_sync: {
          summary: { missing: 2 },
        },
      },
    }

    renderDoctorView()

    expect(screen.getByText('Warnings found; workspace can run, but the setup needs attention.')).toBeInTheDocument()
    expect(screen.getByText('2 tmux-managed panes are not started.')).toBeInTheDocument()
    expect(screen.getByText('1 warning')).toBeInTheDocument()
  })

  it('offers an inline cleanup action for stale local session records', async () => {
    const mutateAsync = vi.fn().mockResolvedValue({ code: 'orphaned_state_pruned' })
    mocks.actionMutation.current = { mutateAsync, isPending: false }
    mocks.doctorResult.current = {
      data: {
        report: {
          project: 'demo',
          has_errors: false,
          issues: [
            {
              issue_type: 'orphaned_state',
              severity: 'warning',
              message: '2 stale local session records no longer match the current config',
              target: 'state',
              context: { count: 2 },
              fixable: true,
            },
          ],
        },
      },
      error: null,
      isLoading: false,
      isFetching: false,
      refetch: vi.fn(),
    }

    renderDoctorView()
    fireEvent.click(screen.getByRole('button', { name: 'Clean up' }))

    await waitFor(() => {
      expect(mutateAsync).toHaveBeenCalledWith({
        action: 'prune_state',
        target: undefined,
        opener: undefined,
        intent: undefined,
        projectPath: '/tmp/demo',
      })
    })
  })

  it('keeps hook order stable when diagnosis finishes loading', () => {
    mocks.doctorResult.current = {
      data: undefined,
      error: null,
      isLoading: true,
      isFetching: true,
      refetch: vi.fn(),
    }

    const view = render(
      <I18nProvider>
        <DoctorView projectPath="/tmp/demo" />
      </I18nProvider>
    )

    mocks.doctorResult.current = {
      data: { report: 'Workspace:\n✓ config: .cc-branch/config.yaml found\n' },
      error: null,
      isLoading: false,
      isFetching: false,
      refetch: vi.fn(),
    }

    expect(() => {
      view.rerender(
        <I18nProvider>
          <DoctorView projectPath="/tmp/demo" />
        </I18nProvider>
      )
    }).not.toThrow()
    expect(screen.getAllByText('All checks passed')).toHaveLength(1)
  })

  it('copies a compact diagnostic report for support', async () => {
    Object.assign(navigator, {
      clipboard: {
        writeText: vi.fn().mockResolvedValue(undefined),
      },
    })

    renderDoctorView()
    fireEvent.click(screen.getByRole('button', { name: 'Copy report' }))

    await waitFor(() => {
      const apiClient = mocks.apiClient.current as { getDiagnosticBundle: ReturnType<typeof vi.fn> }
      expect(apiClient.getDiagnosticBundle).toHaveBeenCalledWith({
        projectPath: '/tmp/demo',
        configPath: undefined,
      })
      expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
        expect.stringContaining('cc-branch-diagnostic-bundle')
      )
      expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
        expect.stringContaining('"project"')
      )
      expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
        expect.stringContaining('"logs"')
      )
    })
  })
})
