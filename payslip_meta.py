"""Deduit l'annee/mois d'un bulletin de paie a partir de son libelle.

L'annee vient du document lui-meme (et non de la date du jour) : le bulletin
de decembre telecharge en janvier va dans le dossier de l'annee precedente.
"""
import os
import re
import unicodedata
from datetime import date

MONTHS = {
    "janvier": 1, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6,
    "juillet": 7, "aout": 8, "septembre": 9, "octobre": 10, "novembre": 11,
    "decembre": 12,
}
MONTH_ABBR = {
    "janv": 1, "fevr": 2, "févr": 2, "avr": 4, "juil": 7, "sept": 9,
    "oct": 10, "nov": 11, "dec": 12,
}


def _norm(text):
    text = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def parse_period(text, today=None):
    """Retourne (annee, mois|None). Ordre : 'octobre 2026', '10/2026',
    '2026-10', annee seule, sinon date du jour."""
    t = _norm(text)
    words = "|".join(sorted(list(MONTHS) + list(MONTH_ABBR), key=len, reverse=True))
    m = re.search(rf"\b({words})\.?\s*(?:de\s+)?(20\d{{2}})\b", t)
    if m:
        w = m.group(1)
        return int(m.group(2)), MONTHS.get(w) or MONTH_ABBR[w]
    m = re.search(r"\b(0?[1-9]|1[0-2])\s*[/.-]\s*(20\d{2})\b", t)
    if m:
        return int(m.group(2)), int(m.group(1))
    m = re.search(r"\b(20\d{2})\s*[/.-]\s*(0?[1-9]|1[0-2])\b", t)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.search(r"\b(20\d{2})\b", t)
    if m:
        return int(m.group(1)), None
    return (today or date.today()).year, None


def dest_parts(text, subdir="Bulletins de paye", today=None, prefix="Bulletin"):
    """-> (chemin relatif 'ANNEE/Bulletins de paye', nom de fichier 'Employeur - 09_26.pdf')."""
    year, month = parse_period(text, today)
    if month:
        name = f"{prefix} - {month:02d}_{year % 100:02d}.pdf"
    else:
        name = "_".join(text.split()).replace("/", "-")[:80] + ".pdf"
    return f"{year}/{subdir}", name


# Nom affiche par MyPeopleDoc ("par PAYROLL CO.") -> nom utilise dans les fichiers.
# Se configure via PAYSLIP_EMPLOYERS (voir .env.example).
DEFAULT_EMPLOYERS = {}


def employer_map():
    """Table par defaut + surcharge via PAYSLIP_EMPLOYERS="PAYROLL CO=Globex;ACME SAS=Acme"."""
    mapping = dict(DEFAULT_EMPLOYERS)
    for pair in os.environ.get("PAYSLIP_EMPLOYERS", "").split(";"):
        if "=" in pair:
            k, v = pair.split("=", 1)
            mapping[k.strip().upper()] = v.strip()
    return mapping


def employer_from(text, default="Bulletin"):
    """Lit l'employeur dans 'Cree le ..., par PAYROLL CO. Taille ...' ; sinon `default`."""
    m = re.search(r"\bpar\s+(.+?)\.\s*(?:Taille|$)", " ".join(text.split()), re.I)
    if not m:
        return default
    raw = m.group(1).strip()
    mapping = employer_map()
    if raw.upper() in mapping:
        return mapping[raw.upper()]
    return re.sub(r"^groupe\s+", "", raw, flags=re.I)  # inconnu : nom brut sans "Groupe"
