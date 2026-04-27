import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useOnlineStatus } from './useOnlineStatus'

describe('useOnlineStatus', () => {
  beforeEach(() => {
    vi.spyOn(window, 'addEventListener').mockRestore()
    vi.spyOn(window, 'removeEventListener').mockRestore()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('returns current online status', () => {
    const { result } = renderHook(() => useOnlineStatus())
    expect(result.current).toBe(navigator.onLine)
  })

  it('updates when online event fires', () => {
    const { result } = renderHook(() => useOnlineStatus())
    // Simulate going offline
    Object.defineProperty(navigator, 'onLine', { value: false, writable: true, configurable: true })
    act(() => {
      window.dispatchEvent(new Event('offline'))
    })
    expect(result.current).toBe(false)
    // Restore
    Object.defineProperty(navigator, 'onLine', { value: true, writable: true, configurable: true })
  })
})
