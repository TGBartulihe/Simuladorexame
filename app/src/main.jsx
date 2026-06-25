import React from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.jsx'
import './styles.css'

createRoot(document.getElementById('root')).render(<App />)

// Registo do Service Worker — só em produção (build), para não cachear
// agressivamente durante o desenvolvimento com `npm run dev` e confundir
// alterações no código com "cache antigo".
//
// O caminho e o scope usam import.meta.env.BASE_URL porque este projeto
// é publicado no GitHub Pages num subpath (https://<user>.github.io/
// Simuladorexame/, não na raiz do domínio) — ver nota em vite.config.js.
// Registar com '/sw.js' fixo faria o navegador tentar um scope na raiz do
// domínio, fora da pasta do app, e o registo falharia silenciosamente.
if ('serviceWorker' in navigator && import.meta.env.PROD) {
  const base = import.meta.env.BASE_URL
  window.addEventListener('load', () => {
    navigator.serviceWorker
      .register(`${base}sw.js`, { scope: base })
      .then((reg) => console.log('[pwa] service worker registado', reg.scope))
      .catch((err) => console.error('[pwa] falha ao registar service worker', err))
  })
}
