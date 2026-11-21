"""Gera o PDF do manual a partir dos capítulos em Markdown.

    python ferramentas/gerar_pdf.py            # manual completo -> pdf/manual-sisgec.pdf
    python ferramentas/gerar_pdf.py 07         # um capítulo     -> pdf/capitulo-07.pdf

Precisa de: pip install markdown  — e do Microsoft Edge (imprime o PDF).
"""
import datetime as dt
import html
import re
import subprocess
import sys
import time
from pathlib import Path

import markdown

RAIZ = Path(__file__).resolve().parents[1]
MANUAL = RAIZ / "manual"
SAIDA = RAIZ / "pdf"
VERSAO = "2.10.1"
AUTOR = "EZAÚ LAURENTINO PAULINO - 1º Sgt"
CONTATO = "linkedin.com/in/ezaulaurentino"
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

SUBTITULOS = {
    "00": "O que é o SISGEC, como entrar e como a tela se organiza",
    "01": "Contas de acesso, perfis e redefinição de senha",
    "02": "Cadastro, situação e histórico das viaturas",
    "03": "OMs, postos de combustível e órgão controlador",
    "04": "Planejar, aprovar e encerrar missões",
    "05": "Saída e chegada de viaturas no portão",
    "06": "Efetivo, situação de cada militar e quem está fora",
    "07": "Pedir, autorizar e registrar o combustível de uma viatura",
    "08": "Cotas recebidas, saldo e débitos",
    "09": "Régua diária do tanque e livro de lacres",
    "10": "Escala, folgas e trocas de serviço",
    "11": "Leitura do BI e resultados de TAF e TAT",
    "12": "Notas fiscais de combustível e anexos",
    "13": "Relatórios e trilha de auditoria",
    "14": "Deslocamentos publicados em BI e o QSGR",
}

ALERTAS = {"NOTE": "nota", "TIP": "resumo", "WARNING": "atencao", "IMPORTANT": "atencao", "CAUTION": "atencao"}


def alertas_para_html(md: str) -> str:
    """> [!NOTE] ... (sintaxe do GitHub) vira <div class="caixa ..."> no PDF."""
    def troca(m):
        tipo = ALERTAS[m.group(1)]
        corpo = re.sub(r"^> ?", "", m.group(2), flags=re.M)
        return f'<div class="caixa {tipo}" markdown="1">\n\n{corpo}\n\n</div>\n'
    return re.sub(r"^> \[!(\w+)\]\n((?:^>.*\n?)+)", troca, md, flags=re.M)


def largura_png(arq: Path) -> int:
    with open(arq, "rb") as f:
        return int.from_bytes(f.read(24)[16:20], "big")


def figura(m) -> str:
    """Tela inteira ocupa a largura; recorte (janela, formulário) fica no
    tamanho proporcional, para não virar letra gigante no papel."""
    arq = MANUAL / m.group(2)
    estilo = ""
    if largura_png(arq) < 2400:  # prints em 2x: tela cheia tem 2880 px
        estilo = f' style="width:{largura_png(arq) / 2880 * 100:.0f}%"'
    return (f'<figure><img src="{arq.as_uri()}"{estilo}/>'
            f'<figcaption>{m.group(1)}</figcaption></figure>')


def capitulo_html(arq: Path) -> tuple[str, str, str]:
    num = arq.name[:2]
    md = arq.read_text(encoding="utf-8")
    titulo = re.search(r"^# (.+)$", md, re.M).group(1).strip()
    md = re.sub(r"^# .+\n", "", md, count=1, flags=re.M)
    md = re.sub(r"\[`?([^\]`]+\.webm)`?\]\([^)]+\)", r"<b>\1</b> (na pasta videos do repositório)", md)
    corpo = markdown.markdown(alertas_para_html(md), extensions=["tables", "md_in_html", "sane_lists"])
    corpo = re.sub(r'<img alt="([^"]*)" src="([^"]+)" />', figura, corpo)
    abertura = (f'<header class="abre"><div class="num">{num}</div><div class="tt">'
                f'<div class="sec">CAPÍTULO {num}</div><h1>{html.escape(titulo)}</h1>'
                f'<span class="pill">{html.escape(SUBTITULOS.get(num, ""))}</span></div></header>')
    return num, titulo, f'<section class="cap">{abertura}{corpo}</section>'


def montar(capitulos: list[Path], completo: bool) -> str:
    css = (Path(__file__).parent / "manual.css").read_text(encoding="utf-8")
    partes = [capitulo_html(c) for c in capitulos]
    hoje = dt.date.today().strftime("%m/%Y")
    selo = (MANUAL / "img" / "selo.png").as_uri()
    capa = f"""<section class="capa">
      <img class="selo" src="{selo}"/>
      <div class="org">SISTEMA DE GESTÃO E CONTROLE</div>
      <h1>SISGEC</h1>
      <div class="tit">MANUAL DO USUÁRIO</div>
      <p class="sub">{'Todos os módulos, passo a passo, com as telas do sistema' if completo else f'Capítulo {partes[0][0]} — {html.escape(partes[0][1])}'}</p>
      <div class="rod">Versão {VERSAO} · {hoje}</div>
    </section>"""
    sumario = ""
    if completo:
        linhas = "".join(f"<tr><td>{n}</td><td>{html.escape(t)}</td><td>{html.escape(SUBTITULOS.get(n, ''))}</td></tr>"
                         for n, t, _ in partes)
        sumario = (f'<section class="sumario"><h2>SUMÁRIO</h2><table><thead><tr><th>CAP.</th><th>MÓDULO</th>'
                   f'<th>ASSUNTO</th></tr></thead><tbody>{linhas}</tbody></table></section>')
    meses = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
             "setembro", "outubro", "novembro", "dezembro"]
    d = dt.date.today()
    fecho = (f'<section class="fecho"><p class="local">Curitiba - PR, {d.day} de {meses[d.month - 1]} de {d.year}.</p>'
             f'<p class="nome">{AUTOR}</p><p>Responsável pelo SISGEC</p><p>Contato: {CONTATO}</p></section>')
    return (f'<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><title>Manual do SISGEC</title>'
            f'<style>{css}</style></head><body>{capa}{sumario}{"".join(p[2] for p in partes)}{fecho if completo else ""}</body></html>')


def imprimir(html_txt: str, pdf: Path) -> None:
    tmp = SAIDA / f".{pdf.stem}.html"
    tmp.write_text(html_txt, encoding="utf-8")
    pdf.unlink(missing_ok=True)
    subprocess.run([EDGE, "--headless", "--disable-gpu", "--no-pdf-header-footer",
                    "--allow-file-access-from-files", f"--print-to-pdf={pdf}", tmp.as_uri()],
                   check=True, capture_output=True, timeout=180)
    # O Edge às vezes devolve o controle antes de terminar de gravar:
    # espera o arquivo existir e o tamanho parar de mudar.
    anterior = -1
    for _ in range(240):
        atual = pdf.stat().st_size if pdf.exists() else -1
        if atual > 0 and atual == anterior:
            break
        anterior = atual
        time.sleep(0.5)
    else:
        raise RuntimeError(f"O Edge não gerou {pdf.name}")
    tmp.unlink()
    print(f"[ok] {pdf.relative_to(RAIZ)}")


if __name__ == "__main__":
    SAIDA.mkdir(exist_ok=True)
    todos = sorted(MANUAL.glob("[0-9][0-9]-*.md"))
    if len(sys.argv) > 1:
        escolhidos = [c for c in todos if c.name.startswith(sys.argv[1])]
        imprimir(montar(escolhidos, completo=False), SAIDA / f"capitulo-{sys.argv[1]}.pdf")
    else:
        imprimir(montar(todos, completo=True), SAIDA / "manual-sisgec.pdf")
