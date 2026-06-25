// engine/correctionEngine.js
//
// Corrige uma tentativa de exame cruzando as respostas do aluno com o
// gabarito real vindo do export (choices[].isCorrect, criteriaText,
// pontuacaoDisponivel). Substitui a versão anterior que trabalhava sobre
// dados mockados ("pendente de extração").
//
// Princípio: nunca inventar uma nota para o que os dados não sustentam.
// Quando o gabarito ou a pontuação não estão disponíveis, a questão entra
// no resultado como "needsManualReview", não como certa nem errada.

function correctMultipleChoice(question, studentAnswerLetter) {
  if (!question.gabaritoDisponivel) {
    return {
      isCorrect: null,
      obtainedPoints: null,
      feedback: 'Gabarito ainda não confirmado para esta questão nesta base de dados.',
      needsManualReview: true,
    }
  }

  const correctLetters = question.choices.filter((c) => c.isCorrect).map((c) => c.letter)
  const isCorrect = studentAnswerLetter != null && correctLetters.includes(studentAnswerLetter)
  const maxPoints = question.pontuacaoDisponivel ? question.max_points : null

  return {
    isCorrect,
    obtainedPoints: maxPoints != null ? (isCorrect ? maxPoints : 0) : null,
    feedback: isCorrect
      ? 'Resposta certa.'
      : `Resposta certa: ${correctLetters.join(' ou ')}.`,
    needsManualReview: false,
  }
}

function correctOpenEnded(question, studentAnswerText) {
  const hasAnswer = Boolean(studentAnswerText && studentAnswerText.trim())

  // Questões abertas (open/essay/calculation) não têm correção automática
  // confiável — o critério oficial é texto livre de rubrica, não uma
  // resposta exata comparável. A correção aqui é sempre "para revisão",
  // mostrando o critério oficial lado a lado com a resposta do aluno.
  return {
    isCorrect: null,
    obtainedPoints: null,
    feedback: hasAnswer
      ? 'Resposta registada. Compare com o critério oficial abaixo — a pontuação final depende de avaliação por rubrica.'
      : 'Questão sem resposta.',
    needsManualReview: true,
  }
}

export function correctExam(exam, usableQuestions, answers) {
  const items = usableQuestions.map((q) => {
    const studentAnswer = answers[q.id] ?? null

    const outcome =
      q.question_type === 'multiple_choice'
        ? correctMultipleChoice(q, studentAnswer)
        : correctOpenEnded(q, studentAnswer)

    return {
      questionId: q.id,
      number: q.question_number,
      type: q.question_type,
      groupName: q.groupName,
      topic: q.topic,
      subtopic: q.subtopic,
      maxPoints: q.pontuacaoDisponivel ? q.max_points : null,
      statement: q.statement,
      choices: q.choices,
      criteriaText: q.criteriaText,
      studentAnswer,
      ...outcome,
    }
  })

  const autoGraded = items.filter((i) => i.obtainedPoints != null)
  const totalAutoPoints = autoGraded.reduce((sum, i) => sum + i.obtainedPoints, 0)
  const maxAutoPoints = autoGraded.reduce((sum, i) => sum + i.maxPoints, 0)
  const pendingReviewCount = items.filter((i) => i.needsManualReview).length

  return {
    examId: exam.examId,
    examKey: exam.examKey,
    subject: exam.subject,
    year: exam.year,
    phase: exam.phase,
    items,
    scoring: {
      autoGradedPoints: totalAutoPoints,
      autoGradedMaxPoints: maxAutoPoints,
      // null se nada pôde ser auto-corrigido — evita "0 de 0" parecer um zero real
      autoGradedPercentage: maxAutoPoints > 0 ? totalAutoPoints / maxAutoPoints : null,
      pendingReviewCount,
      totalQuestions: items.length,
    },
  }
}
