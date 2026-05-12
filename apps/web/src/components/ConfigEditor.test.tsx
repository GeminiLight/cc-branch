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
    mocks.saveConfig.mockResolvedValue({ issues: [] })
    mocks.configResult.current = {
      data: {
        status: 'ready',
        content: [
          'version: 2',
          'project: demo',
          'root: .',
          'tabs:',
          '  - name: dev',
          '    panes:',
          '      - name: dev',
          '        runtime: tmux',
          '        windows:',
          '          - name: main',
          '            command: zsh',
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
  }, 10000)

  it('does not repeat form sections as summary tags', () => {
    renderConfigEditor()

    expect(screen.getAllByText('Form')).toHaveLength(1)
  })

  it('shows terminal commands as shell commands only when no agent is selected', () => {
    const currentResult = mocks.configResult.current as { data: Record<string, unknown> }
    mocks.configResult.current = {
      ...currentResult,
      data: {
        ...currentResult.data,
        content: [
          'version: 2',
          'project: demo',
          'root: .',
          'tabs:',
          '  - name: scratch',
          '    panes:',
          '      - name: scratch',
          '        command: "$SHELL"',
          '',
        ].join('\n'),
      },
    }

    renderConfigEditor()
    fireEvent.click(screen.getByRole('button', { name: 'Expand window scratch' }))

    expect(screen.getByText('Shell command')).toBeInTheDocument()
    expect(screen.queryByText(/^Command$/)).not.toBeInTheDocument()
  })

  it('hides shell command for agent-backed terminal slots', () => {
    const currentResult = mocks.configResult.current as { data: Record<string, unknown> }
    mocks.configResult.current = {
      ...currentResult,
      data: {
        ...currentResult.data,
        content: [
          'version: 2',
          'project: demo',
          'root: .',
          'tabs:',
          '  - name: coder',
          '    panes:',
          '      - name: coder',
          '        agent: codex',
          '        session_id: abc123',
          '',
        ].join('\n'),
      },
    }

    renderConfigEditor()
    fireEvent.click(screen.getByRole('button', { name: 'Expand window coder' }))

    expect(screen.queryByText('Shell command')).not.toBeInTheDocument()
    expect(screen.getByText('Session ID')).toBeInTheDocument()
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
          'version: 2',
          'project: demo',
          'root: .',
          'tabs:',
          '  - name: dev',
          '    panes:',
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

    expect(screen.getByRole('button', { name: 'Collapse slot dev' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Remove slot dev' })).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Expand window main' }))

    expect(screen.getByRole('button', { name: 'Move window main up' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Move window main down' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Remove window main' })).toBeInTheDocument()
  })

  it('adds another pane to a terminal tab without converting it to tmux', async () => {
    const currentResult = mocks.configResult.current as { data: Record<string, unknown> }
    mocks.configResult.current = {
      ...currentResult,
      data: {
        ...currentResult.data,
        content: [
          'version: 2',
          'project: demo',
          'root: .',
          'tabs:',
          '  - name: scratch',
          '    panes:',
          '      - name: scratch',
          '        command: zsh',
          '',
        ].join('\n'),
      },
    }

    renderConfigEditor()

    fireEvent.click(screen.getAllByRole('button', { name: 'Add pane' })[0])
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))

    await waitFor(() => expect(mocks.saveConfig).toHaveBeenCalled())
    const payload = mocks.saveConfig.mock.calls[0][0]
    expect(payload.content).toContain('tabs:')
    expect(payload.content).toContain('panes:')
    expect(payload.content).toContain('name: scratch')
    expect(payload.content).toContain('name: pane-2')
    expect(payload.content).not.toContain('slots:')
    expect(payload.content).not.toContain('runtime: terminal')
    expect(payload.content).not.toContain('runtime: tmux')
  })

  it('reorders tmux panes by dragging on the workspace matrix', () => {
    const currentResult = mocks.configResult.current as { data: Record<string, unknown> }
    mocks.configResult.current = {
      ...currentResult,
      data: {
        ...currentResult.data,
        content: [
          'version: 2',
          'project: demo',
          'root: .',
          'tabs:',
          '  - name: dev',
          '    panes:',
          '      - name: dev',
          '        runtime: tmux',
          '        windows:',
          '          - name: main',
          '            command: zsh',
          '          - name: worker',
          '            command: npm test',
          '          - name: review',
          '            command: npm run lint',
          '',
        ].join('\n'),
      },
    }

    renderConfigEditor()

    const main = screen.getByRole('button', { name: 'Expand window main' })
    const review = screen.getByRole('button', { name: 'Expand window review' })
    review.getBoundingClientRect = () => ({
      x: -100,
      y: 0,
      left: -100,
      top: 0,
      right: 20,
      bottom: 60,
      width: 120,
      height: 60,
      toJSON: () => ({}),
    })

    const dataTransfer = {
      effectAllowed: '',
      dropEffect: '',
      setData: vi.fn(),
      getData: vi.fn(),
    }
    fireEvent.dragStart(main, { dataTransfer })
    fireEvent.dragOver(review, { dataTransfer, clientX: 90, clientY: 20 })
    fireEvent.drop(review, { dataTransfer, clientX: 90, clientY: 20 })

    expect(
      screen.getAllByRole('button', { name: /Expand window/ }).map((button) => button.getAttribute('aria-label'))
    ).toEqual(['Expand window worker', 'Expand window main', 'Expand window review'])
  })

  it('moves tmux windows across tabs by dragging on the workspace matrix', () => {
    const currentResult = mocks.configResult.current as { data: Record<string, unknown> }
    mocks.configResult.current = {
      ...currentResult,
      data: {
        ...currentResult.data,
        content: [
          'version: 2',
          'project: demo',
          'root: .',
          'tabs:',
          '  - name: dev',
          '    panes:',
          '      - name: dev',
          '        runtime: tmux',
          '        windows:',
          '          - name: main',
          '            command: zsh',
          '          - name: worker',
          '            command: npm test',
          '  - name: review',
          '    panes:',
          '      - name: review',
          '        runtime: tmux',
          '        windows:',
          '          - name: audit',
          '            command: npm run lint',
          '',
        ].join('\n'),
      },
    }

    renderConfigEditor()

    const main = screen.getByRole('button', { name: 'Expand window main' })
    const audit = screen.getByRole('button', { name: 'Expand window audit' })
    audit.getBoundingClientRect = () => ({
      x: 0,
      y: 0,
      left: 0,
      top: 0,
      right: 120,
      bottom: 60,
      width: 120,
      height: 60,
      toJSON: () => ({}),
    })

    const dataTransfer = {
      effectAllowed: '',
      dropEffect: '',
      setData: vi.fn(),
      getData: vi.fn(),
    }
    fireEvent.dragStart(main, { dataTransfer })
    fireEvent.dragOver(audit, { dataTransfer, clientX: 90, clientY: 20 })
    fireEvent.drop(audit, { dataTransfer, clientX: 90, clientY: 20 })

    expect(
      screen.getAllByRole('button', { name: /Expand window/ }).map((button) => button.getAttribute('aria-label'))
    ).toEqual(['Expand window worker', 'Expand window main', 'Expand window audit'])
  })

  it('reorders tabs by dragging rows on the workspace matrix', () => {
    const currentResult = mocks.configResult.current as { data: Record<string, unknown> }
    mocks.configResult.current = {
      ...currentResult,
      data: {
        ...currentResult.data,
        content: [
          'version: 2',
          'project: demo',
          'root: .',
          'tabs:',
          '  - name: dev',
          '    panes:',
          '      - name: dev',
          '        command: zsh',
          '  - name: spec',
          '    panes:',
          '      - name: spec',
          '        command: npm test',
          '  - name: review',
          '    panes:',
          '      - name: review',
          '        command: npm run lint',
          '',
        ].join('\n'),
      },
    }

    renderConfigEditor()

    const devRow = screen.getByRole('button', { name: 'Collapse slot dev' }).closest('section')!
    const reviewRow = screen.getByRole('button', { name: 'Expand slot review' }).closest('section')!
    reviewRow.getBoundingClientRect = () => ({
      x: 0,
      y: 0,
      left: 0,
      top: 0,
      right: 600,
      bottom: 100,
      width: 600,
      height: 100,
      toJSON: () => ({}),
    })

    const dataTransfer = {
      effectAllowed: '',
      dropEffect: '',
      setData: vi.fn(),
      getData: vi.fn(),
    }
    fireEvent.dragStart(devRow, { dataTransfer })
    fireEvent.dragOver(reviewRow, { dataTransfer, clientX: 20, clientY: 80 })
    fireEvent.drop(reviewRow, { dataTransfer, clientX: 20, clientY: 80 })

    const tabLabels = screen
      .getAllByRole('button')
      .map((button) => button.getAttribute('aria-label'))
      .filter((label): label is string => Boolean(label?.match(/^(Collapse|Expand) slot /)))

    expect(tabLabels).toEqual(['Expand slot spec', 'Collapse slot dev', 'Expand slot review'])
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

    fireEvent.click(screen.getByRole('button', { name: 'Tmux (unavailable)' }))
    const tmuxOption = screen.getByRole('option', { name: 'Tmux (unavailable)' })
    expect(tmuxOption).toBeDisabled()
    expect(screen.getByRole('option', { name: 'Open terminal' })).not.toBeDisabled()
  })
})
