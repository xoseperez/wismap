import { useState, useEffect } from 'react'
import { fetchItem } from '../api'
import { exportModuleMarkdown, exportModulePdf } from '../utils/exportModule'

function normalizeI2C(info) {
  if (Array.isArray(info.i2c_addresses) && info.i2c_addresses.length > 0) return info.i2c_addresses
  if (typeof info.i2c_address === 'string' && info.i2c_address) return [info.i2c_address]
  return null
}

export default function ModuleDetail({ moduleId, onBack, onSelect, onTagClick }) {
  const [info, setInfo] = useState(null)
  const [showNc, setShowNc] = useState(false)
  const [copied, setCopied] = useState(false)
  const [exporting, setExporting] = useState(false)

  useEffect(() => {
    fetchItem(moduleId, showNc).then(setInfo)
  }, [moduleId, showNc])

  if (!info) return <p>Loading...</p>

  const i2cAddrs = normalizeI2C(info)
  const datasheetUrl = info.datasheet_url || info.documentation
  const description = info.name || info.description
  const isBase = info._endpoint === 'base'
  const isCore = info._endpoint === 'core'
  const pinMapping = info.pin_mapping
  const slotsTable = info.pin_mapping_table

  return (
    <div className="module-detail">
      <button className="back-btn" onClick={onBack}>&larr; Back to list</button>

      <h2>{info.id}</h2>
      <dl className="meta">
        <dt>Type</dt><dd>{info.type}</dd>
        {info.category && <><dt>Category</dt><dd>{info.category}</dd></>}
        <dt>Description</dt><dd>{description}</dd>
        {info.chip && <><dt>Chip</dt><dd>{info.chip}</dd></>}
        {isCore && info.mcu && <><dt>MCU</dt><dd>{info.mcu}</dd></>}
        {isCore && info.lora_chip && <><dt>LoRa chip</dt><dd>{info.lora_chip}</dd></>}
        {isCore && info.peripherals && info.peripherals.length > 0 && (
          <><dt>Peripherals</dt><dd>{info.peripherals.join(', ')}</dd></>
        )}
        {isBase && info.form_factor && <><dt>Form factor</dt><dd>{info.form_factor}</dd></>}
        {datasheetUrl && (
          <><dt>Documentation</dt>
          <dd><a href={datasheetUrl} target="_blank" rel="noreferrer">{datasheetUrl}</a></dd></>
        )}
        {info.double !== null && info.double !== undefined && (
          <><dt>Long (double)</dt><dd>{info.double ? 'Yes' : 'No'}</dd></>
        )}
        {i2cAddrs && <><dt>I2C Address</dt><dd>{i2cAddrs.join(', ')}</dd></>}
        {info.tags && info.tags.length > 0 && (
          <><dt>Tags</dt>
          <dd><span className="tag-list">
            {info.tags.map(tag => (
              <button key={tag} className="tag-badge" onClick={() => onTagClick(tag)}>{tag}</button>
            ))}
          </span></dd></>
        )}

        {info.notes && info.notes.length > 0 && (
          <><dt>Notes</dt>
          <dd><ul style={{ paddingLeft: '12px' }}>{info.notes.map((n, i) => <li key={i}>{n}</li>)}</ul></dd></>
        )}

      </dl>

      {pinMapping && pinMapping.length > 0 && (
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
              {pinMapping.map((r, i) => (
                <tr key={i}><td>{r.pin}</td><td>{r.function}</td></tr>
              ))}
            </tbody>
          </table>
        </>
      )}

      {slotsTable && (
        <>
          <h3 style={{ marginTop: '1rem' }}>Slot pin mapping</h3>
          <div style={{ overflowX: 'auto' }}>
            <table>
              <thead>
                <tr>
                  <th>PIN</th>
                  {slotsTable.columns.map(c => <th key={c}>{c}</th>)}
                </tr>
              </thead>
              <tbody>
                {slotsTable.rows.map((row, i) => (
                  <tr key={i}>
                    <td>{row.pin}</td>
                    {slotsTable.columns.map(c => (
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
            <img key={i} src={url} alt={`${info.id} schematic ${i + 1}`} style={{ maxWidth: '100%', display: 'block' }} />
          ))}
        </>
      )}

      {info.images && info.images.length > 0 && (
        <>
          <h3 style={{ marginTop: '1rem' }}>Images</h3>
          {info.images.map((url, i) => (
            <img key={i} src={url} alt={`${info.id} ${i + 1}`} style={{ maxWidth: '400px', display: 'block' }} />
          ))}
        </>
      )}

      <div className="docs">
        <h3>Actions</h3>
        <ul>
          <li>
            <a href={`#module/${info.id.toLowerCase()}`} onClick={e => {
              e.preventDefault()
              window.location.hash = `#module/${info.id.toLowerCase()}`
              const url = `${window.location.origin}${window.location.pathname}#module/${info.id.toLowerCase()}`
              navigator.clipboard.writeText(url).then(() => {
                setCopied(true)
                setTimeout(() => setCopied(false), 2000)
              })
            }}>
              {copied ? 'Copied!' : 'Copy link to this module'}
            </a>
          </li>
          <li><a href="#" onClick={e => { e.preventDefault(); exportModuleMarkdown(info) }}>Export as Markdown</a></li>
          <li><a href="#" onClick={async e => {
            e.preventDefault()
            setExporting(true)
            try { await exportModulePdf(info) } finally { setExporting(false) }
          }}>{exporting ? 'Exporting...' : 'Export as PDF'}</a></li>
        </ul>
      </div>

    </div>
  )
}
