import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import {
  Activity,
  Brain,
  BriefcaseBusiness,
  GraduationCap,
  Network,
  ShieldCheck,
  SlidersHorizontal,
  Users,
} from 'lucide-react'

type PriorityKey = 'edu' | 'cq' | 'pr' | 'st' | 'ri' | 'jrf' | 'semantic' | 'bi' | 'cs'

const PRIORITIES: Array<{
  key: PriorityKey;
  label: string;
  description: string;
  icon: typeof GraduationCap;
}> = [
  {
    key: 'edu',
    label: 'Education',
    description: 'Use when college tier, degree, or academic pedigree matters.',
    icon: GraduationCap,
  },
  {
    key: 'cq',
    label: 'Experience',
    description: 'Use when seniority, career quality, and role depth matter most.',
    icon: BriefcaseBusiness,
  },
  {
    key: 'pr',
    label: 'Production',
    description: 'Use when shipping, scale, latency, and reliability are critical.',
    icon: Activity,
  },
  {
    key: 'st',
    label: 'Skill Trust',
    description: 'Use when proven skill evidence matters more than keyword mentions.',
    icon: ShieldCheck,
  },
  {
    key: 'ri',
    label: 'Retrieval',
    description: 'Use for RAG, search, ranking, embeddings, or vector database roles.',
    icon: Network,
  },
  {
    key: 'jrf',
    label: 'JD Coverage',
    description: 'Use when exact role requirements must be covered by profile evidence.',
    icon: SlidersHorizontal,
  },
  {
    key: 'semantic',
    label: 'JD Match',
    description: 'Use when overall semantic similarity to the JD matters most.',
    icon: Brain,
  },
  {
    key: 'bi',
    label: 'Behavior',
    description: 'Use when responsiveness, availability, and platform signals matter.',
    icon: Users,
  },
  {
    key: 'cs',
    label: 'Consistency',
    description: 'Use when coherent profile claims and stable evidence matter.',
    icon: SlidersHorizontal,
  },
]

const PRESETS: Record<string, Record<PriorityKey, number>> = {
  balanced: { edu: 1, cq: 1, pr: 1, st: 1, ri: 1, jrf: 2, semantic: 1, bi: 1, cs: 1 },
  education: { edu: 5, cq: 2, pr: 1, st: 2, ri: 1, jrf: 3, semantic: 1, bi: 0, cs: 1 },
  experience: { edu: 1, cq: 5, pr: 3, st: 2, ri: 1, jrf: 3, semantic: 1, bi: 1, cs: 2 },
  production: { edu: 0, cq: 2, pr: 5, st: 3, ri: 3, jrf: 3, semantic: 1, bi: 1, cs: 2 },
}

export default function AdaptiveJD() {
  const [jd, setJd] = useState('Senior AI Engineer. Candidate must be from a Tier 1 college like IIT or IISc. Build production retrieval systems. Healthcare domain and AWS certification preferred.')
  const [priorities, setPriorities] = useState<Record<PriorityKey, number>>(PRESETS.balanced)
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const strongest = useMemo(() => {
    return Object.entries(priorities)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 3)
      .map(([key]) => PRIORITIES.find((item) => item.key === key)?.label)
      .filter(Boolean)
      .join(', ')
  }, [priorities])

  const applyPreset = (preset: keyof typeof PRESETS) => {
    setPriorities(PRESETS[preset])
  }

  const setPriority = (key: PriorityKey, value: number) => {
    setPriorities((current) => ({ ...current, [key]: value }))
  }

  const handleRank = async () => {
    setLoading(true)
    try {
      const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'
      const response = await axios.post(`${baseUrl}/rank`, {
        job_description: jd,
        top_k: 100,
        use_adaptive: true,
        priority_overrides: priorities,
      }, { timeout: 30000 })
      localStorage.setItem('rankingResults', JSON.stringify(response.data))
      navigate('/rankings')
    } catch (error) {
      console.error(error)
      alert('Failed to run adaptive ranking. Is the FastAPI backend running?')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="space-y-3">
        <div className="inline-flex items-center gap-2 text-xs uppercase tracking-widest text-blue-300 bg-blue-950/50 border border-blue-900 rounded-full px-3 py-1">
          <SlidersHorizontal className="w-3.5 h-3.5" />
          Adaptive JD Mode
        </div>
        <h1 className="text-3xl md:text-4xl font-extrabold tracking-tight">Tune the ranking for this exact role</h1>
        <p className="text-slate-400 max-w-3xl">
          Paste the JD, choose what should matter most, and the engine will combine JD-detected signals with your priority controls.
        </p>
      </div>

      <div className="grid lg:grid-cols-[1fr_420px] gap-6">
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
          <div>
            <label className="text-sm font-semibold text-slate-300">Job Description</label>
            <textarea
              value={jd}
              onChange={(e) => setJd(e.target.value)}
              className="mt-2 w-full h-[420px] bg-slate-950 border border-slate-800 rounded-lg p-4 text-slate-200 focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none resize-none"
              placeholder="Paste Job Description here..."
            />
          </div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-5">
          <div>
            <h2 className="text-lg font-semibold text-white">Importance Controls</h2>
            <p className="text-sm text-slate-400 mt-1">Top focus: {strongest || 'Balanced'}</p>
          </div>

          <div className="grid grid-cols-2 gap-2">
            <PresetButton label="Balanced" onClick={() => applyPreset('balanced')} />
            <PresetButton label="Education First" onClick={() => applyPreset('education')} />
            <PresetButton label="Experience First" onClick={() => applyPreset('experience')} />
            <PresetButton label="Production First" onClick={() => applyPreset('production')} />
          </div>

          <div className="space-y-4 max-h-[520px] overflow-y-auto pr-1">
            {PRIORITIES.map((priority) => {
              const Icon = priority.icon
              return (
                <div key={priority.key} className="space-y-2 border border-slate-800 rounded-lg p-3 bg-slate-950/50">
                  <div className="flex items-start gap-3">
                    <div className="w-9 h-9 rounded-lg bg-slate-800 flex items-center justify-center text-blue-300">
                      <Icon className="w-4 h-4" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-3">
                        <h3 className="text-sm font-semibold text-slate-200">{priority.label}</h3>
                        <span className="text-sm font-mono text-blue-300">{priorities[priority.key]}</span>
                      </div>
                      <p className="text-xs text-slate-500 mt-1 leading-relaxed">{priority.description}</p>
                    </div>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="5"
                    step="1"
                    value={priorities[priority.key]}
                    onChange={(e) => setPriority(priority.key, Number(e.target.value))}
                    className="w-full accent-blue-500"
                  />
                </div>
              )
            })}
          </div>

          <button
            onClick={handleRank}
            disabled={loading}
            className="w-full bg-blue-600 hover:bg-blue-500 text-white font-semibold py-3 px-6 rounded-lg shadow-lg hover:shadow-blue-500/40 transition-all disabled:opacity-50"
          >
            {loading ? 'Running Adaptive Ranking...' : 'Run Adaptive Ranking'}
          </button>
        </div>
      </div>
    </div>
  )
}

function PresetButton({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="text-sm text-slate-300 hover:text-white bg-slate-950 hover:bg-slate-800 border border-slate-800 rounded-lg px-3 py-2 transition-colors"
    >
      {label}
    </button>
  )
}
