import { describe, it, expect, vi } from 'vitest'
import { render, fireEvent } from '@testing-library/react'
import AddProjectModal from './AddProjectModal'
import { I18nProvider } from '../i18n'
import { ToastProvider } from './ui/Toast'
import type { APIClient } from '../api/client'

const api = {
  getApiInfo: vi.fn().mockResolvedValue({
    port: 8080,
    config_path: '/tmp/demo/.cc-branch.yaml',
    state_path: '/tmp/demo/.cc-branch.state.toml',
  }),
  probeProject: vi.fn(),
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
})
