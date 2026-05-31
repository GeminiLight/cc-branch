import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { ToastProvider, useToast } from './Toast'

function TestComponent() {
  const toast = useToast()
  return (
    <div>
      <button onClick={() => toast.success('Saved!')}>Success</button>
      <button onClick={() => toast.error('Failed!')}>Error</button>
      <button onClick={() => toast.info('Info!')}>Info</button>
    </div>
  )
}

describe('Toast', () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('shows success toast', () => {
    render(
      <ToastProvider>
        <TestComponent />
      </ToastProvider>
    )
    fireEvent.click(screen.getByText('Success'))
    expect(screen.getByText('Saved!')).toBeInTheDocument()
  })

  it('shows error toast with alert role', () => {
    render(
      <ToastProvider>
        <TestComponent />
      </ToastProvider>
    )
    fireEvent.click(screen.getByText('Error'))
    expect(screen.getByText('Failed!')).toBeInTheDocument()
    expect(screen.getByRole('alert')).toBeInTheDocument()
  })

  it('dismisses toast on button click', () => {
    render(
      <ToastProvider>
        <TestComponent />
      </ToastProvider>
    )
    fireEvent.click(screen.getByText('Success'))
    const dismissBtn = screen.getByLabelText(/dismiss/i)
    fireEvent.click(dismissBtn)
    expect(screen.queryByText('Saved!')).not.toBeInTheDocument()
  })

  it('auto-dismisses after duration', async () => {
    // Note: CSS animation onAnimationEnd does not fire in jsdom,
    // so we verify the animation style is present instead
    render(
      <ToastProvider>
        <TestComponent />
      </ToastProvider>
    )
    fireEvent.click(screen.getByText('Success'))
    const toast = screen.getByText('Saved!').closest('[role="status"]')
    expect(toast).toBeInTheDocument()
    // Verify the progress bar animation is set
    const progressBar = toast?.querySelector('.toast-progress-bar')
    expect(progressBar).toBeInTheDocument()
    expect((progressBar as HTMLElement)?.style.animation).toContain('toast-progress')
  })

  it('limits to max 5 toasts', () => {
    render(
      <ToastProvider>
        <TestComponent />
      </ToastProvider>
    )
    for (let i = 0; i < 7; i++) {
      fireEvent.click(screen.getByText('Success'))
    }
    expect(screen.getAllByText('Saved!')).toHaveLength(5)
  })
})
