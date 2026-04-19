HTML_PATH = r"c:\Users\diego\Documents\Proyectos Python\generador de csv\templates\index.html"

with open(HTML_PATH, "r", encoding="utf-8") as f:
    html = f.read()

# Fix the nested backticks issue where \"` is inserted inside string literal.
# We want to change: reTrans(document.getElementById(\'`edu-${id}`\')); 
# to: reTrans(document.getElementById(`edu-${id}`));
html = html.replace("document.getElementById(\\'`", "document.getElementById(`")
html = html.replace("`\\')", "` )")

with open(HTML_PATH, "w", encoding="utf-8") as f:
    f.write(html)
