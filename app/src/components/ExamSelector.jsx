// components/ExamSelector.jsx
import { useState } from 'react'

const PHASE_LABELS = {
  F1: '1.ª fase',
  F2: '2.ª fase',
  EE: 'Exame de equivalência',
}

const COMPLETENESS_LABELS = {
  completo: null, // não precisa de aviso
  gabarito_parcial: 'gabarito parcial',
  pontuacao_parcial: 'cotações parciais',
  incompleto: 'dados incompletos',
  sem_questoes_extraidas: 'sem questões disponíveis',
  revisar_extracao: 'extração não verificada',
}

function ExamOption({ exam, onSelect }) {
  const isUsable = exam.completeness !== 'sem_questoes_extraidas' && exam.totalQuestions > 0
  const warningLabel = COMPLETENESS_LABELS[exam.completeness]

  return (
    <button
      className={`exam-option ${!isUsable ? 'disabled' : ''}`}
      disabled={!isUsable}
      onClick={() => isUsable && onSelect(exam)}
    >
      <span>
        <span className="phase-tag">{PHASE_LABELS[exam.phase] || exam.phase}</span>
        {'  '}
        {isUsable ? `${exam.totalQuestions} questões` : 'Sem questões extraídas ainda'}
      </span>
      {warningLabel && (
        <span className="completeness-flag warn">{warningLabel}</span>
      )}
    </button>
  )
}

export default function ExamSelector({ catalog, onSelectExam }) {
  const [selectedSubjectSlug, setSelectedSubjectSlug] = useState(null)
  const [selectedYear, setSelectedYear] = useState(null)

  const subject = catalog.subjects.find((s) => s.slug === selectedSubjectSlug)
  const yearEntry = subject?.years.find((y) => y.year === selectedYear)

  if (!subject) {
    return (
      <section>
        <h2>Escolhe a disciplina</h2>
        <p className="lede">
          Cada disciplina reúne os exames nacionais disponíveis, organizados por ano.
        </p>
        <div className="shelf-grid" style={{ marginTop: 20 }}>
          {catalog.subjects.map((s) => {
            const totalExams = s.years.reduce((sum, y) => sum + y.exams.length, 0)
            const totalYears = s.years.length
            return (
              <button
                key={s.slug}
                className="subject-button"
                onClick={() => setSelectedSubjectSlug(s.slug)}
              >
                <span className="subject-name">{s.subject}</span>
                <span className="subject-meta">
                  {totalYears} anos · {totalExams} exames
                </span>
              </button>
            )
          })}
        </div>
      </section>
    )
  }

  if (!yearEntry) {
    return (
      <section>
        <button className="linkButton" onClick={() => setSelectedSubjectSlug(null)}>
          ← disciplinas
        </button>
        <h2>{subject.subject}</h2>
        <p className="lede">Escolhe o ano do exame que queres simular.</p>
        <div className="year-chip-grid" style={{ marginTop: 20 }}>
          {subject.years.map((y) => (
            <button
              key={y.year}
              className="year-chip"
              onClick={() => setSelectedYear(y.year)}
            >
              {y.year}
            </button>
          ))}
        </div>
      </section>
    )
  }

  return (
    <section>
      <button className="linkButton" onClick={() => setSelectedYear(null)}>
        ← anos de {subject.subject}
      </button>
      <h2>{subject.subject} — {yearEntry.year}</h2>
      <p className="lede">
        Escolhe a fase. Cada caderno é simulado com a numeração e os grupos do exame original.
      </p>
      <div className="exam-option-list">
        {yearEntry.exams.map((exam) => (
          <ExamOption
            key={exam.examId}
            exam={exam}
            onSelect={() => onSelectExam({ ...exam, subject: subject.subject, year: yearEntry.year })}
          />
        ))}
      </div>
    </section>
  )
}
