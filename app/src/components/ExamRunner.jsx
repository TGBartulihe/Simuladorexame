import { useState } from 'react'
import { correctExam } from '../engine/correctionEngine.js'

export default function ExamRunner({ exam, onFinish, onBack }) {
  const [answers, setAnswers] = useState({})

  function submit() {
    onFinish(correctExam(exam, answers))
  }

  return (
    <section className="card">
      <button className="linkButton" onClick={onBack}>← voltar</button>
      <h2>{exam.title}</h2>
      {exam.questions.map((q) => (
        <article key={q.id} className="question">
          <h3>Questão {q.number}</h3>
          <p>{q.statement}</p>
          <textarea
            value={answers[q.id] || ''}
            onChange={(e) => setAnswers({ ...answers, [q.id]: e.target.value })}
            placeholder="Escreve aqui a tua resposta..."
          />
        </article>
      ))}
      <button className="primary" onClick={submit}>Submeter exame</button>
    </section>
  )
}
