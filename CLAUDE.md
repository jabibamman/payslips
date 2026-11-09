# Payslips Fetcher

Telecharge les bulletins de paie depuis MyPeopleDoc (Playwright), gere le 2FA par
code email Gmail (IMAP), puis les copie sur Google Drive via rclone.

## Commandes
- Installation : `./setup.sh` (venv, deps, Chromium, `.env`, tests)
- Execution : `./run.sh` (fetch.py puis rclone)
- Tests : `.venv/bin/python -m pytest`
- Debug navigateur : `HEADLESS=0` ; captures dans `debug/`
- Reset session : supprimer `state.json`

## Architecture
- `fetch.py` : login (+ OTP), parcourt les lignes de documents, telecharge les PDF.
- `payslip_meta.py` : deduit annee/mois depuis le libelle du document, calcule
  le sous-dossier et le nom de fichier.
- `mailcode.py` : lecture IMAP et extraction du code a 6 chiffres.
- `run.sh` : charge `.env`, lance fetch.py, puis `rclone copy --ignore-existing`.
- `deploy/` : unites systemd (timer du 1er au 8 du mois, 08h30 et 14h30).

## Rangement (regle importante)
Drive : `<RCLONE_DEST> > <ANNEE> > Bulletins de paye`.
- L'ANNEE vient du **bulletin** (ex. "Decembre 2025"), jamais de la date du jour :
  un bulletin de decembre recupere en janvier va dans l'annee precedente.
- Le dossier `<ANNEE>` est cree automatiquement (localement et par rclone).
- Arborescence locale `out/<ANNEE>/Bulletins de paye/ACME - <MM>_<AA>.pdf (ex. `ACME - 09_26.pdf`, l'employeur est lu dans la ligne MPD ("par PAYROLL CO.") via `PAYSLIP_EMPLOYERS="GROUPE ACME=ACME;PAYROLL CO=Globex"` (dans `.env`, pas dans le code : projet destine a l'open source), defaut `PAYSLIP_PREFIX`)`,
  copiee telle quelle sous `RCLONE_DEST` (= `gdrive:Documents/Payslips`).
- Si le libelle n'a pas de mois : nom issu du libelle ; sans annee : annee courante.
- Un fichier deja present localement est ignore (pas de re-telechargement).
- Avec `MAX_DOCS=0`, tout l'historique est trie dans les bons dossiers annuels.

## Site MyPeopleDoc (verifie le 2026-11-09)
- Login : `#username` + `#password` sur la meme page (bouton actif une fois les deux remplis).
- 2FA email : `[data-test-input-2fa-code]`, case "ne plus demander pendant 60 jours" cochee
  par le script ; la session est gardee dans `state.json`.
- Lignes : `[data-test-document-list-item]` (attribut = id). Telechargement direct via
  `/api/documents/<id>/download` avec la session. Le filtre `DOC_FILTER` (defaut
  `bulletin`) evite de ranger contrats/factures. Le parsing n'utilise que le titre
  (les anciens sont "BULLETIN DE SALAIRE DE 31/01/2022").
- Test sans toucher au Drive : `OUT_DIR=./out-test MAX_DOCS=0 .venv/bin/python fetch.py`.

## Variables .env
`MPD_EMAIL`, `MPD_PASSWORD`, `GMAIL_USER`, `GMAIL_APP_PASSWORD`, `RCLONE_DEST`,
`MAX_DOCS`, `HEADLESS`, `NOTIFY_URL`. Optionnelles : `PAYSLIP_SUBDIR` (defaut
`Bulletins de paye`), `OUT_DIR`, `DEBUG_DIR`, `STATE_FILE`, `MPD_URL`,
`MPD_MAIL_SENDER`, `SEL_*` (selecteurs CSS).

## Deploiement
LXC Debian dans `/opt/payslips`, `rclone.conf` local au projet (`RCLONE_CONFIG`), voir README. Alerte d'echec : `deploy/payslips-fail@.service` -> `NOTIFY_URL`. `fetch.py` echoue (donc alerte) si 0 bulletin trouve.

## Conventions
- Ne jamais committer `.env`, `state.json`, `out/`, `debug/` (secrets / donnees perso).
- Les selecteurs `SEL_*` sont des suppositions : a verifier avec `HEADLESS=0` si le
  site change.
- rclone doit avoir un remote nomme `gdrive` (`rclone config`) ; "Mon Drive" = racine.
- Ajouter un test dans `tests/` pour toute nouvelle logique de parsing.
