import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import Dropdown from './Dropdown'

describe('Dropdown', () => {
  const originalRect = HTMLElement.prototype.getBoundingClientRect

  beforeEach(() => {
    HTMLElement.prototype.getBoundingClientRect = vi.fn(() => ({
      x: 24,
      y: 40,
      width: 264,
      height: 36,
      top: 40,
      right: 288,
      bottom: 76,
      left: 24,
      toJSON: () => ({}),
    }))
  })

  afterEach(() => {
    HTMLElement.prototype.getBoundingClientRect = originalRect
  })

  it('sizes the portal menu to at least the trigger width', () => {
    render(
      <Dropdown
        align="left"
        value="terminal"
        onChange={() => undefined}
        items={[
          { label: 'System Terminal', value: 'terminal' },
          { label: 'VS Code', value: 'vscode' },
        ]}
        trigger={
          <span className="h-9 px-3 flex items-center">
            Open with System Terminal
          </span>
        }
      />
    )

    fireEvent.click(screen.getByRole('button'))

    expect(screen.getByRole('listbox')).toHaveStyle({ width: '264px' })
  })

  it('renders the menu in a portal outside the trigger container', () => {
    const { container } = render(
      <div data-testid="clipping-parent" className="overflow-hidden">
        <Dropdown
          value="terminal"
          onChange={() => undefined}
          items={[{ label: 'System Terminal', value: 'terminal' }]}
          trigger={<span>Open with System Terminal</span>}
        />
      </div>
    )

    fireEvent.click(screen.getByRole('button'))

    const menu = screen.getByRole('listbox')
    expect(container).not.toContainElement(menu)
    expect(document.body).toContainElement(menu)
  })

  it('does not steal focus on mount', () => {
    render(
      <Dropdown
        value="terminal"
        onChange={() => undefined}
        items={[{ label: 'System Terminal', value: 'terminal' }]}
        trigger={<span>Open with System Terminal</span>}
      />
    )

    expect(screen.getByRole('button')).not.toHaveFocus()
  })

  it('restores focus to the trigger after closing', () => {
    render(
      <Dropdown
        value="terminal"
        onChange={() => undefined}
        items={[{ label: 'System Terminal', value: 'terminal' }]}
        trigger={<span>Open with System Terminal</span>}
      />
    )

    const trigger = screen.getByRole('button')
    fireEvent.click(trigger)
    fireEvent.keyDown(document, { key: 'Escape' })

    expect(trigger).toHaveFocus()
  })

  it('does not pull focus back when closing from an outside click', () => {
    render(
      <>
        <Dropdown
          value="terminal"
          onChange={() => undefined}
          items={[{ label: 'System Terminal', value: 'terminal' }]}
          trigger={<span>Open with System Terminal</span>}
        />
        <button type="button">Outside action</button>
      </>
    )

    const trigger = screen.getByRole('button', { name: 'Open with System Terminal' })
    const outside = screen.getByRole('button', { name: 'Outside action' })
    fireEvent.click(trigger)
    outside.focus()
    fireEvent.mouseDown(outside)

    expect(outside).toHaveFocus()
  })
})
