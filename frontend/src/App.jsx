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
        <h1>WisMAP</h1>
        <nav>
          <button
            className={view === 'combine' ? 'active' : ''}
            onClick={() => { setView('combine'); setSelectedModule(null) }}
          >
            Combine
          </button>
          <button
            className={view === 'modules' ? 'active' : ''}
            onClick={() => { setView('modules'); setSelectedModule(null) }}
          >
            Modules
          </button>
        </nav>
      </header>

      {view === 'modules' && !selectedModule && (
        <ModuleList onSelect={setSelectedModule} />
      )}
      {view === 'modules' && selectedModule && (
        <ModuleDetail
          moduleId={selectedModule}
          onBack={() => setSelectedModule(null)}
          onSelect={setSelectedModule}
        />
      )}
      {view === 'combine' && (
        <CombineTool
          initialConfig={initialConfig}
          onConfigConsumed={() => setInitialConfig(null)}
        />
      )}

      <footer>Copyright &copy; 2026 RAKwireless Technology Limited. All rights reserved.</footer>
    </div>
  )
}

export default App
