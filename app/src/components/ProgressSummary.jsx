export default function ProgressSummary({ result, onRestart }) {
  return (
    <section className="card">
      <h2>Correção</h2>
      <p className="score">Pontuação estimada: {result.estimatedScore}</p>
      {result.items.map((item) => (
        <article key={item.questionId} className="correction">
          <h3>Questão {item.number}</h3>
          <p><strong>Modo:</strong> {item.mode}</p>
          <p><strong>Resposta do aluno:</strong> {item.answer || 'Sem resposta'}</p>
          <p><strong>Critério oficial:</strong> {item.officialCriteria}</p>
          <p><strong>Observação:</strong> {item.feedback}</p>
        </article>
      ))}
      <button className="primary" onClick={onRestart}>Voltar ao início</button>
    </section>
  )
}
