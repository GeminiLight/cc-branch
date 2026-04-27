import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import Modal from './Modal'
import { I18nProvider } from '../../i18n'

function renderModal(onClose = vi.fn()) {
  const result = render(
    <I18nProvider>
      <Modal
        isOpen
        onClose={onClose}
        title="Confirm action"
        description="This should close from the backdrop."
        confirmText="Confirm"
        onConfirm={() => {}}
      />
    </I18nProvider>
  )
  return { ...result, onClose }
}

describe('Modal', () => {
  it('closes when the backdrop is clicked', () => {
    const { container, onClose } = renderModal()
    const backdrop = container.querySelector('[aria-hidden="true"]')

    expect(backdrop).toBeInTheDocument()
    fireEvent.click(backdrop!)

    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('keeps footer buttons clickable above the backdrop', () => {
    const onConfirm = vi.fn()
    render(
      <I18nProvider>
        <Modal
          isOpen
          onClose={() => {}}
          title="Confirm action"
          confirmText="Confirm"
          onConfirm={onConfirm}
        />
      </I18nProvider>
    )

    fireEvent.click(screen.getByRole('button', { name: 'Confirm' }))

    expect(onConfirm).toHaveBeenCalledTimes(1)
  })
})
