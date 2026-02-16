import { useState, useEffect, useMemo } from 'react'
import { fetchModules } from '../api'

const TYPES = ['All', 'WisBase', 'WisCore', 'WisIO', 'WisSensor', 'WisPower', 'WisModule', 'Accessories']

export default function ModuleList({ onSelect }) {
  const [modules, setModules] = useState([])
  const [typeFilter, setTypeFilter] = useState('All')
  const [search, setSearch] = useState('')

  useEffect(() => {
    fetchModules().then(setModules)
  }, [])

  const filtered = useMemo(() => {
    const q = search.toLowerCase()
    return modules.filter(m => {
      if (typeFilter !== 'All' && m.type !== typeFilter) return false
      if (q && !m.id.includes(q) && !m.description.toLowerCase().includes(q)) return false
      return true
    })
  }, [modules, typeFilter, search])

  return (
    <div>
      <div className="filters">
        <select value={typeFilter} onChange={e => setTypeFilter(e.target.value)}>
          {TYPES.map(t => <option key={t} value={t}>{t}</option>)}
        </select>
        <input
          type="text"
          placeholder="Search modules..."
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
        <span>{filtered.length} modules</span>
      </div>
      <table>
        <thead>
          <tr>
            <th>Module</th>
            <th>Type</th>
            <th>Description</th>
          </tr>
        </thead>
        <tbody>
          {filtered.map(m => (
            <tr key={m.id} onClick={() => onSelect(m.id)} style={{ cursor: 'pointer' }}>
              <td>{m.id.toUpperCase()}</td>
              <td>{m.type}</td>
              <td>{m.description}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
