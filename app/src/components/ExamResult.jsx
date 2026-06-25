// components/ExamResult.jsx

function statusOf(item) {
  if (item.needsManualReview) return 'review'
  return item.isCorrect ? 'correct' : 'wrong'
}

function StatusBadge({ item }) {
  const status = statusOf(item)
  const label =
    status === 'correct' ? 'Certo' : status === 'wrong' ? 'Errado' : 'Para revisão'
  return <span className={`correction-status ${status}`}>{label}</span>
}

function CotacaoGrid({ items }) {
  return (
    <div className="cotacao-grid">
      {items.map((item) => (
        <div key={item.questionId} className={`cotacao-cell ${statusOf(item)}`}>
          <span className="cotacao-num">{item.number}</span>
          <span className="cotacao-pts">
            {item.maxPoints != null ? item.maxPoints : '—'}
          </span>
        </div>
      ))}
    </div>
  )
}

export default function ExamResult({ result, onRestart, onBackToMenu }) {
  const { scoring, items } = result
  const hasAutoScore = scoring.autoGradedMaxPoints > 0

  return (
    <section>
      <button className="linkButton" onClick={onBackToMenu}>← voltar ao menu</button>
      <h2>Correção — {result.subject} {result.year}</h2>

      <div className="score-banner">
        <div>
          <div className="score-label">Pontuação automática</div>
          <div className="score-ring">
            {hasAutoScore
              ? `${scoring.autoGradedPoints} / ${scoring.autoGradedMaxPoints}`
              : '— / —'}
          </div>
        </div>
        <div className="score-detail">
          {scoring.pendingReviewCount > 0 && (
            <>
              {scoring.pendingReviewCount} de {scoring.totalQuestions} questões dependem de
              revisão manual (gabarito de escolha múltipla ainda incompleto nesta base, ou
              questões abertas que exigem correção por rubrica).
            </>
          )}
          {scoring.pendingReviewCount === 0 && (
            <>Todas as questões desta prova já têm correção automática disponível.</>
          )}
        </div>
      </div>

      <h3 style={{ marginBottom: 8 }}>Grade de cotações</h3>
      <CotacaoGrid items={items} />

      <h3 style={{ margin: '32px 0 8px' }}>Todas as respostas</h3>
      {items.map((item) => (
        <article key={item.questionId} className="correction-item">
          <StatusBadge item={item} />
          <div className="question-head">
            <span className="question-number">{item.number}.</span>
            {item.maxPoints != null && (
              <span className="question-points">{item.maxPoints} pontos</span>
            )}
          </div>
          <p className="question-statement">{item.statement}</p>

          {item.choices ? (
            <div className="choice-list">
              {item.choices.map((c) => {
                const isStudentPick = item.studentAnswer === c.letter
                const isAnswerKey = c.isCorrect
                let style = {}
                if (isAnswerKey) style = { borderColor: 'var(--correct)', background: 'var(--correct-bg)' }
                else if (isStudentPick) style = { borderColor: 'var(--wrong)', background: 'var(--wrong-bg)' }
                return (
                  <div key={c.id} className="choice-option" style={{ cursor: 'default', ...style }}>
                    <span className="choice-letter">{c.letter})</span>
                    <span>
                      {c.text}
                      {isStudentPick && ' — a tua resposta'}
                      {isAnswerKey && ' — resposta certa'}
                    </span>
                  </div>
                )
              })}
            </div>
          ) : (
            <>
              <div className="answer-block">
                <div className="answer-label">A tua resposta</div>
                {item.studentAnswer || <em>Sem resposta.</em>}
              </div>
              {item.criteriaText && (
                <div className="answer-block">
                  <div className="answer-label">Critério oficial</div>
                  {item.criteriaText}
                </div>
              )}
            </>
          )}

          <p style={{ fontSize: 14, color: 'var(--muted)', marginTop: 8 }}>{item.feedback}</p>
        </article>
      ))}

      <button className="primary" onClick={onRestart} style={{ marginTop: 32 }}>
        Simular outro exame
      </button>
    </section>
  )
}
