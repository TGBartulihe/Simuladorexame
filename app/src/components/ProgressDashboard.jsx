// components/ProgressDashboard.jsx
import { useEffect, useState } from 'react'
import { getTopicStatistics } from '../lib/progressStore.js'
import { loadCatalog, loadExam, usableQuestions } from '../lib/dataApi.js'

function bandFor(rate) {
  if (rate < 0.5) return 'low'
  if (rate < 0.75) return 'mid'
  return 'high'
}

function TopicRow({ stat }) {
  const pct = Math.round(stat.successRate * 100)
  return (
    <div className="topic-bar-row">
      <div>
        <div className="topic-name">{stat.topic || 'Sem tópico classificado'}</div>
        <div className="topic-bar-track">
          <div className={`topic-bar-fill ${bandFor(stat.successRate)}`} style={{ width: `${pct}%` }} />
        </div>
      </div>
      <div className="topic-meta">{pct}% · {stat.attempts} questões</div>
    </div>
  )
}

/**
 * Sugere exercícios de fixação: procura, no catálogo, exames da mesma
 * disciplina que tenham questões já classificadas com o tópico mais frágil
 * do aluno. Isto é uma busca em tempo real sobre os JSONs estáticos — para
 * uma base muito maior, valeria pré-computar um índice topic -> exames no
 * próprio export (scripts/03), mas para o volume atual (152 exames) a busca
 * direta é suficientemente rápida.
 */
async function findFixationExercises(subject, topic, excludeExamIds, maxResults = 3) {
  const catalog = await loadCatalog()
  const subjectEntry = catalog.subjects.find((s) => s.subject === subject)
  if (!subjectEntry) return []

  const candidates = subjectEntry.years
    .flatMap((y) => y.exams)
    .filter((e) => e.completeness !== 'sem_questoes_extraidas' && !excludeExamIds.has(e.examId))

  const matches = []
  for (const candidate of candidates) {
    if (matches.length >= maxResults) break
    try {
      const exam = await loadExam(candidate.examKey)
      const hasTopic = usableQuestions(exam).some((q) => q.topic === topic)
      if (hasTopic) {
        matches.push({ examKey: exam.examKey, year: exam.year, phase: exam.phase })
      }
    } catch {
      // exame sem arquivo exportado ainda — ignora silenciosamente
    }
  }
  return matches
}

export default function ProgressDashboard({ student, onOpenExam }) {
  const [subject, setSubject] = useState(null)
  const [subjects, setSubjects] = useState([])
  const [stats, setStats] = useState([])
  const [suggestions, setSuggestions] = useState(null)
  const [loadingSuggestions, setLoadingSuggestions] = useState(false)

  useEffect(() => {
    loadCatalog().then((catalog) => {
      const names = catalog.subjects.map((s) => s.subject)
      setSubjects(names)
      if (names.length > 0) setSubject(names[0])
    })
  }, [])

  useEffect(() => {
    if (!subject) return
    setStats(getTopicStatistics({ student, subject }))
    setSuggestions(null)
  }, [subject, student])

  const weakestTopic = stats.find((s) => s.attempts > 0 && s.successRate < 0.75)

  async function handleSuggest() {
    if (!weakestTopic) return
    setLoadingSuggestions(true)
    const results = await findFixationExercises(subject, weakestTopic.topic, new Set())
    setSuggestions(results)
    setLoadingSuggestions(false)
  }

  if (subjects.length === 0) {
    return <p className="lede">A carregar disciplinas...</p>
  }

  const hasAnyAttempt = stats.length > 0

  return (
    <section>
      <h2>O teu progresso</h2>
      <p className="lede">Desempenho por tópico, com base nas simulações já feitas.</p>

      <div className="year-chip-grid" style={{ margin: '16px 0 24px' }}>
        {subjects.map((s) => (
          <button
            key={s}
            className={`year-chip ${s === subject ? 'active' : ''}`}
            onClick={() => setSubject(s)}
          >
            {s}
          </button>
        ))}
      </div>

      {!hasAnyAttempt && (
        <div className="empty-state card">
          <div className="empty-icon">—</div>
          <p>
            Ainda não há respostas registadas em {subject} com tópico classificado.
            Faz uma simulação para começar a ver o teu progresso aqui.
          </p>
        </div>
      )}

      {hasAnyAttempt && (
        <div className="card">
          {stats.map((s) => (
            <TopicRow key={s.topic || '_sem_topico'} stat={s} />
          ))}
        </div>
      )}

      {weakestTopic && (
        <div className="suggestion-card">
          <div className="suggestion-label">Sugestão de fixação</div>
          <p style={{ margin: '8px 0' }}>
            O tópico onde tens mais dificuldade é <strong>{weakestTopic.topic}</strong>{' '}
            ({Math.round(weakestTopic.successRate * 100)}% de acerto).
          </p>
          {!suggestions && (
            <button className="secondary" onClick={handleSuggest} disabled={loadingSuggestions}>
              {loadingSuggestions ? 'A procurar exercícios...' : 'Sugerir exercícios deste tópico'}
            </button>
          )}
          {suggestions && suggestions.length === 0 && (
            <p style={{ fontSize: 14, color: 'var(--muted)' }}>
              Não encontrei outro exame com questões deste tópico já classificadas.
              Isto pode significar que a classificação de tópicos ainda não foi feita
              para outros exames desta disciplina.
            </p>
          )}
          {suggestions && suggestions.length > 0 && (
            <div className="exam-option-list">
              {suggestions.map((s) => (
                <button
                  key={s.examKey}
                  className="exam-option"
                  onClick={() => onOpenExam(s)}
                >
                  <span>{subject} — {s.year} ({s.phase})</span>
                  <span className="phase-tag">praticar</span>
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </section>
  )
}
