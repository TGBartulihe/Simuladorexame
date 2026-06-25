<<<<<<< HEAD
# Simuladorexame

PoC privada para consolidar uma biblioteca local de exames nacionais do IAVE, extrair conteúdo para JSON e disponibilizar uma interface simples de simulação.

## Ideia central

- O GitHub guarda código, scripts e dados estruturados.
- Os PDFs ficam localmente em `storage/`, ignorados pelo Git.
- A aplicação consome JSON em `library/parsed/`.

## Primeiros comandos

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt

python scripts/discover_library.py
python scripts/download_library.py
python scripts/extract_text.py
python scripts/build_library.py
python scripts/validate_library.py
```

## App

```bash
cd app
npm install
npm run dev
```

## Estado atual

Esta é a base inicial do projeto. O crawler está preparado para ser evoluído com regras reais da estrutura IAVE. Por segurança, o projeto não versiona PDFs.
=======
# Simuladorexame
>>>>>>> f1ecdf565426e86d1801be352ba06a177028303d
