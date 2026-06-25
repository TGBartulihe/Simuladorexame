// sw.js
//
// Service Worker do Simulador de Exame Nacional.
//
// Estratégia escolhida (decisão tomada em conversa: baixar tudo de uma vez
// na instalação, em vez de cache progressivo por exame acessado):
//   1. No "install", cacheia o app shell (HTML/JS/CSS/ícones) — isso é
//      pequeno e rápido, faz o app abrir instantaneamente já na primeira
//      instalação.
//   2. Em paralelo, cacheia TODOS os JSON de dados (catalog.json + os 152
//      exams/*.json + topics/*.json) — são ~5.7MB hoje, tamanho trivial,
//      e o resultado é que o aluno tem acesso a qualquer exame sem
//      internet, sem ficar descobrindo na hora que "esse aqui não foi
//      baixado ainda".
//   3. Em runtime, serve sempre do cache primeiro (cache-first) para os
//      dados — eles são estáticos por natureza (um exame de 2018 não
//      muda), então não há necessidade de revalidar contra a rede.
//
// Quando você gerar uma nova versão dos dados (rodando os scripts
// 01/02/03 de novo) e quiser que os PWAs já instalados peguem a
// atualização, troque o valor de CACHE_VERSION abaixo — isso invalida o
// cache antigo e força um novo download completo na próxima visita.

const CACHE_VERSION = 'v1'
const SHELL_CACHE = `exame-shell-${CACHE_VERSION}`
const DATA_CACHE = `exame-data-${CACHE_VERSION}`

// Este arquivo vive em public/, então NÃO passa pelo Vite — não há
// import.meta.env.BASE_URL disponível aqui (isso só existe no código que
// o bundler processa). Como o app é publicado em
// https://<user>.github.io/Simuladorexame/ (subpath, não raiz — ver nota
// em vite.config.js), derivamos a base a partir de onde o próprio
// Service Worker foi registado: self.location já contém o subpath certo,
// porque o navegador só registou o SW com aquele scope.
const BASE = self.location.pathname.replace(/sw\.js$/, '')

const SHELL_ASSETS = [
  BASE,
  `${BASE}index.html`,
  `${BASE}manifest.json`,
  `${BASE}icons/icon-192.png`,
  `${BASE}icons/icon-512.png`,
  `${BASE}icons/icon-maskable-192.png`,
  `${BASE}icons/icon-maskable-512.png`,
]

self.addEventListener('install', (event) => {
  event.waitUntil(
    (async () => {
      const shellCache = await caches.open(SHELL_CACHE)
      await shellCache.addAll(SHELL_ASSETS)

      // baixa o catálogo primeiro para saber a lista completa de exames
      const dataCache = await caches.open(DATA_CACHE)
      const catalogUrl = `${BASE}data/catalog.json`
      await dataCache.add(catalogUrl)

      const catalogResponse = await dataCache.match(catalogUrl)
      const catalog = await catalogResponse.json()

      const examUrls = catalog.subjects.flatMap((subject) =>
        subject.years.flatMap((year) =>
          year.exams
            .filter((exam) => exam.completeness !== 'sem_questoes_extraidas')
            .map((exam) => `${BASE}data/exams/${exam.examKey}.json`)
        )
      )

      const topicUrls = catalog.subjects.map(
        (subject) => `${BASE}data/topics/${subject.slug}.json`
      )

      // Promise.allSettled: se um arquivo de tópicos ainda não existir
      // (script 02 não rodou para essa disciplina), isso não deve
      // impedir o resto do cache de completar.
      await Promise.allSettled([
        ...examUrls.map((url) => dataCache.add(url)),
        ...topicUrls.map((url) => dataCache.add(url)),
      ])

      console.log(
        `[sw] cache completo: ${examUrls.length} exames + ${topicUrls.length} catálogos de tópicos`
      )
    })()
  )
  self.skipWaiting()
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    (async () => {
      // remove versões antigas de cache (de uma instalação anterior do app)
      const keys = await caches.keys()
      await Promise.all(
        keys
          .filter((key) => key !== SHELL_CACHE && key !== DATA_CACHE)
          .map((key) => caches.delete(key))
      )
      await self.clients.claim()
    })()
  )
})

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url)

  // dados: cache-first, porque são estáticos por natureza — um exame de
  // 2018 não muda nunca. Isso também é o que garante funcionamento 100%
  // offline depois da instalação.
  if (url.pathname.startsWith(`${BASE}data/`)) {
    event.respondWith(
      (async () => {
        const cached = await caches.match(event.request)
        if (cached) return cached

        // fallback de rede: cobre o caso de um exame novo ter sido
        // publicado depois da instalação do PWA (ex: você rodou os
        // scripts de novo e fez deploy, mas o cache do aluno é antigo)
        try {
          const fresh = await fetch(event.request)
          const dataCache = await caches.open(DATA_CACHE)
          dataCache.put(event.request, fresh.clone())
          return fresh
        } catch {
          return new Response(
            JSON.stringify({ error: 'Sem conexão e este dado não está no cache local.' }),
            { status: 503, headers: { 'Content-Type': 'application/json' } }
          )
        }
      })()
    )
    return
  }

  // app shell: cache-first com atualização em segundo plano (stale-while-
  // revalidate) — abre instantâneo, mas se houver internet, atualiza o
  // cache para a próxima visita.
  event.respondWith(
    (async () => {
      const cached = await caches.match(event.request)
      const networkFetch = fetch(event.request)
        .then((response) => {
          if (response.ok) {
            caches.open(SHELL_CACHE).then((cache) => cache.put(event.request, response.clone()))
          }
          return response
        })
        .catch(() => null)

      return cached || (await networkFetch) || Response.error()
    })()
  )
})
