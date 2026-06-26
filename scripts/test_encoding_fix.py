"""
test_encoding_fix.py — utilitário de diagnóstico (não faz parte do
pipeline). Testa se o texto extraído do PDF de critério está com
mojibake (UTF-8 decodificado como cp1252) e se a correção
texto.encode('cp1252').decode('utf-8') resolve, sem perder dados.

Uso:
    python scripts/test_encoding_fix.py --file debug_pilot_output/criteria_raw.txt
"""
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--file", required=True)
args = parser.parse_args()

with open(args.file, encoding="utf-8") as f:
    original = f.read()

print("=== Amostra do texto ORIGINAL (primeiros 300 chars) ===")
print(original[:300])
print()

try:
    corrigido = original.encode("cp1252").decode("utf-8")
    print("=== Amostra do texto CORRIGIDO (primeiros 300 chars) ===")
    print(corrigido[:300])
    print()
    print("Correção aplicada SEM ERRO.")

    # heurística simples: o texto corrigido deve ter menos ocorrências de
    # sequências de mojibake típicas (Ã, â€) do que o original
    mojibake_antes = original.count("Ã") + original.count("â€")
    mojibake_depois = corrigido.count("Ã") + corrigido.count("â€")
    print(f"\nOcorrências de mojibake (Ã / â€): antes={mojibake_antes}, depois={mojibake_depois}")
    if mojibake_depois < mojibake_antes:
        print("MELHOROU — a correção parece estar certa.")
    else:
        print("NÃO MELHOROU — algo está diferente do esperado, não aplicar ainda.")

except UnicodeDecodeError as e:
    print(f"ERRO ao tentar corrigir: {e}")
    print("Isto pode significar que o mojibake não é simples cp1252->utf-8,")
    print("ou que o arquivo já está parcialmente correto em algumas partes.")
