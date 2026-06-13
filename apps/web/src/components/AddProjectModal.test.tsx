import { beforeEach, describe, it, expect, vi } from 'vitest'
import { render, fireEvent, screen, waitFor } from '@testing-library/react'
import AddProjectModal from './AddProjectModal'
import { I18nProvider } from '../i18n'
import { ToastProvider } from './ui/Toast'
import type { APIClient } from '../api/client'

const mocks = vi.hoisted(() => ({
  getApiInfo: vi.fn().mockResolvedValue({
    port: 8080,
    config_path: '/tmp/demo/.cc-branch/config.yaml',
    state_path: '/tmp/demo/.cc-branch/state.yaml',
    ssh_hosts: [{ alias: 'gpu-dev', hostname: 'gpu.example.com', user: 'ubuntu', port: 2222 }],
  }),
  probeProject: vi.fn(),
  pickProjectDirectory: vi.fn(),
  listRemoteDirectories: vi.fn(),
  shouldInjectCurrentProject: vi.fn().mockReturnValue(true),
  supportsNativeProjectDirectoryPicker: vi.fn().mockReturnValue(true),
}))

const api = {
  getApiInfo: mocks.getApiInfo,
  probeProject: mocks.probeProject,
  pickProjectDirectory: mocks.pickProjectDirectory,
  listRemoteDirectories: mocks.listRemoteDirectories,
  shouldInjectCurrentProject: mocks.shouldInjectCurrentProject,
  supportsNativeProjectDirectoryPicker: mocks.supportsNativeProjectDirectoryPicker,
} as unknown as APIClient

describe('AddProjectModal', () => {
  beforeEach(() => {
    mocks.getApiInfo.mockReset()
    mocks.getApiInfo.mockResolvedValue({
      port: 8080,
      config_path: '/tmp/demo/.cc-branch/config.yaml',
      state_path: '/tmp/demo/.cc-branch/state.yaml',
      ssh_hosts: [{ alias: 'gpu-dev', hostname: 'gpu.example.com', user: 'ubuntu', port: 2222 }],
    })
    mocks.probeProject.mockReset()
    mocks.pickProjectDirectory.mockReset()
    mocks.listRemoteDirectories.mockReset()
    mocks.listRemoteDirectories.mockResolvedValue({
      path: '/srv',
      parent: '/',
      entries: [{ name: 'app', path: '/srv/app' }],
    })
    mocks.shouldInjectCurrentProject.mockReturnValue(true)
    mocks.supportsNativeProjectDirectoryPicker.mockReturnValue(true)
  })

  it('closes when the backdrop is clicked', () => {
    const onClose = vi.fn()
    const { container } = render(
      <I18nProvider>
        <ToastProvider>
          <AddProjectModal
            api={api}
            isOpen
            onClose={onClose}
            onAdd={() => {}}
          />
        </ToastProvider>
      </I18nProvider>
    )
    const backdrop = container.querySelector('[aria-hidden="true"]')

    expect(backdrop).toBeInTheDocument()
    fireEvent.click(backdrop!)

    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('uses the native directory picker when available', async () => {
    const onAdd = vi.fn()
    mocks.pickProjectDirectory.mockResolvedValue('/tmp/demo')
    mocks.probeProject.mockResolvedValue({
      path: '/tmp/demo',
      path_exists: true,
      config_exists: true,
      state_exists: true,
      project_name: 'demo',
      slots: 2,
      status: 'ready',
    })

    render(
      <I18nProvider>
        <ToastProvider>
          <AddProjectModal
            api={api}
            isOpen
            onClose={vi.fn()}
            onAdd={onAdd}
          />
        </ToastProvider>
      </I18nProvider>
    )

    fireEvent.click(screen.getByRole('button', { name: 'Browse folder' }))

    await waitFor(() => {
      expect(mocks.pickProjectDirectory).toHaveBeenCalledTimes(1)
      expect(mocks.probeProject).toHaveBeenCalledWith('/tmp/demo')
      expect(screen.getByText('demo')).toBeInTheDocument()
    })
    expect(screen.getByRole('button', { name: 'Browse folder' })).not.toBeDisabled()
  })

  it('fills and scans the current server directory in one click', async () => {
    mocks.probeProject.mockResolvedValue({
      path: '/tmp/demo',
      path_exists: true,
      config_exists: true,
      state_exists: true,
      project_name: 'demo',
      slots: 2,
      status: 'ready',
    })

    render(
      <I18nProvider>
        <ToastProvider>
          <AddProjectModal
            api={api}
            isOpen
            onClose={vi.fn()}
            onAdd={vi.fn()}
          />
        </ToastProvider>
      </I18nProvider>
    )

    fireEvent.click(await screen.findByRole('button', { name: 'Use current directory' }))

    await waitFor(() => {
      expect(screen.getByDisplayValue('/tmp/demo')).toBeInTheDocument()
      expect(mocks.probeProject).toHaveBeenCalledWith('/tmp/demo')
      expect(screen.getByText('demo')).toBeInTheDocument()
    })
  })

  it('allows adding an existing project directory that still needs initialization', async () => {
    const onAdd = vi.fn().mockResolvedValue(undefined)
    const onClose = vi.fn()
    mocks.probeProject.mockResolvedValue({
      path: '/tmp/fresh',
      path_exists: true,
      config_exists: false,
      state_exists: false,
      project_name: 'fresh',
      slots: 0,
      status: 'needs_init',
    })

    render(
      <I18nProvider>
        <ToastProvider>
          <AddProjectModal
            api={api}
            isOpen
            onClose={onClose}
            onAdd={onAdd}
          />
        </ToastProvider>
      </I18nProvider>
    )

    fireEvent.change(screen.getByLabelText('Project Directory'), { target: { value: '/tmp/fresh' } })
    fireEvent.click(screen.getByRole('button', { name: 'Scan' }))

    await waitFor(() => {
      expect(screen.getByText('fresh')).toBeInTheDocument()
      expect(screen.getByText('No config yet — add it, then initialize from Overview')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByRole('button', { name: 'Add Project' }))

    await waitFor(() => {
      expect(onAdd).toHaveBeenCalledWith({ path: '/tmp/fresh' })
      expect(onClose).toHaveBeenCalledTimes(1)
    })
  })

  it('does not show a current-directory shortcut in desktop mode', async () => {
    mocks.shouldInjectCurrentProject.mockReturnValue(false)

    render(
      <I18nProvider>
        <ToastProvider>
          <AddProjectModal
            api={api}
            isOpen
            onClose={vi.fn()}
            onAdd={vi.fn()}
          />
        </ToastProvider>
      </I18nProvider>
    )

    await waitFor(() => {
      expect(mocks.getApiInfo).toHaveBeenCalled()
    })
    expect(screen.queryByRole('button', { name: 'Use current directory' })).not.toBeInTheDocument()
  })

  it('adds an SSH project from a saved SSH target and remote directory', async () => {
    const onAdd = vi.fn().mockResolvedValue(undefined)

    render(
      <I18nProvider>
        <ToastProvider>
          <AddProjectModal
            api={api}
            isOpen
            onClose={vi.fn()}
            onAdd={onAdd}
          />
        </ToastProvider>
      </I18nProvider>
    )

    await waitFor(() => {
      expect(mocks.getApiInfo).toHaveBeenCalled()
    })
    fireEvent.click(screen.getByRole('button', { name: 'SSH machine' }))
    fireEvent.click(await screen.findByRole('button', { name: 'Saved SSH targets' }))
    fireEvent.click(screen.getByRole('option', { name: 'gpu-dev' }))
    expect(screen.getByDisplayValue('gpu-dev')).toBeInTheDocument()
    expect(screen.getByDisplayValue('ubuntu')).toBeInTheDocument()
    expect(screen.getByDisplayValue('2222')).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Remote directory'), { target: { value: '/srv/app' } })
    fireEvent.click(screen.getByRole('button', { name: 'Add SSH Project' }))

    await waitFor(() => {
      expect(onAdd).toHaveBeenCalledWith({
        name: 'app',
        agent: 'codex',
        remote: {
          host: 'gpu-dev',
          user: 'ubuntu',
          port: 2222,
          cwd: '/srv/app',
        },
      })
    })
  })

  it('uses a compact SSH target selector with connection details', async () => {
    render(
      <I18nProvider>
        <ToastProvider>
          <AddProjectModal
            api={api}
            isOpen
            onClose={vi.fn()}
            onAdd={vi.fn()}
          />
        </ToastProvider>
      </I18nProvider>
    )

    fireEvent.click(screen.getByRole('button', { name: 'SSH machine' }))

    expect(await screen.findByRole('button', { name: 'Saved SSH targets' })).toBeInTheDocument()
    expect(screen.queryByRole('combobox', { name: 'Saved SSH targets' })).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Saved SSH targets' }))
    fireEvent.click(screen.getByRole('option', { name: 'gpu-dev' }))

    expect(screen.getByDisplayValue('gpu-dev')).toBeInTheDocument()
    expect(screen.getByText('ubuntu@gpu.example.com:2222')).toBeInTheDocument()
    expect(screen.getByText('Selected target')).toBeInTheDocument()
  })

  it('adds an SSH project with the selected agent', async () => {
    const onAdd = vi.fn().mockResolvedValue(undefined)

    render(
      <I18nProvider>
        <ToastProvider>
          <AddProjectModal
            api={api}
            isOpen
            onClose={vi.fn()}
            onAdd={onAdd}
          />
        </ToastProvider>
      </I18nProvider>
    )

    fireEvent.click(screen.getByRole('button', { name: 'SSH machine' }))
    fireEvent.change(await screen.findByLabelText(/ssh host/i), { target: { value: 'gpu-dev' } })
    fireEvent.change(screen.getByLabelText('Remote directory'), { target: { value: '/srv/app' } })
    fireEvent.change(screen.getByLabelText('Agent'), { target: { value: 'claude' } })
    fireEvent.click(screen.getByRole('button', { name: 'Add SSH Project' }))

    await waitFor(() => {
      expect(onAdd).toHaveBeenCalledWith({
        name: 'app',
        agent: 'claude',
        remote: {
          host: 'gpu-dev',
          user: null,
          port: null,
          cwd: '/srv/app',
        },
      })
    })
  })

  it('browses directories on the selected SSH target', async () => {
    mocks.listRemoteDirectories.mockImplementation((_remote, path) => Promise.resolve(
      path === '/srv/app'
        ? { path: '/srv/app', parent: '/srv', entries: [] }
        : { path: '/srv', parent: '/', entries: [{ name: 'app', path: '/srv/app' }], truncated: true }
    ))

    render(
      <I18nProvider>
        <ToastProvider>
          <AddProjectModal
            api={api}
            isOpen
            onClose={vi.fn()}
            onAdd={vi.fn()}
          />
        </ToastProvider>
      </I18nProvider>
    )

    fireEvent.click(screen.getByRole('button', { name: 'SSH machine' }))
    fireEvent.click(await screen.findByRole('button', { name: 'Saved SSH targets' }))
    fireEvent.click(screen.getByRole('option', { name: 'gpu-dev' }))
    fireEvent.change(screen.getByLabelText('Remote directory'), { target: { value: '/srv' } })
    fireEvent.click(screen.getByRole('button', { name: 'Browse remote directory' }))

    await waitFor(() => {
      expect(mocks.listRemoteDirectories).toHaveBeenCalledWith(
        { host: 'gpu-dev', user: 'ubuntu', port: 2222 },
        '/srv'
      )
    })

    expect(screen.getByText('Showing the first 1 directories. Narrow the path to browse more.')).toBeInTheDocument()

    fireEvent.click(await screen.findByRole('button', { name: 'Open /srv/app' }))

    await waitFor(() => {
      expect(screen.getByDisplayValue('/srv/app')).toBeInTheDocument()
    })
  })

  it('does nothing when the native directory picker is cancelled', async () => {
    mocks.pickProjectDirectory.mockResolvedValue(null)

    render(
      <I18nProvider>
        <ToastProvider>
          <AddProjectModal
            api={api}
            isOpen
            onClose={vi.fn()}
            onAdd={vi.fn()}
          />
        </ToastProvider>
      </I18nProvider>
    )

    fireEvent.click(screen.getByRole('button', { name: 'Browse folder' }))

    await waitFor(() => {
      expect(mocks.pickProjectDirectory).toHaveBeenCalledTimes(1)
    })
    expect(mocks.probeProject).not.toHaveBeenCalled()
  })
})
