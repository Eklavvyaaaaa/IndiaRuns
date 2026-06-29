import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'

export default function Dashboard() {
  const [jd, setJd] = useState('We are looking for a Senior AI Engineer with experience in building production retrieval systems...')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const handleRank = async () => {
    setLoading(true)
    try {
      const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'
      const response = await axios.post(`${baseUrl}/rank`, {
        job_description: jd,
        top_k: 100
      }, { timeout: 30000 })
      // Store results in local storage for now to pass to the rankings page
      localStorage.setItem('rankingResults', JSON.stringify(response.data))
      navigate('/rankings')
    } catch (error) {
      console.error(error)
      alert("Failed to rank candidates. Is the FastAPI backend running?")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-4xl mx-auto space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="space-y-4 text-center">
        <h1 className="text-4xl font-extrabold tracking-tight lg:text-5xl">
          Discover the <span className="text-blue-500">Hidden Gems</span>
        </h1>
        <p className="text-lg text-slate-400">
          Paste your job description below. Our Intelligence Engine will bypass keyword stuffing and rank the top 100 candidates based on true semantic capability, skill trust, and production readiness.
        </p>
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-2xl relative group">
        <div className="absolute -inset-0.5 bg-gradient-to-r from-blue-500 to-purple-600 rounded-xl opacity-20 group-hover:opacity-40 transition duration-500 blur"></div>
        <div className="relative bg-slate-900 rounded-xl p-4">
          <textarea
            value={jd}
            onChange={(e) => setJd(e.target.value)}
            className="w-full h-64 bg-slate-950 border border-slate-800 rounded-lg p-4 text-slate-200 focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none resize-none"
            placeholder="Paste Job Description here..."
          />
          <div className="mt-6 flex justify-end">
            <button
              onClick={handleRank}
              disabled={loading}
              className="bg-blue-600 hover:bg-blue-500 text-white font-semibold py-3 px-8 rounded-lg shadow-lg hover:shadow-blue-500/50 transition-all disabled:opacity-50 flex items-center gap-2"
            >
              🚀 Rank Candidates
            </button>
          </div>
          
          {loading && (
            <div className="absolute inset-0 bg-slate-950/80 backdrop-blur-sm rounded-xl flex flex-col items-center justify-center z-10 animate-in fade-in duration-300">
              <div className="w-16 h-16 border-4 border-blue-500/30 border-t-blue-500 rounded-full animate-spin mb-6 shadow-[0_0_15px_rgba(59,130,246,0.5)]"></div>
              <h3 className="text-2xl font-bold text-white mb-2 bg-gradient-to-r from-blue-400 to-indigo-400 bg-clip-text text-transparent animate-pulse">Running Intelligence Engine...</h3>
              <p className="text-slate-400 font-mono text-sm max-w-sm text-center">
                Computing 384-dimensional dense vectors, searching FAISS index, evaluating production readiness, and checking honeypot logic.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
