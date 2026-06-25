# apply_parser_fixes.ps1
#
# Move/renomeia os arquivos corrigidos do parser para os caminhos certos
# dentro do repositorio, e limpa o bytecode em cache.
#
# Uso: rode este script a partir da RAIZ do repositorio
# (C:\github\Repositories\Simuladorexame), com os 7 arquivos baixados
# em $SourceDir (ajuste a variavel abaixo se nao estiverem em Downloads).

$SourceDir = "$env:USERPROFILE\Downloads"

$moves = @(
    @{ From = "question_boundaries.py";          To = "parser\utils\question_boundaries.py" },
    @{ From = "clean_text_corrigido.py";         To = "parser\utils\clean_text.py" },
    @{ From = "parse_groups_corrigido.py";       To = "parser\parse\parse_groups.py" },
    @{ From = "parse_questions_corrigido.py";    To = "parser\parse\parse_questions.py" },
    @{ From = "extract_contexts_corrigido.py";   To = "parser\extract\extract_contexts.py" },
    @{ From = "parse_criteria_corrigido.py";     To = "parser\parse\parse_criteria.py" },
    @{ From = "extract_pdf_corrigido.py";        To = "parser\extract\extract_pdf.py" },
    @{ From = "batch_extract_corrigido.py";      To = "parser\extract\batch_extract.py" }
)

Write-Host "=== Aplicando correcoes do parser ===" -ForegroundColor Cyan
Write-Host "Origem: $SourceDir`n"

$missing = @()
$applied = @()

foreach ($move in $moves) {
    $sourcePath = Join-Path $SourceDir $move.From
    $destPath = $move.To

    if (-not (Test-Path $sourcePath)) {
        $missing += $move.From
        Write-Host "  [FALTA] $($move.From) nao encontrado em $SourceDir" -ForegroundColor Yellow
        continue
    }

    $destDir = Split-Path $destPath -Parent
    if (-not (Test-Path $destDir)) {
        Write-Host "  [AVISO] pasta de destino '$destDir' nao existe -- criando" -ForegroundColor Yellow
        New-Item -ItemType Directory -Path $destDir -Force | Out-Null
    }

    Copy-Item -Path $sourcePath -Destination $destPath -Force
    $applied += $destPath
    Write-Host "  [OK] $($move.From) -> $destPath" -ForegroundColor Green
}

Write-Host "`n=== Limpando __pycache__ dentro de parser/ ===" -ForegroundColor Cyan
$pycacheDirs = Get-ChildItem -Path parser -Include __pycache__ -Recurse -Directory -ErrorAction SilentlyContinue
if ($pycacheDirs) {
    $pycacheDirs | Remove-Item -Recurse -Force
    Write-Host "  $($pycacheDirs.Count) pasta(s) __pycache__ removida(s)." -ForegroundColor Green
} else {
    Write-Host "  Nenhuma pasta __pycache__ encontrada." -ForegroundColor Gray
}

Write-Host "`n=== Resumo ===" -ForegroundColor Cyan
Write-Host "Aplicados: $($applied.Count)/$($moves.Count)"
if ($missing.Count -gt 0) {
    Write-Host "Faltando: $($missing -join ', ')" -ForegroundColor Yellow
    Write-Host "Baixe os arquivos faltantes e rode o script de novo, ou copie manualmente." -ForegroundColor Yellow
} else {
    Write-Host "Todos os arquivos foram aplicados com sucesso." -ForegroundColor Green
}
