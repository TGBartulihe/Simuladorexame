import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// GitHub Pages serve este projeto em https://<user>.github.io/Simuladorexame/
// (não na raiz do domínio, porque o repo não se chama <user>.github.io).
//
// Por que base ABSOLUTO (não './'): testamos usar base relativa para
// evitar configurar o nome do repo aqui, mas import.meta.env.BASE_URL não
// fica utilizável para fetch() quando base é relativo — ele não resolve
// para um caminho consistente em runtime. Com base absoluto,
// import.meta.env.BASE_URL é confiável tanto em dev ('/') quanto em build
// ('/Simuladorexame/'), e é isso que lib/dataApi.js e main.jsx usam para
// montar as URLs de fetch e o registo do Service Worker.
//
// ATENÇÃO — três lugares precisam do MESMO nome de repo, manualmente:
//   1. REPO_NAME aqui
//   2. os caminhos absolutos dentro de public/manifest.json
//      (start_url, scope, e cada icons[].src)
//   3. nada mais — index.html usa %BASE_URL% (substituição nativa do
//      Vite) e sw.js deriva de self.location, então esses dois não
//      precisam de edição manual.
// Se о nome do repositório mudar, edite o valor abaixo E os caminhos no
// manifest.json. Não há como evitar essa duplicação: manifest.json é um
// arquivo estático, servido tal como está, sem passar pelo processamento
// de variáveis do Vite.
const REPO_NAME = 'Simuladorexame'

export default defineConfig({
  plugins: [react()],
  base: `/${REPO_NAME}/`,
})
