import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from payslip_meta import dest_parts, employer_from, parse_period


def test_mois_en_toutes_lettres():
    assert parse_period("Bulletin de paie Octobre 2026") == (2026, 10)
    assert parse_period("Fiche de paie Février 2025") == (2025, 2)
    assert parse_period("Décembre 2025 - 12 pages") == (2025, 12)


def test_formats_numeriques():
    assert parse_period("Paie 03/2026") == (2026, 3)
    assert parse_period("paie 2026-11") == (2026, 11)


def test_annee_seule_et_repli():
    assert parse_period("Bulletin 2024") == (2024, None)
    assert parse_period("Bulletin", today=date(2026, 5, 1)) == (2026, None)


def test_annee_du_document_pas_du_jour():
    folder, name = dest_parts("Décembre 2025", today=date(2026, 1, 3))
    assert folder == "2025/Bulletins de paye"
    assert name == "Bulletin - 12_25.pdf"


def test_ancien_format_date_complete():
    assert parse_period("BULLETIN DE SALAIRE DE 31/01/2022") == (2022, 1)
    assert parse_period("BULLETIN DE SALAIRE DE 31/12/2021") == (2021, 12)


def test_format_nom_acme():
    assert dest_parts("Bulletin de paie Septembre 2026", prefix="ACME")[1] == "ACME - 09_26.pdf"


def test_employeur_depuis_la_ligne(monkeypatch):
    monkeypatch.setenv("PAYSLIP_EMPLOYERS", "GROUPE ACME=ACME;PAYROLL CO=Globex")
    acme = "Bulletin de paie Octobre 2026 Document daté du 2 novembre 2026. Créé le 2 novembre 2026, par GROUPE ACME. Taille du document : 15 KB"
    payroll = "BULLETIN DE SALAIRE DE 31/08/2022\nDocument daté du 31 août 2022. Créé le 5 septembre 2022, par PAYROLL CO. Taille du document : 77 KB"
    assert employer_from(acme) == "ACME"
    assert employer_from(payroll) == "Globex"
    assert employer_from("Bulletin sans employeur") == "Bulletin"
    assert employer_from("x, par ACME SAS. Taille") == "ACME SAS"
    assert dest_parts("BULLETIN DE SALAIRE DE 31/01/2022", prefix=employer_from(payroll))[1] == "Globex - 01_22.pdf"
