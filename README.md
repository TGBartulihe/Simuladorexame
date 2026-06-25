# Simuladorexame

Simulador estático de exames nacionais baseado em dados estruturados.

## Objetivo

Permitir que um estudante escolha uma disciplina, selecione um exame e realize uma simulação com correção, critérios e acompanhamento de progresso.

## Arquitetura

- PDFs originais: não versionados
- SQLite: base local/processada
- JSON estáticos: consumidos pelo frontend
- React/Vite: interface publicada no GitHub Pages

## Desenvolvimento

```bash
python -m scripts.process_parser_v2
python -m scripts.export_static_site_data

cd app
npm install
npm run dev