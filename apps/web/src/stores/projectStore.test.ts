import { describe, it, expect, beforeEach } from 'vitest'
import { useProjectStore, getActiveProject } from './projectStore'

describe('projectStore', () => {
  beforeEach(() => {
    // Reset store state before each test
    useProjectStore.setState({ projects: [], activeProjectId: null })
  })

  it('starts with empty projects', () => {
    expect(useProjectStore.getState().projects).toEqual([])
    expect(useProjectStore.getState().activeProjectId).toBeNull()
  })

  it('hydrates from backend snapshot', () => {
    useProjectStore.getState().setSnapshot([{ id: 'p1', name: 'proj', path: '/path' }], 'p1')
    expect(useProjectStore.getState().projects).toHaveLength(1)
    expect(useProjectStore.getState().activeProjectId).toBe('p1')
  })

  it('allows selecting active project locally', () => {
    useProjectStore.getState().setSnapshot(
      [
        { id: 'p1', name: 'a', path: '/a' },
        { id: 'p2', name: 'b', path: '/b' },
      ],
      'p1'
    )
    useProjectStore.getState().setActiveProjectId('p2')
    expect(useProjectStore.getState().activeProjectId).toBe('p2')
  })

  it('getActiveProject selector works', () => {
    useProjectStore.getState().setSnapshot([{ id: 'p1', name: 'a', path: '/a' }], 'p1')
    const state = useProjectStore.getState()
    expect(getActiveProject(state)?.id).toBe('p1')
  })
})
