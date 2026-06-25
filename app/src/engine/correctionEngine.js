export function correctExam(exam, answers) {
  const items = exam.questions.map((q) => {
    const answer = answers[q.id] || ''
    return {
      questionId: q.id,
      number: q.number,
      mode: q.correctionMode || 'rubric',
      answer,
      officialCriteria: q.officialCriteria || 'Sem critério associado.',
      feedback: answer.trim()
        ? 'Resposta registada. Nesta fase, a correção aberta é assistida por rubrica.'
        : 'Questão sem resposta. Deve ser marcada como zero ou para revisão manual.'
    }
  })

  return {
    examId: exam.examId,
    estimatedScore: 'pendente de rubrica',
    items
  }
}
