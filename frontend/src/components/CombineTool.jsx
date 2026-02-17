import { useState, useEffect, useRef } from 'react'
import { fetchModules, fetchBaseSlots, postCombine } from '../api'
import FunctionTable from './FunctionTable'

export default function CombineTool({ initialConfig, onConfigConsumed }) {
  const [bases, setBases] = useState([])
  const [selectedBase, setSelectedBase] = useState('')
  const [slots, setSlots] = useState(null)       // { CORE: { double, double_blocks, eligible_modules }, ... }
  const [assignments, setAssignments] = useState({}) // { CORE: 'rak4631', SENSOR_A: '', ... }
  const [blocked, setBlocked] = useState(new Set())
  const [result, setResult] = useState(null)
  const pendingConfig = useRef(null)

  // Load base boards
  useEffect(() => {
    fetchModules('WisBase').then(setBases)
  }, [])

  // When initialConfig arrives, store it and select the base
  useEffect(() => {
    if (!initialConfig) return
    pendingConfig.current = initialConfig
    setSelectedBase(initialConfig.base)
    onConfigConsumed()
  }, [initialConfig, onConfigConsumed])

  // When base changes, load its slots
  useEffect(() => {
    if (!selectedBase) { setSlots(null); setResult(null); return }
    setResult(null)
    fetchBaseSlots(selectedBase).then(data => {
      setSlots(data)
      const slotNames = Object.keys(data)

      // Check if we have a pending config to apply
      const config = pendingConfig.current
      if (config && config.base === selectedBase && config.modules.length > 0) {
        pendingConfig.current = null
        const newAssignments = {}
        const blockedSet = new Set()

        for (let i = 0; i < slotNames.length; i++) {
          const slotName = slotNames[i]
          const moduleId = i < config.modules.length ? config.modules[i] : ''
          newAssignments[slotName] = (moduleId && moduleId !== 'empty') ? moduleId : ''
        }

        // Recompute double-sensor blocking
        for (const [sName, sInfo] of Object.entries(data)) {
          const mid = newAssignments[sName]
          if (!mid || !sInfo.double_blocks) continue
          if (isModuleDouble(mid, sName, data)) {
            blockedSet.add(sInfo.double_blocks)
            newAssignments[sInfo.double_blocks] = ''
          }
        }

        setAssignments(newAssignments)
        setBlocked(blockedSet)
      } else {
        // Normal init: empty for all slots
        const init = {}
        for (const name of slotNames) init[name] = ''
        setAssignments(init)
        setBlocked(new Set())
      }
    })
  }, [selectedBase])

  const handleAssignment = (slotName, moduleId) => {
    const newAssignments = { ...assignments, [slotName]: moduleId }

    // Recompute blocked: look for double-sensor blocking
    const blockedSet = new Set()
    if (slots) {
      for (const [sName, sInfo] of Object.entries(slots)) {
        const mid = sName === slotName ? moduleId : newAssignments[sName]
        if (!mid || !sInfo.double_blocks) continue
        const isDouble = isModuleDouble(mid, sName, slots)
        if (isDouble) {
          blockedSet.add(sInfo.double_blocks)
          newAssignments[sInfo.double_blocks] = ''
        }
      }
    }

    setAssignments(newAssignments)
    setBlocked(blockedSet)
  }

  // Auto-analyze whenever assignments change
  useEffect(() => {
    if (!selectedBase || !slots) { setResult(null); return }
    const slotMap = {}
    for (const [name, moduleId] of Object.entries(assignments)) {
      slotMap[name] = moduleId || 'EMPTY'
    }
    for (const b of blocked) {
      slotMap[b] = 'BLOCKED'
    }
    postCombine(selectedBase, slotMap).then(setResult)
  }, [selectedBase, slots, assignments, blocked])

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
