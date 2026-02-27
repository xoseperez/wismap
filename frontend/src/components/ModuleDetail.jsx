import { useState, useEffect } from 'react'
import { fetchModuleInfo } from '../api'

export default function ModuleDetail({ moduleId, onBack, onSelect, onTagClick }) {
  const [info, setInfo] = useState(null)
  const [showNc, setShowNc] = useState(false)

  useEffect(() => {
    fetchModuleInfo(moduleId, showNc).then(setInfo)
  }, [moduleId, showNc])

  if (!info) return <p>Loading...</p>

  return (
    <div className="module-detail">
      <button className="back-btn" onClick={onBack}>&larr; Back to list</button>

      <h2>{info.id.toUpperCase()}</h2>
      <dl className="meta">
        <dt>Type</dt><dd>{info.type}</dd>
        <dt>Description</dt><dd>{info.description}</dd>
        <dt>Documentation</dt>
        <dd><a href={info.documentation} target="_blank" rel="noreferrer">{info.documentation}</a></dd>
        {info.double !== null && <><dt>Long (double)</dt><dd>{info.double ? 'Yes' : 'No'}</dd></>}
        {info.i2c_address && <><dt>I2C Address</dt><dd>{info.i2c_address}</dd></>}
        {info.tags && info.tags.length > 0 && (
          <><dt>Tags</dt>
          <dd><span className="tag-list">
            {info.tags.map(tag => (
              <button key={tag} className="tag-badge" onClick={() => onTagClick(tag)}>{tag}</button>
            ))}
          </span></dd></>
        )}

        {info.notes && info.notes.length > 0 && <><dt>Notes</dt><dd><ul style={{ paddingLeft: '12px' }}>{info.notes.map((n, i) => <li key={i}>{n}</li>)}</ul></dd></>}

      </dl>

      {info.mapping && info.mapping.length > 0 && (
        <>
          <h3>
            Pin mapping
            <label style={{ fontWeight: 'normal', fontSize: '0.8rem', marginLeft: '1rem' }}>
              <input type="checkbox" checked={showNc} onChange={e => setShowNc(e.target.checked)} />
              {' '}Show NC pins
            </label>
          </h3>
          <table>
            <thead><tr><th>PIN</th><th>Function</th></tr></thead>
            <tbody>
              {info.mapping.map((r, i) => (
                <tr key={i}><td>{r.pin}</td><td>{r.function}</td></tr>
              ))}
            </tbody>
          </table>
        </>
      )}

      {info.slots_table && (
        <>
          <h3 style={{ marginTop: '1rem' }}>Slot pin mapping</h3>
          <div style={{ overflowX: 'auto' }}>
            <table>
              <thead>
                <tr>
                  <th>PIN</th>
                  {info.slots_table.columns.map(c => <th key={c}>{c}</th>)}
                </tr>
              </thead>
              <tbody>
                {info.slots_table.rows.map((row, i) => (
                  <tr key={i}>
                    <td>{row.pin}</td>
                    {info.slots_table.columns.map(c => (
                      <td key={c}>{row[c] || ''}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {info.schematics && info.schematics.length > 0 && (
        <>
          <h3 style={{ marginTop: '1rem' }}>Schematics</h3>
          {info.schematics.map((url, i) => (
            <img key={i} src={url} alt={`${info.id.toUpperCase()} schematic ${i + 1}`} style={{ maxWidth: '100%', display: 'block' }} />
          ))}
        </>
      )}

      {info.images && info.images.length > 0 && (
        <>
          <h3 style={{ marginTop: '1rem' }}>Images</h3>
          {info.images.map((url, i) => (
            <img key={i} src={url} alt={`${info.id.toUpperCase()} ${i + 1}`} style={{ maxWidth: '400px', display: 'block' }} />
          ))}
        </>
      )}

    </div>
  )
}
