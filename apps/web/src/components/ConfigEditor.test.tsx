import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import ConfigEditor from './ConfigEditor'
import { I18nProvider } from '../i18n'
import { ToastProvider } from './ui/Toast'
import { APIRequestError } from '../api/client'

const mocks = vi.hoisted(() => ({
  configResult: {
    current: null as unknown,
  },
  saveConfig: vi.fn(),
}))

vi.mock('../hooks', () => ({
  useConfig: () => mocks.configResult.current,
  useSaveConfig: () => ({
    mutateAsync: mocks.saveConfig,
    isPending: false,
  }),
  useKeyboardShortcuts: vi.fn(),
  useAgents: () => ({
    data: { agents: [] },
  }),
  useAgentSessions: () => ({
    data: { sessions: [] },
    isFetching: false,
  }),
}))

function renderConfigEditor() {
  return render(
    <I18nProvider>
      <ToastProvider>
        <ConfigEditor projectPath="/tmp/demo" />
      </ToastProvider>
    </I18nProvider>
  )
}

describe('ConfigEditor diagnostics', () => {
  beforeEach(() => {
    mocks.saveConfig.mockReset()
    mocks.configResult.current = {
      data: {
        status: 'ready',
        content: [
          'version: 1',
          'project: demo',
          'root: .',
          'slots:',
          '  - name: dev',
          '    windows:',
          '      - name: main',
          '        command: zsh',
          '',
        ].join('\n'),
        path: '/tmp/demo/.cc-branch/config.yaml',
        project_path: '/tmp/demo',
        state_path: '/tmp/demo/.cc-branch.state.toml',
        mtime: 1,
        content_hash: 'abc123',
        issues: [
          {
            issue_type: 'unknown_field',
            severity: 'warning',
            message: "Unknown field 'unknown'",
            target: 'config',
            context: { field: 'unknown' },
            fixable: false,
          },
          {
            issue_type: 'invalid_enum',
            severity: 'error',
            message: 'Invalid runtime: docker',
            target: 'slot:dev',
            context: { field: 'runtime' },
            fixable: false,
          },
        ],
      },
      error: null,
      isLoading: false,
    }
  })

  it('surfaces config validation issues returned by the backend', () => {
    renderConfigEditor()

    expect(screen.getByText("Unknown field 'unknown'")).toBeInTheDocument()
    expect(screen.getByText('Invalid runtime: docker')).toBeInTheDocument()
  })

  it('does not duplicate generated YAML inside form mode', () => {
    renderConfigEditor()

    expect(screen.getByRole('button', { name: 'Form' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'YAML' })).toBeInTheDocument()
    expect(screen.queryByText('Generated YAML')).not.toBeInTheDocument()
  })

  it('surfaces config validation issues returned by a failed save', async () => {
    mocks.saveConfig.mockRejectedValue(
      new APIRequestError(400, {
        error: 'Invalid config',
        code: 'invalid_config',
        issues: [
          {
            issue_type: 'missing_launch_command',
            severity: 'error',
            message: 'Window must define command or agent',
            target: 'slot:dev/window:worker',
            context: {},
            fixable: false,
          },
        ],
      })
    )

    renderConfigEditor()
    fireEvent.click(screen.getByRole('button', { name: 'YAML' }))
    fireEvent.change(screen.getByLabelText('Configuration editor'), {
      target: {
        value: [
          'version: 1',
          'project: demo',
          'root: .',
          'slots:',
          '  - name: dev',
          '    windows:',
          '      - name: worker',
          '',
        ].join('\n'),
      },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))

    await waitFor(() => {
      expect(screen.getByText('Window must define command or agent')).toBeInTheDocument()
    })
  })

  it('gives slot and window icon controls specific accessible names', () => {
    renderConfigEditor()

    fireEvent.click(screen.getByRole('button', { name: 'Expand slots section' }))
    expect(screen.getByRole('button', { name: 'Collapse slot dev' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Remove slot dev' })).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Expand window main' }))

    expect(screen.getByRole('button', { name: 'Move window main up' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Move window main down' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Remove window main' })).toBeInTheDocument()
  })

  it('disables tmux as a runtime choice when tmux is unavailable locally', () => {
    const currentResult = mocks.configResult.current as { data: Record<string, unknown> }
    const currentData = currentResult.data
    mocks.configResult.current = {
      ...currentResult,
      data: {
        ...currentData,
        runtimes: {
          tmux: { available: false, reason: 'tmux was not found on PATH' },
          terminal: { available: true },
        },
      },
    }

    renderConfigEditor()

    fireEvent.click(screen.getByRole('button', { name: 'Expand slots section' }))
    fireEvent.click(screen.getByRole('button', { name: 'Tmux (unavailable)' }))
    const tmuxOption = screen.getByRole('option', { name: 'Tmux (unavailable)' })
    expect(tmuxOption).toBeDisabled()
    expect(screen.getByRole('option', { name: 'Open terminal' })).not.toBeDisabled()
  })
})
