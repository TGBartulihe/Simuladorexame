import { useState } from 'react'
import ExamSelector from './components/ExamSelector.jsx'
import ExamRunner from './components/ExamRunner.jsx'
import ProgressSummary from './components/ProgressSummary.jsx'

const demoExams = [
  {
    examId: 'seed-2025-portugues-639-f1-v1',
    title: 'Português 639 - 2025 - Fase 1',
    questions: [
      {
        id: 'q1',
        number: '1',
        type: 'open_text',
        statement: 'Pergunta pendente de extração. Quando o parser estiver ligado, este campo receberá a pergunta real extraída do enunciado.',
        officialCriteria: 'Critério pendente de extração. Quando o parser estiver ligado, este campo receberá os critérios oficiais.',
        maxScore: 20,
        correctionMode: 'rubric'
      }
    ]
  }
]

export default function App() {
  const [selectedExam, setSelectedExam] = useState(null)
  const [result, setResult] = useState(null)

  return (
    <main className="shell">
      <header className="hero">
        <p className="eyebrow">PoC privada</p>
        <h1>Simulador de Exame Nacional</h1>
        <p>Escolhe um exame, responde e vê a correção com base nos critérios estruturados.</p>
      </header>

      {!selectedExam && <ExamSelector exams={demoExams} onSelect={setSelectedExam} />}
      {selectedExam && !result && <ExamRunner exam={selectedExam} onFinish={setResult} onBack={() => setSelectedExam(null)} />}
      {result && <ProgressSummary result={result} onRestart={() => { setResult(null); setSelectedExam(null) }} />}
    </main>
  )
}
