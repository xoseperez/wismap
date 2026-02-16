export default function FunctionTable({ result }) {
  if (!result) return null

  const { columns, slot_module, function_table, conflicts, documentation, notes } = result
  const conflictFns = new Set(conflicts.functions)

  // Build module id -> documentation URL lookup from the documentation strings
  const docUrls = {}
  for (const d of documentation) {
    const idx = d.lastIndexOf(': http')
    if (idx !== -1) {
      const url = d.slice(idx + 2)
      // Match module id from slot_module values against the description prefix
      for (const modId of Object.values(slot_module)) {
        if (modId !== 'EMPTY' && modId !== 'BLOCKED' && d.toLowerCase().startsWith(modId.toLowerCase())) {
          docUrls[modId] = url
        }
      }
    }
  }

  return (
    <div>
      <div className="function-table-wrap">
        <table className="function-table">
          <thead>
            <tr>{columns.map(c => <th key={c}>{c}</th>)}</tr>
          </thead>
          <tbody>
            <tr className="module-row">
              <td>MODULE</td>
              {Object.values(slot_module).map((v, i) => (
                <td key={i}>
                  {docUrls[v]
                    ? <a href={docUrls[v]} target="_blank" rel="noreferrer">{v.toUpperCase()}</a>
                    : v.toUpperCase()
                  }
                </td>
              ))}
            </tr>
            {Object.entries(function_table).map(([fn, row]) => (
              <tr key={fn} className={conflictFns.has(fn) ? 'conflict' : ''}>
                {row.map((cell, i) => <td key={i}>{cell}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {(conflicts.notes.length > 0 || notes.length > 0) && (
        <div className="notes">
          <h3>Notes</h3>
          <ul>
            {conflicts.notes.map((n, i) => (
              <li key={'c' + i} className="conflict-note">{n}</li>
            ))}
            {notes.map((n, i) => <li key={'n' + i}>{n}</li>)}
          </ul>
        </div>
      )}

      {documentation.length > 0 && (
        <div className="docs">
          <h3>Documentation</h3>
          <ul>
            {documentation.map((d, i) => {
              const idx = d.lastIndexOf(': http')
              if (idx === -1) return <li key={i}>{d}</li>
              const label = d.slice(0, idx)
              const url = d.slice(idx + 2)
              return (
                <li key={i}>
                  {label}: <a href={url} target="_blank" rel="noreferrer">{url}</a>
                </li>
              )
            })}
          </ul>
        </div>
      )}
    </div>
  )
}
