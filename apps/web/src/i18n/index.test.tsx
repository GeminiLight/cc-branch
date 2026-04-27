import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { I18nProvider, useI18n } from './index'

function TestComponent() {
  const { t, lang, setLang } = useI18n()
  return (
    <div>
      <span data-testid="lang">{lang}</span>
      <span data-testid="title">{t('appTitle')}</span>
      <button onClick={() => setLang('zh')}>Switch</button>
    </div>
  )
}

describe('i18n', () => {
  beforeEach(() => {
    document.documentElement.lang = 'en'
    localStorage.removeItem('cc-branch-lang')
  })

  it('renders with default language', () => {
    render(
      <I18nProvider>
        <TestComponent />
      </I18nProvider>
    )
    expect(screen.getByTestId('lang').textContent).toBe('en')
    expect(screen.getByTestId('title').textContent).toBe('CC Branch')
  })

  it('switches language', () => {
    render(
      <I18nProvider>
        <TestComponent />
      </I18nProvider>
    )
    fireEvent.click(screen.getByText('Switch'))
    expect(screen.getByTestId('lang').textContent).toBe('zh')
    expect(screen.getByTestId('title').textContent).toBe('CC Branch')
    expect(document.documentElement.lang).toBe('zh-CN')
  })

  it('interpolates variables', () => {
    function InterpolationTest() {
      const { t } = useI18n()
      return <span>{t('confirmStop', { name: 'test-slot' })}</span>
    }
    render(
      <I18nProvider>
        <InterpolationTest />
      </I18nProvider>
    )
    expect(screen.getByText('Stop "test-slot"?')).toBeInTheDocument()
  })
})
