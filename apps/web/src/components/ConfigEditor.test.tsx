import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react'
import ConfigEditor from './ConfigEditor'
import { I18nProvider } from '../i18n'
import { ToastProvider } from './ui/Toast'
import { APIRequestError } from '../api/client'

const mocks = vi.hoisted(() => ({
  configResult: {
    current: null as unknown,
  },
  saveConfig: vi.fn(),
  useAgentSessions: vi.fn(),
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
  useAgentSessions: (...args: unknown[]) => mocks.useAgentSessions(...args),
}))

function renderConfigEditor(view: 'workspace' | 'project' = 'workspace') {
  return render(
    <I18nProvider>
      <ToastProvider>
        <ConfigEditor projectPath="/tmp/demo" view={view} />
      </ToastProvider>
    </I18nProvider>
  )
}

function createDataTransfer() {
  const store = new Map<string, string>()
  return {
    effectAllowed: '',
    dropEffect: '',
    setData: vi.fn((type: string, value: string) => store.set(type, value)),
    getData: vi.fn((type: string) => store.get(type) || ''),
  }
}

describe('ConfigEditor diagnostics', () => {
  beforeEach(() => {
    mocks.saveConfig.mockReset()
    mocks.saveConfig.mockResolvedValue({ issues: [] })
    mocks.useAgentSessions.mockReset()
    mocks.useAgentSessions.mockReturnValue({
      data: { sessions: [] },
      isFetching: false,
    })
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

  it('suppresses stale unknown-field warnings for canonical v2 fields', () => {
    const currentResult = mocks.configResult.current as { data: Record<string, unknown> }
    mocks.configResult.current = {
      ...currentResult,
      data: {
        ...currentResult.data,
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

    renderConfigEditor()

    expect(screen.queryByText("Unknown field 'openWith'")).not.toBeInTheDocument()
    expect(screen.queryByText("Unknown field 'layoutBackend'")).not.toBeInTheDocument()
    expect(screen.getByText("Unknown field 'stillWrong'")).toBeInTheDocument()
  })

  it('clears stale backend issues as soon as the YAML draft changes', () => {
    renderConfigEditor()

    expect(screen.getByText("Unknown field 'unknown'")).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'YAML' }))
    fireEvent.change(screen.getByLabelText('Configuration editor'), {
      target: {
        value: [
          'version: 2',
          'project: demo',
          'root: .',
          'openWith: auto-terminal',
          'layoutBackend: tmux',
          'tabs:',
          '  - name: dev',
          '    panes:',
          '      - name: main',
          '        command: zsh',
          '',
        ].join('\n'),
      },
    })

    expect(screen.queryByText("Unknown field 'unknown'")).not.toBeInTheDocument()
    expect(screen.queryByText('Invalid runtime: docker')).not.toBeInTheDocument()
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

  it('shows project identity and launch defaults without hiding them behind advanced details', () => {
    renderConfigEditor('project')

    expect(screen.getByText('Workspace identity')).toBeInTheDocument()
    expect(screen.getByText('Launch defaults')).toBeInTheDocument()
    expect(screen.getByText('Default launch tool')).toBeInTheDocument()
    expect(screen.queryByText('Advanced defaults')).not.toBeInTheDocument()
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
    fireEvent.click(screen.getByRole('button', { name: 'Edit pane scratch' }))

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
    fireEvent.click(screen.getByRole('button', { name: 'Edit pane coder' }))

    expect(screen.queryByText('Shell command')).not.toBeInTheDocument()
    expect(screen.getByText('Agent session')).toBeInTheDocument()
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

    expect(screen.getByRole('button', { name: 'Edit tab dev' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Remove tab dev' })).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Edit pane dev' }))

    expect(screen.queryByRole('button', { name: 'Edit pane main' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Move pane main up' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Remove pane main' })).not.toBeInTheDocument()
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

  it('renders tmux windows as one draggable group on the workspace matrix', () => {
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

    const group = screen.getByRole('button', { name: 'Edit pane dev' })

    expect(group).toBeInTheDocument()
    expect(group).toHaveAttribute('draggable', 'true')
    expect(screen.getByText('Tmux group')).toBeInTheDocument()
    expect(screen.getAllByText('Tabs: 1 / panes: 1').length).toBeGreaterThan(0)
    expect(screen.getAllByText('3 tmux windows')).not.toHaveLength(0)
    expect(screen.getByText('main')).toBeInTheDocument()
    expect(screen.getByText('worker')).toBeInTheDocument()
    expect(screen.getByText('review')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Edit pane main' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Edit pane worker' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Edit pane review' })).not.toBeInTheDocument()

    fireEvent.click(group)

    expect(screen.getByRole('heading', { name: 'Selected pane' })).toBeInTheDocument()
    expect(screen.getByDisplayValue('main')).toBeInTheDocument()
    expect(screen.getByDisplayValue('worker')).toBeInTheDocument()

    fireEvent.change(screen.getByDisplayValue('worker'), { target: { value: 'builder' } })

    expect(screen.getByDisplayValue('builder')).toBeInTheDocument()
  })

  it('loads agent sessions only after resume mode is requested', () => {
    const currentResult = mocks.configResult.current as { data: Record<string, unknown> }
    mocks.configResult.current = {
      ...currentResult,
      data: {
        ...currentResult.data,
        content: [
          'version: 2',
          'project: demo',
          'root: .',
          'agents:',
          '  codex:',
          '    command: codex',
          'tabs:',
          '  - name: dev',
          '    panes:',
          '      - name: coder',
          '        agent: codex',
          '',
        ].join('\n'),
      },
    }

    renderConfigEditor()

    fireEvent.click(screen.getByRole('button', { name: 'Edit pane coder' }))

    expect(mocks.useAgentSessions).toHaveBeenLastCalledWith(
      { projectPath: '/tmp/demo', configPath: undefined },
      false,
      'codex',
    )

    fireEvent.click(screen.getByRole('button', { name: 'Resume' }))

    expect(mocks.useAgentSessions).toHaveBeenLastCalledWith(
      { projectPath: '/tmp/demo', configPath: undefined },
      true,
      'codex',
    )
  })

  it('moves a tmux window group across tabs by dragging on the workspace matrix', async () => {
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

    const devGroup = screen.getByRole('button', { name: 'Edit pane dev' })
    const reviewGroup = screen.getByRole('button', { name: 'Edit pane review' })
    devGroup.getBoundingClientRect = () => ({
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

    const dataTransfer = createDataTransfer()
    fireEvent.dragStart(reviewGroup, { dataTransfer })
    expect(dataTransfer.setData).toHaveBeenCalledWith('text/plain', '1:0')
    fireEvent.dragOver(devGroup, { dataTransfer, clientX: 20, clientY: 20 })
    fireEvent.drop(devGroup, { dataTransfer, clientX: 20, clientY: 20 })

    await waitFor(() => {
      const tabLabels = screen
        .getAllByRole('button')
        .map((button) => button.getAttribute('aria-label'))
        .filter((label): label is string => Boolean(label?.match(/^Edit tab /)))

      expect(tabLabels).toEqual(['Edit tab dev'])
    })
    expect(screen.getByRole('button', { name: 'Edit pane review' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Edit pane dev' })).toBeInTheDocument()
  })

  it('moves a selected tmux group from the inspector', async () => {
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

    fireEvent.click(screen.getByRole('button', { name: 'Edit pane review' }))
    fireEvent.click(screen.getByRole('button', { name: 'Move to tab' }))
    fireEvent.click(screen.getByRole('option', { name: /dev/ }))
    fireEvent.click(screen.getByRole('button', { name: 'Move' }))

    await waitFor(() => {
      const tabLabels = screen
        .getAllByRole('button')
        .map((button) => button.getAttribute('aria-label'))
        .filter((label): label is string => Boolean(label?.match(/^Edit tab /)))

      expect(tabLabels).toEqual(['Edit tab dev'])
    })
    expect(screen.getByRole('button', { name: 'Edit pane dev' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Edit pane review' })).toBeInTheDocument()
  })

  it('moves a legacy tmux tab group from the inspector', async () => {
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
          '      - name: ui',
          '        command: npm run dev',
          '  - name: review',
          '    layoutBackend: tmux',
          '    panes:',
          '      - name: audit',
          '        command: npm run lint',
          '',
        ].join('\n'),
      },
    }

    renderConfigEditor()

    fireEvent.click(screen.getByRole('button', { name: 'Edit pane review' }))
    fireEvent.click(screen.getByRole('button', { name: 'Move to tab' }))
    fireEvent.click(screen.getByRole('option', { name: /dev/ }))
    fireEvent.click(screen.getByRole('button', { name: 'Move' }))

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Edit tab dev' })).toBeInTheDocument()
      expect(screen.queryByRole('button', { name: 'Edit tab review' })).not.toBeInTheDocument()
    })
    expect(screen.getByRole('button', { name: 'Edit pane ui' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Edit pane review' })).toBeInTheDocument()
  })

  it('moves terminal panes across tabs by dragging on the workspace matrix', async () => {
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
          '      - name: ui',
          '        command: npm run dev',
          '      - name: spec',
          '        command: npm test',
          '  - name: ops',
          '    panes:',
          '      - name: shell',
          '        command: zsh',
          '',
        ].join('\n'),
      },
    }

    renderConfigEditor()

    const uiPane = screen.getByRole('button', { name: 'Edit pane ui' })
    const shellPane = screen.getByRole('button', { name: 'Edit pane shell' })
    uiPane.getBoundingClientRect = () => ({
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

    const dataTransfer = createDataTransfer()
    fireEvent.dragStart(shellPane, { dataTransfer })
    expect(dataTransfer.setData).toHaveBeenCalledWith('text/plain', '1:0')
    fireEvent.dragOver(uiPane, { dataTransfer, clientX: 20, clientY: 20 })
    fireEvent.drop(uiPane, { dataTransfer, clientX: 20, clientY: 20 })

    await waitFor(() => {
      const paneLabels = screen
        .getAllByRole('button')
        .map((button) => button.getAttribute('aria-label'))
        .filter((label): label is string => Boolean(label?.match(/^Edit pane /)))

      expect(paneLabels).toEqual(['Edit pane shell', 'Edit pane ui', 'Edit pane spec'])
    })
  })

  it('moves an implicit terminal pane across tabs by dragging on the workspace matrix', async () => {
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
          '  - name: shell',
          '    command: zsh',
          '  - name: dev',
          '    panes:',
          '      - name: ui',
          '        command: npm run dev',
          '',
        ].join('\n'),
      },
    }

    renderConfigEditor()

    const shellPane = screen.getByRole('button', { name: 'Edit pane shell' })
    const uiPane = screen.getByRole('button', { name: 'Edit pane ui' })
    uiPane.getBoundingClientRect = () => ({
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

    const dataTransfer = createDataTransfer()
    fireEvent.dragStart(shellPane, { dataTransfer })
    expect(dataTransfer.setData).toHaveBeenCalledWith('text/plain', '0:0')
    fireEvent.dragOver(uiPane, { dataTransfer, clientX: 140, clientY: 20 })
    fireEvent.drop(uiPane, { dataTransfer, clientX: 140, clientY: 20 })

    await waitFor(() => {
      const paneLabels = screen
        .getAllByRole('button')
        .map((button) => button.getAttribute('aria-label'))
        .filter((label): label is string => Boolean(label?.match(/^Edit pane /)))

      expect(paneLabels).toEqual(['Edit pane shell', 'Edit pane ui'])
      expect(screen.queryByRole('button', { name: 'Edit tab shell' })).not.toBeInTheDocument()
    })
  })

  it('keeps implicit terminal pane names aligned between the canvas and inspector', () => {
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
          '  - name: shell',
          '    command: zsh',
          '',
        ].join('\n'),
      },
    }

    renderConfigEditor()

    fireEvent.click(screen.getByRole('button', { name: 'Edit pane shell' }))
    expect(screen.getByDisplayValue('shell')).toBeInTheDocument()

    fireEvent.change(screen.getByDisplayValue('shell'), { target: { value: 'terminal' } })
    expect(screen.getByRole('button', { name: 'Edit pane terminal' })).toBeInTheDocument()
  })

  it('moves an implicit terminal pane to another tab from the inspector', async () => {
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
          '  - name: shell',
          '    command: zsh',
          '  - name: dev',
          '    panes:',
          '      - name: ui',
          '        command: npm run dev',
          '',
        ].join('\n'),
      },
    }

    renderConfigEditor()

    fireEvent.click(screen.getByRole('button', { name: 'Edit pane shell' }))
    fireEvent.click(screen.getByRole('button', { name: 'Move to tab' }))
    fireEvent.click(screen.getByRole('option', { name: /dev/ }))
    fireEvent.click(screen.getByRole('button', { name: 'Move' }))

    await waitFor(() => {
      const paneLabels = screen
        .getAllByRole('button')
        .map((button) => button.getAttribute('aria-label'))
        .filter((label): label is string => Boolean(label?.match(/^Edit pane /)))

      expect(paneLabels).toEqual(['Edit pane ui', 'Edit pane shell'])
      expect(screen.queryByRole('button', { name: 'Edit tab shell' })).not.toBeInTheDocument()
    })
  })

  it('reorders terminal panes inside the same tab by dragging on the workspace matrix', async () => {
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
          '      - name: ui',
          '        command: npm run dev',
          '      - name: spec',
          '        command: npm test',
          '      - name: docs',
          '        command: npm run docs',
          '',
        ].join('\n'),
      },
    }

    renderConfigEditor()

    const uiPane = screen.getByRole('button', { name: 'Edit pane ui' })
    const docsPane = screen.getByRole('button', { name: 'Edit pane docs' })
    uiPane.getBoundingClientRect = () => ({
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

    const dataTransfer = createDataTransfer()
    fireEvent.dragStart(docsPane, { dataTransfer })
    expect(dataTransfer.setData).toHaveBeenCalledWith('text/plain', '0:2')
    fireEvent.dragOver(uiPane, { dataTransfer, clientX: 20, clientY: 20 })
    fireEvent.drop(uiPane, { dataTransfer, clientX: 20, clientY: 20 })

    await waitFor(() => {
      const paneLabels = screen
        .getAllByRole('button')
        .map((button) => button.getAttribute('aria-label'))
        .filter((label): label is string => Boolean(label?.match(/^Edit pane /)))

      expect(paneLabels).toEqual(['Edit pane docs', 'Edit pane ui', 'Edit pane spec'])
    })
  })

  it('moves a selected pane to another compatible tab from the inspector', async () => {
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
          '      - name: ui',
          '        command: npm run dev',
          '      - name: spec',
          '        command: npm test',
          '  - name: ops',
          '    panes:',
          '      - name: shell',
          '        command: zsh',
          '  - name: review',
          '    panes:',
          '      - name: lint',
          '        command: npm run lint',
          '',
        ].join('\n'),
      },
    }

    renderConfigEditor()

    fireEvent.click(screen.getByRole('button', { name: 'Edit pane spec' }))
    fireEvent.click(screen.getByRole('button', { name: 'Move to tab' }))

    expect(screen.queryByRole('option', { name: /dev/ })).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('option', { name: /review/ }))
    fireEvent.click(screen.getByRole('button', { name: 'Move' }))

    await waitFor(() => {
      const paneLabels = screen
        .getAllByRole('button')
        .map((button) => button.getAttribute('aria-label'))
        .filter((label): label is string => Boolean(label?.match(/^Edit pane /)))

      expect(paneLabels).toEqual([
        'Edit pane ui',
        'Edit pane shell',
        'Edit pane lint',
        'Edit pane spec',
      ])
    })
  })

  it('moves a terminal pane into a tab that already contains a tmux group', async () => {
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
          '  - name: codex-spec',
          '    panes:',
          '      - name: dev-backend',
          '        agent: codex',
          '      - name: spec',
          '        agent: claude',
          '  - name: tmux-dev',
          '    layoutBackend: tmux',
          '    panes:',
          '      - name: shell',
          '        command: zsh',
          '',
        ].join('\n'),
      },
    }

    renderConfigEditor()

    fireEvent.click(screen.getByRole('button', { name: 'Edit pane spec' }))
    fireEvent.click(screen.getByRole('button', { name: 'Move to tab' }))

    expect(screen.queryByText('Add another tab first.')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('option', { name: /tmux-dev/ }))
    fireEvent.click(screen.getByRole('button', { name: 'Move' }))

    await waitFor(() => {
      const tmuxTab = screen.getByRole('button', { name: 'Edit tab tmux-dev' }).closest('section')!
      expect(within(tmuxTab).getByRole('button', { name: 'Edit pane tmux-dev' })).toBeInTheDocument()
      expect(within(tmuxTab).getByRole('button', { name: 'Edit pane spec' })).toBeInTheDocument()
    })

    fireEvent.click(screen.getByRole('button', { name: 'Save' }))

    await waitFor(() => expect(mocks.saveConfig).toHaveBeenCalled())
    const payload = mocks.saveConfig.mock.calls[0][0]
    expect(payload.content).toContain('name: tmux-dev')
    expect(payload.content).toContain('layoutBackend: tmux')
    expect(payload.content).toContain('windows:')
    expect(payload.content).toContain('name: spec')
    expect(payload.content).not.toContain('runtime:')
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

    const devRow = screen.getByRole('button', { name: 'Edit tab dev' }).closest('section')!
    const reviewRow = screen.getByRole('button', { name: 'Edit tab review' }).closest('section')!
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

    const dataTransfer = createDataTransfer()
    fireEvent.dragStart(devRow, { dataTransfer })
    fireEvent.dragOver(reviewRow, { dataTransfer, clientX: 20, clientY: 80 })
    fireEvent.drop(reviewRow, { dataTransfer, clientX: 20, clientY: 80 })

    const tabLabels = screen
      .getAllByRole('button')
      .map((button) => button.getAttribute('aria-label'))
      .filter((label): label is string => Boolean(label?.match(/^Edit tab /)))

    expect(tabLabels).toEqual(['Edit tab spec', 'Edit tab dev', 'Edit tab review'])
  })

  it('keeps tab details runtime agnostic', () => {
    const currentResult = mocks.configResult.current as { data: Record<string, unknown> }
    const currentData = currentResult.data
    mocks.configResult.current = {
      ...currentResult,
      data: {
        ...currentData,
        issues: [],
        runtimes: {
          tmux: { available: false, reason: 'tmux was not found on PATH' },
          terminal: { available: true },
        },
      },
    }

    renderConfigEditor()

    const inspector = within(screen.getByRole('complementary'))
    expect(inspector.getByRole('heading', { name: 'Selected tab' })).toBeInTheDocument()
    expect(inspector.getByText('Group')).toBeInTheDocument()
    expect(inspector.queryByText('Runtime')).not.toBeInTheDocument()
    expect(inspector.queryByText('Working directory')).not.toBeInTheDocument()
    expect(inspector.queryByText('Environment variables')).not.toBeInTheDocument()
    expect(inspector.queryByText('Tmux (unavailable)')).not.toBeInTheDocument()
  })
})
