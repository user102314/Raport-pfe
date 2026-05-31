#!/usr/bin/env python3
"""Nettoie finalyearrapport.tex : placeholders, chemins .png/.mmd, tableaux."""
import re
from pathlib import Path

TEX = Path(__file__).resolve().parents[1] / "finalyearrapport.tex"
text = TEX.read_text(encoding="utf-8")

# --- Supprimer sections éditoriales entières (ch. II et IV) ---
text = re.sub(
    r"\t%----------------------------------------------------------------\n"
    r"\t\\section\{Figures et diagrammes prévus pour ce chapitre\}.*?"
    r"\t%----------------------------------------------------------------\n"
    r"\t\\section{Conclusion}",
    lambda _m: "\t%----------------------------------------------------------------\n\t\\section{Conclusion}",
    text,
    count=1,
    flags=re.DOTALL,
)

text = re.sub(
    r"\t%------------------------------------------------------------------\n"
    r"\t\\section\{Figures et diagrammes du chapitre\}.*?"
    r"\t%------------------------------------------------------------------\n"
    r"\t\\section{Conclusion}",
    lambda _m: "\t%------------------------------------------------------------------\n\t\\section{Conclusion}",
    text,
    count=1,
    flags=re.DOTALL,
)

# --- Sous-section diagrammes mobile (tableau avec noms de fichiers) ---
text = re.sub(
    r"\t\\subsubsection\{Diagrammes recommandés pour cette interaction\}.*?"
    r"\t\\IfFileExists\{public/exucution\.png\}",
    lambda _m: "\t\\IfFileExists{public/exucution.png}",
    text,
    count=1,
    flags=re.DOTALL,
)

# --- Lignes éditoriales avec chemins sources ---
patterns_remove_line = [
    r"^\t.*Source Mermaid~:.*\n",
    r"^\t.*Source~:.*(?:plantuml|mermaid|\.puml|\.mmd|\.png).*\n",
    r"^\t.*\\texttt\{mermaid/.*\}.*\n",
    r"^\t.*\\texttt\{plantuml/.*\}.*\n",
    r"^\t.*vers\s*\n",
    r"^\t.*\\texttt\{public/[^}]+\}.*\n",
    r"^\t.*Le diagramme \\texttt\{mermaid/.*\n",
    r"^\t.*fichier source : \\texttt\{plantuml/.*\n",
    r"^\t.*diagramme source \\texttt\{plantuml/.*\n",
    r"^\t% Chemin suggéré.*\n",
]
for pat in patterns_remove_line:
    text = re.sub(pat, "", text, flags=re.MULTILINE)

# --- Placeholders visibles ---
text = re.sub(
    r"\t\t\t\\noindent\\textit\{\(Figure à ajouter[^}]*\}\)\n",
    "",
    text,
)
text = re.sub(
    r"\t\t\\noindent\\textit\{\(Figure à ajouter[^}]*\}\)\n",
    "",
    text,
)
text = re.sub(
    r"\t\t\\noindent\\textit\{\(Figure optionnelle[^)]*\)\}\n",
    "",
    text,
)
text = re.sub(
    r"\t\t\t\\noindent\\textit\{\(Figure optionnelle[^)]*\)\}\n",
    "",
    text,
)

# --- Blocs minipage "Emplacement réservé" / "Figure à ajouter" ---
text = re.sub(
    r"\t\}\{\%\n"
    r"\t\t\\begin\{center\}.*?"
    r"\t\t\\end\{center\}\n"
    r"\t\}",
    "\t}{}",
    text,
    flags=re.DOTALL,
)

# --- Corriger phrases coupées (vers seul) ---
text = text.replace(
    "est exporté depuis\n\t\n",
    "est présenté dans la section modélisation.\n\t\n",
)

# --- tabularx : colonnes X sans retour à la ligne ---
RAGGED_X = r">{\\raggedright\\arraybackslash}X"
RAGGED_P = r"|>{\\raggedright\\arraybackslash}p{"

def fix_tabularx(m):
    body = m.group(0)
    body = re.sub(
        r"(?<![\\arraybackslash])X(?=\||\})",
        RAGGED_X,
        body,
    )
    body = re.sub(
        r"\|p\{([^}]+)\}",
        lambda mo: RAGGED_P + mo.group(1) + "}",
        body,
    )
    body = body.replace(
        ">{\raggedright\\arraybackslash}>" + RAGGED_X.replace("X", "").rstrip("X"),
        ">{\raggedright\\arraybackslash}",
    )
    return body


def fix_tabular(m):
    body = m.group(0)
    if "raggedright" in body:
        return body
    body = re.sub(
        r"\|p\{([^}]+)\}",
        lambda mo: RAGGED_P + mo.group(1) + "}",
        body,
    )
    return body

text = re.sub(
    r"\\begin\{tabularx\}.*?\\end\{tabularx\}",
    fix_tabularx,
    text,
    flags=re.DOTALL,
)

text = re.sub(
    r"\\begin\{tabular\}\{[^}]*\}.*?\\end\{tabular\}",
    fix_tabular,
    text,
    flags=re.DOTALL,
)

# --- Références intro ch4 diagrammes ---
text = text.replace(
    "Les diagrammes PlantUML associés sont\n\tlistés au §~\\ref{sec:ch4-diagrammes}.",
    "",
)

text = re.sub(r"\n{4,}", "\n\n\n", text)

TEX.write_text(text, encoding="utf-8")
print("Done:", TEX)
