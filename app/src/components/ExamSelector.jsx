export default function ExamSelector({ exams, onSelect }) {
  return (
    <section className="card">
      <h2>Exames disponíveis</h2>
      <div className="examList">
        {exams.map((exam) => (
          <button key={exam.examId} className="examButton" onClick={() => onSelect(exam)}>
            <strong>{exam.title}</strong>
            <span>{exam.questions.length} questão(ões)</span>
          </button>
        ))}
      </div>
    </section>
  )
}
