import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import Tooltip from './Tooltip'

describe('Tooltip', () => {
  it('renders in a portal so clipped containers do not cut it off', async () => {
    const { container } = render(
      <div data-testid="clipping-parent" className="overflow-hidden">
        <Tooltip content="Open the project terminal" delay={0}>
          <button type="button">Open</button>
        </Tooltip>
      </div>
    )

    fireEvent.mouseEnter(screen.getByRole('button', { name: 'Open' }))

    const tooltip = await screen.findByRole('tooltip')
    expect(container).not.toContainElement(tooltip)
    expect(document.body).toContainElement(tooltip)
    expect(tooltip).toHaveStyle({ position: 'fixed' })
  })
})
