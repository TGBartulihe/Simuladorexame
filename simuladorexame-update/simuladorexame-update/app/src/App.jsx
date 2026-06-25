// App.jsx
import { useEffect, useState } from 'react'
import ExamSelector from './components/ExamSelector.jsx'
import ExamRunner from './components/ExamRunner.jsx'
import ExamResult from './components/ExamResult.jsx'
import ProgressDashboard from './components/ProgressDashboard.jsx'
import { loadCatalog, loadExam, usableQuestions } from './lib/dataApi.js'
import { correctExam } from './engine/correctionEngine.js'
import {
  startAttempt,
  finishAttempt,
  recordTopicOutcome,
  getDefaultStudentId,
} from './lib/progressStore.js'

const VIEWS = {
  MENU: 'menu',
  RUNNING: 'running',
  RESULT: 'result',
  PROGRESS: 'progress',
}

function pickRandom(catalog) {
  const allExams = catalog.subjects.flatMap((s) =>
    s.years.flatMap((y) =>
      y.exams
        .filter((e) => e.completeness !== 'sem_questoes_extraidas')
        .map((e) => ({ ...e, subject: s.subject, year: y.year }))
    )
  )
  if (allExams.length === 0) return null
  return allExams[Math.floor(Math.random() * allExams.length)]
}

export default function App() {
  const [view, setView] = useState(VIEWS.MENU)
  const [catalog, setCatalog] = useState(null)
  const [currentExam, setCurrentExam] = useState(null)
  const [currentUsableQuestions, setCurrentUsableQuestions] = useState([])
  const [currentAttemptId, setCurrentAttemptId] = useState(null)
  const [result, setResult] = useState(null)
  const [loadError, setLoadError] = useState(null)
  const student = getDefaultStudentId()

  useEffect(() => {
    loadCatalog()
      .then(setCatalog)
      .catch((err) => setLoadError(err.message))
  }, [])

  async function openExam(examRef) {
    setLoadError(null)
    try {
      const exam = await loadExam(examRef.examKey)
      const usable = usableQuestions(exam)
      setCurrentExam({ ...exam, subject: examRef.subject ?? exam.subject, year: examRef.year ?? exam.year })
      setCurrentUsableQuestions(usable)
      setCurrentAttemptId(startAttempt({ student, examId: exam.examId }))
      setView(VIEWS.RUNNING)
    } catch (err) {
      setLoadError(err.message)
    }
  }

  async function handleRandomExam() {
    if (!catalog) return
    const choice = pickRandom(catalog)
    if (!choice) {
      setLoadError('Não há exames disponíveis para simulação aleatória ainda.')
      return
    }
    await openExam(choice)
  }

  function handleFinishExam(answers) {
    const corrected = correctExam(currentExam, currentUsableQuestions, answers)
    setResult(corrected)

    finishAttempt({
      attemptId: currentAttemptId,
      score: corrected.scoring.autoGradedPercentage,
      answers: corrected.items.map((item) => ({
        questionId: item.questionId,
        answer: item.studentAnswer,
        isCorrect: item.isCorrect,
        obtainedPoints: item.obtainedPoints,
        feedback: item.feedback,
      })),
    })

    for (const item of corrected.items) {
      if (item.isCorrect != null && item.topic) {
        recordTopicOutcome({
          student,
          subject: currentExam.subject,
          topic: item.topic,
          isCorrect: item.isCorrect,
        })
      }
    }

    setView(VIEWS.RESULT)
  }

  function backToMenu() {
    setView(VIEWS.MENU)
    setCurrentExam(null)
    setResult(null)
  }

  return (
    <main className="shell">
      <header className="hero">
        <p className="eyebrow">Simulador de exame nacional</p>
        <h1>Estuda com os exames reais</h1>
        <p className="lede">
          Escolhe a disciplina e o ano, ou pede um exame ao acaso. No final vês todas
          as respostas corrigidas e o teu progresso por tópico.
        </p>
        {view !== VIEWS.MENU && (
          <button className="linkButton" onClick={() => setView(VIEWS.MENU)} style={{ marginTop: 8 }}>
            ← menu principal
          </button>
        )}
      </header>

      {loadError && <div className="data-warning">{loadError}</div>}

      {view === VIEWS.MENU && catalog && (
        <>
          <div className="card" style={{ marginBottom: 20 }}>
            <button className="primary" onClick={handleRandomExam} style={{ marginTop: 0 }}>
              Simular um exame ao acaso
            </button>
            <button
              className="secondary"
              onClick={() => setView(VIEWS.PROGRESS)}
              style={{ marginTop: 12, marginLeft: 12 }}
            >
              Ver o meu progresso
            </button>
          </div>
          <ExamSelector catalog={catalog} onSelectExam={openExam} />
        </>
      )}

      {view === VIEWS.MENU && !catalog && !loadError && <p className="lede">A carregar exames...</p>}

      {view === VIEWS.RUNNING && currentExam && (
        <ExamRunner
          exam={currentExam}
          usableQuestions={currentUsableQuestions}
          onFinish={handleFinishExam}
          onBack={backToMenu}
        />
      )}

      {view === VIEWS.RESULT && result && (
        <ExamResult result={result} onRestart={backToMenu} onBackToMenu={backToMenu} />
      )}

      {view === VIEWS.PROGRESS && (
        <ProgressDashboard student={student} onOpenExam={openExam} />
      )}
    </main>
  )
}
