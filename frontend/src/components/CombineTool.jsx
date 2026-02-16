import { useState, useEffect, useCallback } from 'react'
import { fetchModules, fetchBaseSlots, postCombine } from '../api'
import FunctionTable from './FunctionTable'

export default function CombineTool() {
  const [bases, setBases] = useState([])
  const [selectedBase, setSelectedBase] = useState('')
  const [slots, setSlots] = useState(null)       // { CORE: { double, double_blocks, eligible_modules }, ... }
  const [assignments, setAssignments] = useState({}) // { CORE: 'rak4631', SENSOR_A: '', ... }
  const [blocked, setBlocked] = useState(new Set())
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)

  // Load base boards
  useEffect(() => {
    fetchModules('WisBase').then(setBases)
  }, [])

  // When base changes, load its slots
  useEffect(() => {
    if (!selectedBase) { setSlots(null); setResult(null); return }
    setResult(null)
    fetchBaseSlots(selectedBase).then(data => {
      setSlots(data)
      // Initialize assignments: empty for all slots
      const init = {}
      for (const name of Object.keys(data)) init[name] = ''
      setAssignments(init)
      setBlocked(new Set())
    })
  }, [selectedBase])

  // Recompute blocked slots when assignments change
  const updateBlocked = useCallback((newAssignments, slotsData) => {
    const blockedSet = new Set()
    if (!slotsData) return blockedSet
    for (const [slotName, slotInfo] of Object.entries(slotsData)) {
      const moduleId = newAssignments[slotName]
      if (!moduleId) continue
      // Check if selected module is a double sensor
      const eligible = slotInfo.eligible_modules.find(m => m.id === moduleId)
      if (!eligible) continue
      // We need to check if the module itself is double — but eligible_modules
      // already filters out doubles for non-double slots. So if a module is in
      // a double slot's eligible list, we check double_blocks.
      if (slotInfo.double_blocks && moduleId) {
        // Fetch module info to check double flag — but we already have it from
        // the eligible list. We don't have the double flag there, so we check
        // if the slot has double_blocks and the module is selected.
        // To properly determine: we need to know if the module is double-size.
        // For simplicity, fetch from the API. But that's async...
        // Instead, let's track this: when a double slot has double_blocks and
        // a module is selected, we assume it might block. The server will handle
        // the actual conflict. For the UI, we check the blocking condition.
      }
    }
    return blockedSet
  }, [])

  const handleAssignment = (slotName, moduleId) => {
    const newAssignments = { ...assignments, [slotName]: moduleId }

    // Recompute blocked: look for double-sensor blocking
    const blockedSet = new Set()
    if (slots) {
      for (const [sName, sInfo] of Object.entries(slots)) {
        const mid = sName === slotName ? moduleId : newAssignments[sName]
        if (!mid || !sInfo.double_blocks) continue
        // Check if the selected module is double-size (it's eligible in a double slot)
        // A module that exists in a double slot's eligible list but NOT in a
        // non-double slot's eligible list is a double-size module.
        // Simpler: check if any non-double slot's eligible list excludes it.
        const isDouble = isModuleDouble(mid, sName, slots)
        if (isDouble) {
          blockedSet.add(sInfo.double_blocks)
          // Clear the blocked slot's assignment
          newAssignments[sInfo.double_blocks] = ''
        }
      }
    }

    setAssignments(newAssignments)
    setBlocked(blockedSet)
  }

  const handleAnalyze = async () => {
    setLoading(true)
    const slotMap = {}
    for (const [name, moduleId] of Object.entries(assignments)) {
      slotMap[name] = moduleId || 'EMPTY'
    }
    // Mark blocked as BLOCKED
    for (const b of blocked) {
      slotMap[b] = 'BLOCKED'
    }
    const data = await postCombine(selectedBase, slotMap)
    setResult(data)
    setLoading(false)
  }

  return (
    <div>
      <div className="combine-layout">
        <div className="slot-panel">
          <label>
            Base Board
            <select value={selectedBase} onChange={e => setSelectedBase(e.target.value)}>
              <option value="">-- Select base --</option>
              {bases.map(b => (
                <option key={b.id} value={b.id}>{b.description}</option>
              ))}
            </select>
          </label>

          {slots && Object.entries(slots).map(([slotName, slotInfo]) => {
            const isBlocked = blocked.has(slotName)
            return (
              <label key={slotName}>
                {slotName}
                {slotInfo.double && ' (double)'}
                {isBlocked && ' - BLOCKED'}
                <select
                  value={isBlocked ? '' : (assignments[slotName] || '')}
                  onChange={e => handleAssignment(slotName, e.target.value)}
                  disabled={isBlocked}
                >
                  <option value="">Empty</option>
                  {slotInfo.eligible_modules.map(m => (
                    <option key={m.id} value={m.id}>{m.description}</option>
                  ))}
                </select>
              </label>
            )
          })}

          {slots && (
            <button
              className="analyze-btn"
              onClick={handleAnalyze}
              disabled={loading}
            >
              {loading ? 'Analyzing...' : 'Analyze'}
            </button>
          )}
        </div>

        <div>
          {result && <FunctionTable result={result} />}
        </div>
      </div>
    </div>
  )
}

/**
 * Determine if a module is double-size by comparing eligible lists.
 * A double module appears in double-capable slot eligible lists but not
 * in non-double slot eligible lists of the same type.
 */
function isModuleDouble(moduleId, currentSlot, slots) {
  const currentType = currentSlot.split('_')[0] // e.g. "SENSOR"
  // Find a non-double slot of the same type
  for (const [name, info] of Object.entries(slots)) {
    if (name === currentSlot) continue
    if (!name.startsWith(currentType)) continue
    if (info.double) continue
    // This is a non-double slot of same type — check if module is NOT eligible
    const found = info.eligible_modules.some(m => m.id === moduleId)
    if (!found) return true // Module is not eligible in non-double slot → it's double
  }
  return false
}
