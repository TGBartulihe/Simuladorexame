// lib/progressStore.js
//
// Persistência local do progresso do aluno. Como a arquitetura é
// SQLite -> JSON estático -> frontend (sem backend vivo), o progresso fica
// em localStorage no navegador do aluno. As estruturas gravadas espelham
// DELIBERADAMENTE o schema de student_attempts / student_answers /
// student_statistics do banco real — se um dia isto precisar ser
// sincronizado de volta para o SQLite (multi-dispositivo, professor vendo
// progresso da turma, etc.), o formato já está pronto para um INSERT direto,
// sem transformação.
//
// Isto é combinado com a regra "DB bem formada e consumida": mesmo correndo
// 100% no browser, os dados não inventam uma estrutura paralela.

const STORAGE_KEY = 'simulador_exame_progress_v1'

function readAll() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return { attempts: [], answers: [], statistics: {} }
    return JSON.parse(raw)
  } catch {
    return { attempts: [], answers: [], statistics: {} }
  }
}

function writeAll(data) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(data))
}

let nextAttemptId = null
let nextAnswerId = null

function ensureCounters(data) {
  if (nextAttemptId === null) {
    nextAttemptId = 1 + data.attempts.reduce((max, a) => Math.max(max, a.id), 0)
  }
  if (nextAnswerId === null) {
    nextAnswerId = 1 + data.answers.reduce((max, a) => Math.max(max, a.id), 0)
  }
}

/**
 * Cria um novo "student_attempts" e devolve o id.
 * student é um identificador livre de perfil local (não há login —
 * ver nota em ProgressSummary sobre multi-perfil).
 */
export function startAttempt({ student, examId }) {
  const data = readAll()
  ensureCounters(data)
  const attempt = {
    id: nextAttemptId++,
    student,
    exam_id: examId,
    started_at: new Date().toISOString(),
    finished_at: null,
    score: null,
  }
  data.attempts.push(attempt)
  writeAll(data)
  return attempt.id
}

/**
 * Fecha um attempt com a pontuação final e grava todas as respostas
 * (espelhando student_answers: attempt_id, question_id, answer,
 * is_correct, obtained_points, feedback).
 */
export function finishAttempt({ attemptId, score, answers }) {
  const data = readAll()
  ensureCounters(data)

  const attempt = data.attempts.find((a) => a.id === attemptId)
  if (attempt) {
    attempt.finished_at = new Date().toISOString()
    attempt.score = score
  }

  for (const ans of answers) {
    data.answers.push({
      id: nextAnswerId++,
      attempt_id: attemptId,
      question_id: ans.questionId,
      answer: ans.answer,
      is_correct: ans.isCorrect,
      obtained_points: ans.obtainedPoints,
      feedback: ans.feedback,
    })
  }

  writeAll(data)
  recomputeStatistics(data)
}

/**
 * Recalcula student_statistics (student, subject, topic, attempts,
 * success_rate) a partir de answers + attempts + metadata das questões
 * (que é passada pela tela que chama isto, pois aqui não temos acesso
 * direto aos JSONs de exame).
 */
function recomputeStatistics(data) {
  // o recálculo real de success_rate por tópico precisa cruzar com
  // subject/topic de cada questão, que só a tela de correção tem
  // disponível (carregou o exame). Por isso a API pública é
  // `recordTopicOutcome`, chamada questão a questão no momento da correção.
  writeAll(data)
}

/**
 * Registra o resultado de UMA questão para fins de estatística por tópico.
 * Chamado pela tela de correção, que tem o contexto subject/topic da
 * questão (o progressStore por si só não carrega JSONs de exame).
 */
export function recordTopicOutcome({ student, subject, topic, isCorrect }) {
  const data = readAll()
  const key = `${student}::${subject}::${topic || '(sem tópico classificado)'}`

  if (!data.statistics[key]) {
    data.statistics[key] = {
      student,
      subject,
      topic: topic || null,
      attempts: 0,
      correct: 0,
    }
  }

  const stat = data.statistics[key]
  stat.attempts += 1
  if (isCorrect) stat.correct += 1

  writeAll(data)
}

/**
 * Devolve as estatísticas por tópico de uma disciplina, já com
 * success_rate calculado, ordenadas da maior dificuldade para a menor
 * (menor taxa de acerto primeiro) — é a base direta do "onde você ainda
 * tem dificuldade" pedido para a tela de progresso.
 */
export function getTopicStatistics({ student, subject }) {
  const data = readAll()
  return Object.values(data.statistics)
    .filter((s) => s.student === student && s.subject === subject)
    .map((s) => ({
      topic: s.topic,
      attempts: s.attempts,
      successRate: s.attempts > 0 ? s.correct / s.attempts : 0,
    }))
    .sort((a, b) => a.successRate - b.successRate)
}

export function getAllAttempts({ student }) {
  const data = readAll()
  return data.attempts.filter((a) => a.student === student)
}

export function getDefaultStudentId() {
  // Sem sistema de login: usa um id de perfil local persistente.
  // Isto é deliberadamente simples — se no futuro houver múltiplos
  // perfis no mesmo dispositivo, troque esta função pela tela de seleção
  // de perfil e passe o id escolhido para as funções acima.
  let id = localStorage.getItem('simulador_exame_student_id')
  if (!id) {
    id = `aluno-${Math.random().toString(36).slice(2, 10)}`
    localStorage.setItem('simulador_exame_student_id', id)
  }
  return id
}
