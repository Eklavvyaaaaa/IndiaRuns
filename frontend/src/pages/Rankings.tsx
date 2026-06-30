import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { MessageSquare, Users } from 'lucide-react'
import DiscussionRoomWidget from '../lib/DiscussionRoomWidget'
import { CometChatService } from '../lib/CometChatService'

interface CandidateScores {
  final_score: number;
  semantic_fit: number;
  jd_requirement_fit: number;
  retrieval_intelligence: number;
  production_readiness: number;
  skill_trust: number;
  behavioral_intelligence: number;
  career_quality: number;
  consistency: number;
  education: number;
  role_penalty: number;
}

interface JDSignal {
  name: string;
  label: string;
  confidence: number;
  strength: number;
  polarity: string;
}

interface JDAnalysis {
  mode?: string;
  signals?: JDSignal[];
  adaptive_weights?: Record<string, number>;
  confidence?: number;
  manual_priorities?: Record<string, number>;
  reasoning?: string[];
  warnings?: string[];
}

interface BlindSpot {
  ats_score: number;
  capability_score: number;
  delta: number;
  is_hidden_gem: boolean;
}

interface RankedCandidate {
  candidate_id: string;
  anonymized_name: string;
  title: string;
  summary: string;
  scores: CandidateScores;
  blindspot: BlindSpot;
  reasoning: string[];
  is_honeypot: boolean;
}

interface RankResponse {
  status: string;
  processing_time_ms: number;
  jd_analysis?: JDAnalysis;
  candidates: RankedCandidate[];
}

export default function Rankings() {
  const [results, setResults] = useState<RankResponse | null>(null)
  const [activeChat, setActiveChat] = useState<{guid: string, candidate: RankedCandidate} | null>(null)
  const [isCreatingUser, setIsCreatingUser] = useState(false)

  const handleDiscussionClick = async (cand: RankedCandidate) => {
    setIsCreatingUser(true)
    const guid = await CometChatService.joinOrCreateDiscussionRoom(cand.candidate_id, cand.anonymized_name)
    if (guid) {
      setActiveChat({ guid, candidate: cand })
    }
    setIsCreatingUser(false)
  }

  useEffect(() => {
    const data = localStorage.getItem('rankingResults')
    if (data) {
      try {
        const parsed = JSON.parse(data)
        // Runtime shape guard
        if (parsed && typeof parsed.processing_time_ms === 'number' && Array.isArray(parsed.candidates)) {
          setResults(parsed as RankResponse)
        } else {
          console.error("Invalid ranking results format in local storage")
          setResults(null)
        }
      } catch (err) {
        console.error("Failed to parse ranking results:", err)
        setResults(null)
      }
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
        <div>
          <h1 className="text-3xl font-bold">Top Ranked Candidates</h1>
          <p className="text-sm text-slate-400 mt-1">
            {results.jd_analysis?.mode === 'adaptive' ? 'Adaptive JD ranking' : 'Normal ranking engine'}
          </p>
        </div>
        <div className="text-sm text-slate-400 bg-slate-900 px-4 py-2 rounded-full border border-slate-800">
          Processed in <span className="text-white font-mono">{results.processing_time_ms}ms</span>
        </div>
      </div>

      {results.jd_analysis?.mode === 'adaptive' && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold text-white">JD-Adaptive Weights</h2>
              <p className="text-sm text-slate-400">
                Confidence: {((results.jd_analysis.confidence || 0) * 100).toFixed(0)}%
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              {(results.jd_analysis.signals || []).filter((s) => s.polarity === 'positive').slice(0, 5).map((signal) => (
                <span key={signal.name} className="text-xs text-blue-200 bg-blue-950/60 border border-blue-800 rounded-full px-3 py-1">
                  {signal.label} {(signal.confidence * 100).toFixed(0)}%
                </span>
              ))}
            </div>
          </div>

          {results.jd_analysis.adaptive_weights && (
            <div className="grid grid-cols-4 md:grid-cols-5 lg:grid-cols-9 gap-3 pt-3 border-t border-slate-800">
              {Object.entries(results.jd_analysis.adaptive_weights).map(([name, value]) => (
                <Metric key={name} label={name.toUpperCase()} value={value * 100} />
              ))}
            </div>
          )}

          {results.jd_analysis.manual_priorities && Object.keys(results.jd_analysis.manual_priorities).length > 0 && (
            <div className="pt-3 border-t border-slate-800">
              <h3 className="text-sm font-semibold text-slate-300 mb-2">Manual Priorities</h3>
              <div className="flex flex-wrap gap-2">
                {Object.entries(results.jd_analysis.manual_priorities).map(([name, value]) => (
                  <span key={name} className="text-xs text-emerald-200 bg-emerald-950/50 border border-emerald-800 rounded-full px-3 py-1">
                    {name.toUpperCase()} {value}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      <div className="space-y-4">
        {results.candidates.map((cand: RankedCandidate, i: number) => (
          <div key={cand.candidate_id} className="bg-slate-900 border border-slate-800 rounded-xl p-6 hover:border-slate-700 transition-all flex flex-col md:flex-row gap-6">
            <div className="flex-shrink-0 w-16 h-16 bg-slate-800 rounded-full flex items-center justify-center text-xl font-bold border-2 border-slate-700">
              #{i + 1}
            </div>
            
            <div className="flex-grow space-y-4">
              <div className="flex justify-between items-start">
                <div>
                  <h2 className="text-xl font-semibold text-white">{cand.anonymized_name}</h2>
                  <h3 className="text-md text-blue-400 font-medium mt-1">{cand.title}</h3>
                  <p className="text-sm text-slate-400 font-mono mt-0.5">{cand.candidate_id}</p>
                </div>
                <div className="text-right flex flex-col items-end gap-2">
                  <div className="text-3xl font-black bg-gradient-to-br from-green-400 to-emerald-600 bg-clip-text text-transparent">
                    {cand.scores.final_score.toFixed(1)}
                  </div>
                  <div className="text-xs text-slate-500 uppercase tracking-widest font-semibold mt-1">Final Score</div>
                  <button 
                    onClick={() => handleDiscussionClick(cand)}
                    disabled={isCreatingUser}
                    className="mt-2 flex items-center gap-1.5 px-3 py-1.5 bg-indigo-600/20 text-indigo-400 hover:bg-indigo-600 hover:text-white border border-indigo-600/30 rounded-md text-sm font-medium transition-colors"
                  >
                    <Users size={14} />
                    {isCreatingUser ? 'Opening...' : 'Discuss'}
                  </button>
                </div>
              </div>
              
              {cand.summary && (
                <div className="bg-slate-800/30 border border-slate-700/50 rounded-lg p-3 text-sm text-slate-300 italic leading-relaxed">
                  &ldquo;{cand.summary}&rdquo;
                </div>
              )}

              <div className="grid grid-cols-3 md:grid-cols-5 lg:grid-cols-9 gap-3 pt-4 border-t border-slate-800">
                <Metric label="Semantic" value={cand.scores.semantic_fit} />
                <Metric label="JD Coverage" value={cand.scores.jd_requirement_fit} />
                <Metric label="Retrieval" value={cand.scores.retrieval_intelligence} />
                <Metric label="Prod Ready" value={cand.scores.production_readiness} />
                <Metric label="Skill Trust" value={cand.scores.skill_trust} />
                <Metric label="Behavioral" value={cand.scores.behavioral_intelligence} />
                <Metric label="Career" value={cand.scores.career_quality} />
                <Metric label="Consistency" value={cand.scores.consistency} />
                <Metric label="Education" value={cand.scores.education} />
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

      {activeChat && (
        <DiscussionRoomWidget 
          guid={activeChat.guid} 
          candidate={activeChat.candidate} 
          onClose={() => setActiveChat(null)} 
        />
      )}
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
