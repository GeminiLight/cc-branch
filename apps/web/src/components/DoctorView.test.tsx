import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import DoctorView from './DoctorView'
import { I18nProvider } from '../i18n'

const mocks = vi.hoisted(() => ({
  doctorResult: {
    current: null as unknown,
  },
}))

vi.mock('../hooks', () => ({
  useDoctor: () => mocks.doctorResult.current,
}))

function renderDoctorView() {
  return render(
    <I18nProvider>
      <DoctorView projectPath="/tmp/demo" />
    </I18nProvider>
  )
}

describe('DoctorView summary', () => {
  beforeEach(() => {
    mocks.doctorResult.current = {
      data: {
        report: [
          'Workspace:',
          '✓ config: .cc-branch.yaml found',
          '✗ tmux: not installed',
          '→ brew install tmux',
          '⚠ agent: codex CLI not found',
          '',
        ].join('\n'),
      },
      error: null,
      isLoading: false,
      isFetching: false,
      refetch: vi.fn(),
    }
  })

  it('summarizes blocking issues and warnings before the detailed checks', () => {
    renderDoctorView()

    expect(screen.getByText('1 issue')).toBeInTheDocument()
    expect(screen.getByText('1 warning')).toBeInTheDocument()
    expect(screen.getByText('Action needed before this workspace is healthy.')).toBeInTheDocument()
  })
})
