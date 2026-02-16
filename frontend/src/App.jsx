import { useState } from 'react'
import './App.css'
import ModuleList from './components/ModuleList'
import ModuleDetail from './components/ModuleDetail'
import CombineTool from './components/CombineTool'

function App() {
  const [view, setView] = useState('modules') // 'modules' | 'combine'
  const [selectedModule, setSelectedModule] = useState(null)

  return (
    <div className="app">
      <header>
        <h1>WisMAP</h1>
        <nav>
          <button
            className={view === 'modules' ? 'active' : ''}
            onClick={() => { setView('modules'); setSelectedModule(null) }}
          >
            Modules
          </button>
          <button
            className={view === 'combine' ? 'active' : ''}
            onClick={() => { setView('combine'); setSelectedModule(null) }}
          >
            Combine
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
      {view === 'combine' && <CombineTool />}

      <footer>Copyright &copy; 2026 RAKwireless Technology Limited. All rights reserved.</footer>
    </div>
  )
}

export default App
