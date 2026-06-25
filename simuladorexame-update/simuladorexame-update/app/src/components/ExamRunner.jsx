// components/ExamRunner.jsx
import { useState, useMemo } from 'react'

const PHASE_LABELS = { F1: '1.ª fase', F2: '2.ª fase', EE: 'Exame de equivalência' }

function ChoiceQuestion({ question, value, onChange }) {
  return (
    <div className="choice-list">
      {question.choices.map((choice) => (
        <button
          key={choice.id}
          className={`choice-option ${value === choice.letter ? 'selected' : ''}`}
          onClick={() => onChange(choice.letter)}
          type="button"
        >
          <span className="choice-letter">{choice.letter})</span>
          <span>{choice.text}</span>
        </button>
      ))}
    </div>
  )
}

function OpenQuestion({ value, onChange }) {
  return (
    <textarea
      value={value || ''}
      onChange={(e) => onChange(e.target.value)}
      placeholder="Escreve aqui a tua resposta..."
    />
  )
}

export default function ExamRunner({ exam, usableQuestions, onFinish, onBack }) {
  const [answers, setAnswers] = useState({})

  const groupedQuestions = useMemo(() => {
    const groups = []
    let currentGroupName = null
    let currentContextId = null
    let currentBucket = null

    for (const q of usableQuestions) {
      if (q.groupName !== currentGroupName) {
        currentGroupName = q.groupName
        currentBucket = { groupName: currentGroupName, contexts: [] }
        groups.push(currentBucket)
        currentContextId = null
      }
      if (q.contextText !== currentContextId) {
        currentContextId = q.contextText
        currentBucket.contexts.push({
          contextTitle: q.contextTitle,
          contextText: q.contextText,
          questions: [],
        })
      }
      currentBucket.contexts[currentBucket.contexts.length - 1].questions.push(q)
    }
    return groups
  }, [usableQuestions])

  const answeredCount = Object.keys(answers).filter((k) => {
    const v = answers[k]
    return v != null && v !== ''
  }).length
  const progressPct = usableQuestions.length
    ? Math.round((answeredCount / usableQuestions.length) * 100)
    : 0

  function setAnswer(questionId, value) {
    setAnswers((prev) => ({ ...prev, [questionId]: value }))
  }

  function submit() {
    onFinish(answers)
  }

  return (
    <section>
      <div className="exam-runner-head">
        <button className="linkButton" onClick={onBack}>← sair da simulação</button>
        <span className="completeness-flag">
          {answeredCount}/{usableQuestions.length} respondidas
        </span>
      </div>

      <div className="timbre">
        <span>
          <strong>{exam.subject}</strong>
          {'  '}
          <span className="timbre-tag">{PHASE_LABELS[exam.phase] || exam.phase}</span>
        </span>
        <span>{exam.year}</span>
      </div>

      <div className="exam-progress-bar">
        <div className="exam-progress-fill" style={{ width: `${progressPct}%` }} />
      </div>

      {groupedQuestions.map((group, gi) => (
        <div key={gi}>
          <div className="group-divider">{group.groupName || 'Questões'}</div>
          {group.contexts.map((ctx, ci) => (
            <div key={ci}>
              {ctx.contextText && (
                <div className="context-block">
                  {ctx.contextTitle && <div className="context-title">{ctx.contextTitle}</div>}
                  {ctx.contextText}
                </div>
              )}
              {ctx.questions.map((q) => (
                <article key={q.id} className="question">
                  <div className="question-head">
                    <span className="question-number">{q.question_number}.</span>
                    {q.pontuacaoDisponivel && (
                      <span className="question-points">{q.max_points} pontos</span>
                    )}
                  </div>
                  <p className="question-statement">{q.statement}</p>
                  {q.question_type === 'multiple_choice' ? (
                    <ChoiceQuestion
                      question={q}
                      value={answers[q.id]}
                      onChange={(letter) => setAnswer(q.id, letter)}
                    />
                  ) : (
                    <OpenQuestion
                      value={answers[q.id]}
                      onChange={(text) => setAnswer(q.id, text)}
                    />
                  )}
                </article>
              ))}
            </div>
          ))}
        </div>
      ))}

      <button className="primary" onClick={submit} style={{ marginTop: 32 }}>
        Submeter exame
      </button>
    </section>
  )
}
