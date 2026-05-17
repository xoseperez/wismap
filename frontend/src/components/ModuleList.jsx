import { useState, useEffect, useMemo } from 'react'
import { fetchAllItems } from '../api'

const TYPES = ['All', 'WisBase', 'WisCore', 'WisIO', 'WisSensor', 'WisPower', 'WisModule', 'Accessories']

export default function ModuleList({ onSelect, typeFilter, onTypeFilterChange, search, onSearchChange }) {
  const [items, setItems] = useState([])

  useEffect(() => {
    fetchAllItems().then(setItems)
  }, [])

  const filtered = useMemo(() => {
    const q = search.toLowerCase()
    return items.filter(m => {
      if (typeFilter !== 'All' && m.type !== typeFilter) return false
      if (q) {
        const idLc = m.id.toLowerCase()
        const nameLc = (m.name || '').toLowerCase()
        const tags = m.tags || []
        if (!idLc.includes(q) && !nameLc.includes(q)
            && !tags.some(tag => tag.includes(q))) return false
      }
      return true
    })
  }, [items, typeFilter, search])

  return (
    <div>
      <div className="filters">
        <select value={typeFilter} onChange={e => onTypeFilterChange(e.target.value)}>
          {TYPES.map(t => <option key={t} value={t}>{t}</option>)}
        </select>
        <input
          type="text"
          placeholder="Search modules..."
          value={search}
          onChange={e => onSearchChange(e.target.value)}
        />
        {(typeFilter !== 'All' || search) && (
          <button onClick={() => { onTypeFilterChange('All'); onSearchChange('') }}>Clear</button>
        )}
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
              <td>{m.id}</td>
              <td>{m.type}</td>
              <td>{m.name}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
