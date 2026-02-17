import { useState, useEffect } from 'react'
import './App.css'
import ModuleList from './components/ModuleList'
import ModuleDetail from './components/ModuleDetail'
import CombineTool from './components/CombineTool'

function parseHash(hash) {
  // Expected format: #combine/base/mod1/mod2/...
  if (!hash.startsWith('#combine/')) return null
  const parts = hash.slice('#combine/'.length).split('/')
  if (parts.length < 1 || !parts[0]) return null
  return { base: parts[0], modules: parts.slice(1) }
}

function App() {
  const [view, setView] = useState('combine') // 'modules' | 'combine'
  const [selectedModule, setSelectedModule] = useState(null)
  const [initialConfig, setInitialConfig] = useState(null)
  const [resetKey, setResetKey] = useState(0)

  useEffect(() => {
    const apply = () => {
      const config = parseHash(window.location.hash)
      if (config) {
        setInitialConfig(config)
        setView('combine')
        setSelectedModule(null)
      }
    }
    apply()
    window.addEventListener('hashchange', apply)
    return () => window.removeEventListener('hashchange', apply)
  }, [])

  return (
    <div className="app">
      <header>
        <h1 style={{ cursor: 'pointer' }} onClick={() => { setResetKey(k => k + 1); setSelectedModule(null) }}>WisMAP</h1>
        <nav>
          <button
            className={view === 'combine' ? 'active' : ''}
            onClick={() => setView('combine')}
          >
            Combine
          </button>
          <button
            className={view === 'modules' ? 'active' : ''}
            onClick={() => setView('modules')}
          >
            Modules
          </button>
        </nav>
      </header>

      <div key={'modules-' + resetKey} style={{ display: view === 'modules' ? undefined : 'none' }}>
        {!selectedModule && (
          <ModuleList onSelect={setSelectedModule} />
        )}
        {selectedModule && (
          <ModuleDetail
            moduleId={selectedModule}
            onBack={() => setSelectedModule(null)}
            onSelect={setSelectedModule}
          />
        )}
      </div>
      <div key={'combine-' + resetKey} style={{ display: view === 'combine' ? undefined : 'none' }}>
        <CombineTool
          initialConfig={initialConfig}
          onConfigConsumed={() => setInitialConfig(null)}
        />
      </div>

      <footer>Copyright &copy; 2026 RAKwireless Technology Limited. All rights reserved.</footer>
    </div>
  )
}

export default App
