import re

HTML_PATH = r"c:\Users\diego\Documents\Proyectos Python\generador de csv\templates\index.html"

with open(HTML_PATH, "r", encoding="utf-8") as f:
    html = f.read()

# Fix the ${t('...')} in HTML body (outside of template literals in scripts)
# Pattern: looking for text that is typically inside HTML tags
# We want to change `${t('Datos Personales')}` back to `Datos Personales`

# Since I know the common ones:
replacements = {
    "${t('Datos Personales')}": "Datos Personales",
    "${t('Competencias')}": "Competencias",
    "${t('Idiomas')}": "Idiomas",
    "${t('Cursos')}": "Cursos",
    "${t('Intereses')}": "Intereses"
}

for old, new in replacements.items():
    html = html.replace(old, new)

with open(HTML_PATH, "w", encoding="utf-8") as f:
    f.write(html)

print("Cleaned index.html static tags")
