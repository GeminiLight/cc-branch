import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useRelativeTime } from './useRelativeTime'

describe('useRelativeTime', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('returns "--" when timestamp is null', () => {
    const { result } = renderHook(() => useRelativeTime(null))
    expect(result.current).toBe('--')
  })

  it('returns "just now" for recent timestamps', () => {
    const now = Date.now()
    const { result } = renderHook(() => useRelativeTime(now - 5000))
    expect(result.current).toBe('just now')
  })

  it('returns seconds ago', () => {
    const now = Date.now()
    const { result } = renderHook(() => useRelativeTime(now - 45000))
    expect(result.current).toBe('45s ago')
  })

  it('returns minutes ago', () => {
    const now = Date.now()
    const { result } = renderHook(() => useRelativeTime(now - 5 * 60 * 1000))
    expect(result.current).toBe('5m ago')
  })

  it('returns hours ago', () => {
    const now = Date.now()
    const { result } = renderHook(() => useRelativeTime(now - 3 * 60 * 60 * 1000))
    expect(result.current).toBe('3h ago')
  })

  it('returns days ago', () => {
    const now = Date.now()
    const { result } = renderHook(() => useRelativeTime(now - 2 * 24 * 60 * 60 * 1000))
    expect(result.current).toBe('2d ago')
  })

  it('updates every 30 seconds', () => {
    const now = Date.now()
    const { result } = renderHook(() => useRelativeTime(now - 59 * 1000))
    expect(result.current).toBe('59s ago')

    act(() => {
      vi.advanceTimersByTime(30000)
    })
    expect(result.current).toBe('1m ago')
  })
})
