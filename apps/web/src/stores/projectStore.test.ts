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

  it('adds a project', () => {
    useProjectStore.getState().addProject({ id: 'p1', name: 'proj', path: '/path' })
    expect(useProjectStore.getState().projects).toHaveLength(1)
    expect(useProjectStore.getState().activeProjectId).toBe('p1')
  })

  it('prevents duplicate paths', () => {
    useProjectStore.getState().addProject({ id: 'p1', name: 'proj', path: '/path' })
    useProjectStore.getState().addProject({ id: 'p2', name: 'proj2', path: '/path' })
    expect(useProjectStore.getState().projects).toHaveLength(1)
  })

  it('removes a project and updates active', () => {
    useProjectStore.getState().addProject({ id: 'p1', name: 'a', path: '/a' })
    useProjectStore.getState().addProject({ id: 'p2', name: 'b', path: '/b' })
    useProjectStore.getState().removeProject('p1')
    expect(useProjectStore.getState().projects).toHaveLength(1)
    expect(useProjectStore.getState().activeProjectId).toBe('p2')
  })

  it('injects current project', () => {
    useProjectStore.getState().injectCurrentProject('/foo/bar')
    expect(useProjectStore.getState().projects).toHaveLength(1)
    expect(useProjectStore.getState().projects[0].id).toBe('current')
    expect(useProjectStore.getState().projects[0].name).toBe('bar')
    expect(useProjectStore.getState().activeProjectId).toBe('current')
  })

  it('deduplicates on inject when path already exists', () => {
    useProjectStore.getState().addProject({ id: 'p1', name: 'proj', path: '/foo/bar' })
    useProjectStore.getState().injectCurrentProject('/foo/bar')
    expect(useProjectStore.getState().projects).toHaveLength(1)
    expect(useProjectStore.getState().projects[0].id).toBe('current')
  })

  it('getActiveProject selector works', () => {
    useProjectStore.getState().addProject({ id: 'p1', name: 'a', path: '/a' })
    const state = useProjectStore.getState()
    expect(getActiveProject(state)?.id).toBe('p1')
  })
})
