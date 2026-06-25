"""
generate_icons.py

Gera os ícones do PWA a partir da identidade visual já definida em
styles.css (azul-tinta + papel + dourado-selo). Desenho simples e
vetorial-like: nenhuma dependência de fonte específica do sistema além
de uma fallback segura, para o resultado ser reproduzível em qualquer
máquina.

Motivo de existir como script (em vez de só entregar os PNGs prontos):
se você ajustar a paleta em styles.css no futuro, basta rodar de novo
para os ícones acompanharem a mudança.
"""

from PIL import Image, ImageDraw, ImageFont

INK = (11, 27, 51)       # --ink
PAPER = (247, 244, 236)  # --paper
GOLD = (196, 166, 97)    # --gold


def draw_mark(size: int, padding_ratio: float) -> Image.Image:
    """Desenha o selo: fundo azul-tinta, círculo dourado, e um traço em
    forma de check estilizado (aprovação de exame) no centro.
    """
    img = Image.new("RGBA", (size, size), INK + (255,))
    draw = ImageDraw.Draw(img)

    padding = int(size * padding_ratio)
    circle_box = [padding, padding, size - padding, size - padding]
    draw.ellipse(circle_box, outline=GOLD + (255,), width=max(2, size // 40))

    # "check" estilizado como dois segmentos de linha, espessura proporcional
    cx, cy = size / 2, size / 2
    r = (size - 2 * padding) / 2
    p1 = (cx - r * 0.45, cy + r * 0.05)
    p2 = (cx - r * 0.12, cy + r * 0.40)
    p3 = (cx + r * 0.50, cy - r * 0.35)

    line_width = max(3, size // 22)
    draw.line([p1, p2], fill=PAPER + (255,), width=line_width, joint="curve")
    draw.line([p2, p3], fill=PAPER + (255,), width=line_width, joint="curve")
    # arredonda as pontas (PIL não faz isso nativamente em linhas)
    for p in (p1, p2, p3):
        r_dot = line_width / 2
        draw.ellipse([p[0] - r_dot, p[1] - r_dot, p[0] + r_dot, p[1] + r_dot], fill=PAPER + (255,))

    return img


def save_icon(size: int, maskable: bool, out_path: str) -> None:
    # ícones "maskable" precisam de uma margem de segurança maior (o SO
    # pode recortar em círculo/squircle) — por isso o padding é maior
    padding_ratio = 0.22 if maskable else 0.12
    img = draw_mark(size, padding_ratio)
    img.save(out_path, "PNG")
    print(f"gerado: {out_path} ({size}x{size}, maskable={maskable})")


if __name__ == "__main__":
    import os

    out_dir = "public/icons"
    os.makedirs(out_dir, exist_ok=True)

    save_icon(192, maskable=False, out_path=f"{out_dir}/icon-192.png")
    save_icon(512, maskable=False, out_path=f"{out_dir}/icon-512.png")
    save_icon(192, maskable=True, out_path=f"{out_dir}/icon-maskable-192.png")
    save_icon(512, maskable=True, out_path=f"{out_dir}/icon-maskable-512.png")
