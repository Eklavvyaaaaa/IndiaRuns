import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

export default function Rankings() {
  const [results, setResults] = useState<any>(null)

  useEffect(() => {
    const data = localStorage.getItem('rankingResults')
    if (data) {
      setResults(JSON.parse(data))
    }
  }, [])

  if (!results) {
    return (
      <div className="text-center py-20 animate-in fade-in">
        <h2 className="text-2xl font-bold text-slate-300">No rankings found</h2>
        <p className="text-slate-500 mt-2">Please go to the dashboard and submit a job description.</p>
        <Link to="/" className="mt-6 inline-block text-blue-400 hover:text-blue-300">
          &larr; Back to Dashboard
        </Link>
      </div>
    )
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6 animate-in fade-in slide-in-from-bottom-4">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Top Ranked Candidates</h1>
        <div className="text-sm text-slate-400 bg-slate-900 px-4 py-2 rounded-full border border-slate-800">
          Processed in <span className="text-white font-mono">{results.processing_time_ms}ms</span>
        </div>
      </div>

      <div className="space-y-4">
        {results.candidates.map((cand: any, i: number) => (
          <div key={cand.candidate_id} className="bg-slate-900 border border-slate-800 rounded-xl p-6 hover:border-slate-700 transition-all flex flex-col md:flex-row gap-6">
            <div className="flex-shrink-0 w-16 h-16 bg-slate-800 rounded-full flex items-center justify-center text-xl font-bold border-2 border-slate-700">
              #{i + 1}
            </div>
            
            <div className="flex-grow space-y-4">
              <div className="flex justify-between items-start">
                <div>
                  <h2 className="text-xl font-semibold text-white">{cand.anonymized_name}</h2>
                  <p className="text-sm text-slate-400 font-mono mt-1">{cand.candidate_id}</p>
                </div>
                <div className="text-right">
                  <div className="text-3xl font-black bg-gradient-to-br from-green-400 to-emerald-600 bg-clip-text text-transparent">
                    {cand.scores.final_score.toFixed(1)}
                  </div>
                  <div className="text-xs text-slate-500 uppercase tracking-widest font-semibold mt-1">Final Score</div>
                </div>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-4 border-t border-slate-800">
                <Metric label="Semantic Fit" value={cand.scores.semantic_fit} />
                <Metric label="Retrieval" value={cand.scores.retrieval_intelligence} />
                <Metric label="Prod Ready" value={cand.scores.production_readiness} />
                <Metric label="Skill Trust" value={cand.scores.skill_trust} />
              </div>
              
              <div className="bg-slate-950 rounded-lg p-4 mt-4">
                <h3 className="text-sm font-semibold text-slate-300 mb-2 uppercase tracking-wide">AI Reasoning</h3>
                <ul className="space-y-2">
                  {cand.reasoning.map((r: string, idx: number) => (
                    <li key={idx} className="text-sm text-slate-400 flex items-start gap-2">
                      <span className="text-blue-500 mt-0.5">•</span> {r}
                    </li>
                  ))}
                </ul>
              </div>

              {cand.blindspot.is_hidden_gem && (
                <div className="mt-4 bg-purple-900/20 border border-purple-500/30 rounded-lg p-3 flex items-center gap-3">
                  <span className="text-xl">💎</span>
                  <div>
                    <span className="text-purple-400 font-semibold text-sm">Hidden Gem Detected!</span>
                    <p className="text-xs text-purple-300/80">Capability score ({cand.blindspot.capability_score}) is {cand.blindspot.delta.toFixed(1)} pts higher than naive ATS score ({cand.blindspot.ats_score}).</p>
                  </div>
                </div>
              )}
              
              {cand.is_honeypot && (
                <div className="mt-4 bg-red-900/20 border border-red-500/30 rounded-lg p-3 flex items-center gap-3">
                  <span className="text-xl">⚠️</span>
                  <div>
                    <span className="text-red-400 font-semibold text-sm">Honeypot Flagged</span>
                    <p className="text-xs text-red-300/80">Candidate has timeline inconsistencies or impossible skill durations.</p>
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function Metric({ label, value }: { label: string, value: number }) {
  return (
    <div>
      <div className="text-lg font-semibold text-slate-200">{value.toFixed(1)}</div>
      <div className="text-xs text-slate-500">{label}</div>
    </div>
  )
}
