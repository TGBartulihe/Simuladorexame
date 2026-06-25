// lib/dataApi.js
//
// Camada de acesso aos JSONs estáticos gerados por
// scripts/03_export_static_site_data.py. Mantém o resto da app sem saber
// onde os dados vivem fisicamente — se um dia isto virar uma API real em
// vez de arquivos estáticos, só este arquivo muda.

const DATA_BASE = '/data'

async function fetchJson(path) {
  const res = await fetch(`${DATA_BASE}/${path}`)
  if (!res.ok) {
    throw new Error(`Não foi possível carregar ${path} (HTTP ${res.status})`)
  }
  return res.json()
}

export async function loadCatalog() {
  return fetchJson('catalog.json')
}

export async function loadExam(examKey) {
  return fetchJson(`exams/${examKey}.json`)
}

export async function loadTopics(subjectSlug) {
  try {
    return await fetchJson(`topics/${subjectSlug}.json`)
  } catch {
    // ainda não foi gerado (script 02 não rodou para esta disciplina) —
    // não é um erro fatal, a UI deve continuar funcionando sem tópicos.
    return { subject: null, topics: [] }
  }
}

// Remove questões com enunciado corrompido (ver nota no script de export)
// antes de a UI sequer enxergá-las. Nenhum componente de tela deve
// precisar saber sobre esse detalhe de qualidade de dados.
export function usableQuestions(exam) {
  return exam.questions.filter((q) => !q.statementCorrompido)
}
