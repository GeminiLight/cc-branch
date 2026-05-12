import { describe, it, expect, vi } from 'vitest'
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
  }),
  probeProject: vi.fn(),
  pickProjectDirectory: vi.fn(),
  supportsNativeProjectDirectoryPicker: vi.fn().mockReturnValue(true),
}))

const api = {
  getApiInfo: mocks.getApiInfo,
  probeProject: mocks.probeProject,
  pickProjectDirectory: mocks.pickProjectDirectory,
  supportsNativeProjectDirectoryPicker: mocks.supportsNativeProjectDirectoryPicker,
} as unknown as APIClient

describe('AddProjectModal', () => {
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
  })
})
