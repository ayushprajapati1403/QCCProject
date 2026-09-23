"""make_pdf.py - render a Markdown report to PDF with rendered math and tables (Chromium via playwright).
Usage: python scripts/reports/make_pdf.py input.md output.pdf
Math is typeset with MathJax from the CDN when reachable; otherwise the LaTeX source is left as text.
"""
import sys, markdown, re, pathlib, os

src, dst = sys.argv[1], sys.argv[2]
text = pathlib.Path(src).read_text(encoding="utf-8")
math_blocks = []
def _stash(m):
    math_blocks.append(m.group(0)); return f"@@MATH{len(math_blocks) - 1}@@"
text = re.sub(r"\$\$.*?\$\$", _stash, text, flags=re.S)
text = re.sub(r"\$[^\$\n]+?\$", _stash, text)
html_body = markdown.markdown(text, extensions=["tables", "fenced_code", "toc", "sane_lists"])
for i, m in enumerate(math_blocks):
    html_body = html_body.replace(f"@@MATH{i}@@", m)
mathjax_src = os.environ.get("MATHJAX_SRC", "https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js")
html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<script>window.MathJax = {{tex: {{inlineMath: [['$','$']], displayMath: [['$$','$$']]}}, svg: {{fontCache: 'global'}}, startup: {{typeset: true}}}};</script>
<script src="{mathjax_src}"></script>
<style>
body {{ font-family: 'Segoe UI', Helvetica, Arial, sans-serif; font-size: 10.5pt; line-height: 1.45; color: #111; max-width: 190mm; margin: 0 auto; }}
h1 {{ font-size: 20pt; margin-top: 0; }} h2 {{ font-size: 14pt; margin-top: 1.4em; border-bottom: 1px solid #ccc; padding-bottom: 2px; }} h3 {{ font-size: 11.5pt; }}
table {{ border-collapse: collapse; font-size: 8.5pt; margin: 0.6em 0; width: 100%; }}
th, td {{ border: 1px solid #bbb; padding: 3px 5px; vertical-align: top; }} th {{ background: #f0f0f0; }}
code {{ font-family: Consolas, monospace; font-size: 9pt; background: #f5f5f5; padding: 0 2px; }}
pre {{ background: #f5f5f5; padding: 6px; font-size: 8.5pt; white-space: pre-wrap; }}
blockquote {{ color: #444; border-left: 3px solid #ccc; padding-left: 8px; }}
</style></head><body>{html_body}</body></html>"""
pathlib.Path(dst).with_suffix(".html").write_text(html, encoding="utf-8")

from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.set_content(html, wait_until="domcontentloaded", timeout=120000)
    try:
        page.wait_for_function("window.MathJax && MathJax.typesetPromise", timeout=45000)
        page.evaluate("() => MathJax.startup.promise.then(() => MathJax.typesetPromise())")
        page.wait_for_timeout(1500)
        print("math typeset with MathJax")
    except Exception as e:
        print("MathJax unavailable, leaving LaTeX as text:", type(e).__name__)
    page.pdf(path=dst, format="A4", margin={"top": "16mm", "bottom": "16mm", "left": "14mm", "right": "14mm"}, print_background=True)
    browser.close()
print("wrote", dst)
