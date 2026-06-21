import React from 'react'
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import Rankings from './pages/Rankings'
import './index.css'

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-slate-950 text-slate-50 font-sans">
        <nav className="border-b border-slate-800 bg-slate-900/50 backdrop-blur-md sticky top-0 z-50">
          <div className="container mx-auto px-4 h-16 flex items-center justify-between">
            <div className="flex items-center gap-6">
              <Link to="/" className="text-xl font-bold bg-gradient-to-r from-blue-400 to-indigo-500 bg-clip-text text-transparent">
                Candidate Intelligence
              </Link>
              <div className="flex gap-4 text-sm font-medium text-slate-300">
                <Link to="/" className="hover:text-white transition-colors">Dashboard</Link>
                <Link to="/rankings" className="hover:text-white transition-colors">Rankings</Link>
              </div>
            </div>
          </div>
        </nav>

        <main className="container mx-auto px-4 py-8">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/rankings" element={<Rankings />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}

export default App
