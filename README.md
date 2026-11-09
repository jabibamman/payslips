# 📄 Payslips Fetcher (MyPeopleDoc → Google Drive)

Télécharge automatiquement vos bulletins de paie depuis **MyPeopleDoc**, gère le 2FA par code email (Gmail/IMAP) et les range sur Google Drive (ou tout stockage supporté par **rclone**) dans une arborescence par année :

```text
<RCLONE_DEST>/
└── 2026/
    └── Bulletins de paye/
        ├── ACME - 09_26.pdf
        └── ACME - 10_26.pdf
```

> [!WARNING]
> **Outil non officiel, fourni « tel quel », sans garantie.** Ce projet n'est ni affilié, ni approuvé par PeopleDoc ou Google.
> - Utilisez-le **uniquement avec votre propre compte** et vos propres documents. Vérifiez que cela respecte les conditions d'utilisation de MyPeopleDoc et de votre employeur.
> - Il automatise un site web (et non une API publique documentée) : il peut cesser de fonctionner à tout moment si le site change (voir [Dépannage](#-dépannage)).
> - Vos identifiants, la session (`state.json`) et le jeton rclone donnent accès à vos comptes : ne les partagez ni ne les publiez jamais (voir [Sécurité](#-sécurité)).
> - Les auteurs ne sont pas responsables des pertes de données, blocages de compte ou autres conséquences de son usage.

## 📋 Sommaire

- [Fonctionnalités](#-fonctionnalités)
- [Prérequis](#-prérequis)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Configurer rclone / Google Drive](#-configurer-rclone--google-drive)
- [Utilisation](#-utilisation)
- [Déploiement (systemd / LXC)](#-déploiement-systemd--lxc)
- [Structure du projet](#-structure-du-projet)
- [Dépannage](#-dépannage)
- [Sécurité](#-sécurité)
- [Contribuer](#-contribuer)
- [Licence](#-licence)

## ✨ Fonctionnalités

- 🤖 Navigation automatisée avec Playwright (Chromium).
- 🔑 **2FA automatique** : lit le code à 6 chiffres reçu par email via IMAP Gmail, et coche « ne plus demander pendant 60 jours ».
- 💾 **Session persistante** (`state.json`) : pas de nouveau code à chaque exécution.
- 🗂️ **Rangement intelligent** : l'année et le mois sont déduits du **bulletin lui-même** (pas de la date du jour). Un bulletin de décembre récupéré en janvier va dans l'année précédente. Les dossiers d'année sont créés automatiquement.
- 🏷️ **Nom de fichier** `<Employeur> - MM_AA.pdf`, avec l'employeur lu sur le site et traduit via une table configurable (utile si vous changez d'entreprise).
- 🔎 Ne télécharge que les documents dont le titre contient « bulletin » (pas vos contrats ou factures).
- ♻️ **Idempotent** : un fichier déjà présent n'est ni retéléchargé ni écrasé (`rclone --ignore-existing`).
- 🚨 **Alerte en cas d'échec** (webhook `NOTIFY_URL`, ex. [ntfy](https://ntfy.sh)), y compris si le site ne renvoie plus aucun bulletin.
- ⏰ Timer systemd : du 1er au 8 du mois, à 08h30 et 14h30 (les bulletins arrivent en général entre le 1er et le 7).

## ⚙️ Prérequis

- Python 3.8+ et `python3-venv`
- Un compte MyPeopleDoc dont le 2FA se fait **par email**, sur une adresse Gmail
- [rclone](https://rclone.org/) configuré (optionnel : sans lui, les PDF restent dans `./out`)

## 🚀 Installation

```bash
git clone <ce-depot> payslips && cd payslips
./setup.sh
```

`setup.sh` crée le venv, installe les dépendances et Chromium (avec `--with-deps` si lancé en root sous Linux), crée `.env` (`chmod 600`) et lance les tests.

## 🔧 Configuration

Éditez `.env` (**mettez entre guillemets toute valeur contenant des espaces**, le fichier est lu par `source` et par systemd) :

| Variable | Description | Exemple |
| :--- | :--- | :--- |
| `MPD_EMAIL` / `MPD_PASSWORD` | Identifiants MyPeopleDoc | |
| `GMAIL_USER` | Adresse Gmail recevant le code | `moi@gmail.com` |
| `GMAIL_APP_PASSWORD` | [Mot de passe d'application](#mot-de-passe-dapplication-gmail) (espaces acceptés) | `"abcd efgh ijkl mnop"` |
| `RCLONE_DEST` | Racine rclone ; les fichiers vont dans `<RCLONE_DEST>/<année>/<PAYSLIP_SUBDIR>/` | `"gdrive:Documents/Payslips"` |
| `PAYSLIP_SUBDIR` | Sous-dossier dans chaque année | `"Bulletins de paye"` |
| `PAYSLIP_EMPLOYERS` | Table `nom affiché=nom voulu`, séparée par `;` | `"GROUPE ACME=ACME;PAYROLL CO=Globex"` |
| `PAYSLIP_PREFIX` | Employeur par défaut si inconnu | `"ACME"` |
| `MAX_DOCS` | `1` = dernier bulletin seulement (usage normal), `0` = tout l'historique | `1` |
| `HEADLESS` | `0` pour voir le navigateur | `1` |
| `NOTIFY_URL` | Webhook appelé en cas d'échec (POST) | `https://ntfy.sh/mon-topic` |

Avancées : `OUT_DIR`, `DEBUG_DIR`, `STATE_FILE`, `MPD_URL`, `MPD_MAIL_SENDER`, `DOC_FILTER` (défaut `bulletin`), `SEL_*` (sélecteurs CSS).

> **Nom d'employeur** : MyPeopleDoc affiche le nom de l'émetteur (« par PAYROLL CO. ») qui n'est pas toujours celui de l'entreprise. Ajoutez-le à `PAYSLIP_EMPLOYERS`. S'il est inconnu, le nom brut est utilisé (sans « Groupe »).

### Mot de passe d'application Gmail

1. Activez la validation en deux étapes sur https://myaccount.google.com/security.
2. Créez un mot de passe d'application (nom : `Payslips`), copiez les 16 caractères.
3. Vérifiez que **IMAP** est activé (Gmail → Paramètres → Transfert et POP/IMAP).

## ☁️ Configurer rclone / Google Drive

> ⚠️ Le `client_id` partagé de rclone est retiré par Google (erreur `401 invalid_client`). Créez le vôtre :

1. [Console Google Cloud](https://console.cloud.google.com/projectcreate) : créez un projet.
2. Activez la **Google Drive API**.
3. *Google Auth Platform* → **Branding** : nom, e-mail d'assistance, page d'accueil et règles de confidentialité (une URL quelconque vous appartenant suffit).
4. *Audience* → **Publier l'application** (statut « En production »). En mode « Test », le jeton expire au bout de 7 jours.
5. *Clients* → **Créer un client** → type *Application de bureau* → notez l'ID client et le secret.
6. `rclone config` → nouveau remote `gdrive`, type `drive`, collez `client_id`/`client_secret`, scope `drive`, « auto config » = oui (acceptez l'avertissement « application non validée » : c'est la vôtre).

Vérification : `rclone lsd gdrive:`

## 💻 Utilisation

```bash
./run.sh                                   # fetch + copie rclone
.venv/bin/python fetch.py                  # téléchargement seul (dans ./out)
.venv/bin/python -m pytest                 # tests
.venv/bin/python check_mail.py             # teste uniquement la lecture du code Gmail
```

**Tester sans rien envoyer sur le Drive** (tout l'historique, dans un dossier jetable) :

```bash
set -a; source .env; set +a
OUT_DIR=./out-test MAX_DOCS=0 .venv/bin/python fetch.py
rclone copy out-test "$RCLONE_DEST" --ignore-existing --dry-run -v   # simulation
```

## 🖥️ Déploiement (systemd / LXC)

Testé sur Debian/Ubuntu (conteneur LXC inclus). Exécution en root pour simplifier ; adaptez `User=` si vous préférez un compte dédié.

```bash
apt install -y python3 python3-venv rclone curl
git clone <ce-depot> /opt/payslips && cd /opt/payslips
./setup.sh                      # en root : installe aussi les libs système de Chromium
nano .env                       # remplir (chmod 600 déjà appliqué)
```

**rclone** : faites `rclone config` sur une machine avec navigateur, puis copiez le fichier :

```bash
scp ~/.config/rclone/rclone.conf root@lxc:/opt/payslips/rclone.conf
chmod 600 /opt/payslips/rclone.conf     # le service utilise RCLONE_CONFIG=/opt/payslips/rclone.conf
```

**Première connexion** : pour éviter un 2FA froid sur le serveur, lancez une fois `./run.sh` à la main (le code est lu par IMAP, aucune interaction requise). Vous pouvez aussi copier un `state.json` valide.

**Activer le timer** :

```bash
cp deploy/payslips.service deploy/payslips.timer deploy/payslips-fail@.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now payslips.timer
systemctl list-timers payslips.timer
systemctl start payslips.service && journalctl -u payslips -n 30   # test immédiat
```

Le timer se déclenche à 08h30 et 14h30 du 1er au 8 de chaque mois (adaptez `OnCalendar` à la date de publication de votre employeur). Une fois le bulletin du mois récupéré, les exécutions suivantes ne font rien. En cas d'échec, `payslips-fail@.service` journalise et appelle `NOTIFY_URL`.

**Alertes** : avec ntfy, `NOTIFY_URL=https://ntfy.sh/<topic-secret>` suffit (corps texte). Pour Discord/Slack, il faudra un petit relais car ils attendent du JSON.

## 📁 Structure du projet

```text
├── fetch.py          # login, 2FA, liste des bulletins, téléchargement (API du site)
├── payslip_meta.py   # année/mois, employeur, dossier et nom de fichier
├── mailcode.py       # lecture IMAP du code 2FA
├── check_mail.py     # test de la lecture du code
├── run.sh            # fetch.py puis rclone copy --ignore-existing
├── setup.sh          # installation
├── deploy/           # unités systemd (service, timer, alerte d'échec)
├── tests/            # tests unitaires (parsing de dates, employeur, code OTP)
└── CLAUDE.md         # notes pour les assistants de code
```

## 🔍 Dépannage

- **Voir ce qui se passe** : `HEADLESS=0`. Des captures sont écrites dans `./debug/` (`after-password.png`, `after-login.png`, `documents.png`).
- **`aucun bulletin trouve`** : session expirée ou site modifié. Supprimez `state.json`, relancez, puis comparez avec `debug/documents.png` et ajustez `SEL_*`.
- **`invalid_client` dans rclone** : voir [Configurer rclone](#-configurer-rclone--google-drive).
- **Erreur IMAP** : vérifiez le mot de passe d'application (pas votre mot de passe Google) et que IMAP est activé.
- **`source .env` échoue** : une valeur avec espaces n'est pas entre guillemets.
- **Doublons sur le Drive** : le nom de fichier ou le dossier d'année diffère de l'existant. Testez avec `--dry-run` avant toute copie en masse.

## 🔒 Sécurité

- `.env`, `state.json`, `rclone.conf`, `out/`, `debug/` et les `*.pdf` sont ignorés par git. **Ne les publiez jamais** (les captures de `debug/` montrent votre nom).
- `state.json` et `rclone.conf` donnent accès à vos comptes : gardez-les en `chmod 600`.
- Cochez « ne plus demander de code » revient à marquer le serveur comme appareil de confiance pendant 60 jours.

## 🤝 Contribuer

Les contributions sont les bienvenues : correctifs, support d'autres portails de paie, meilleure doc, traductions, tests.

**Forker le projet** (pour l'adapter à votre situation ou travailler dessus) :

1. Cliquez sur **Fork** sur GitHub, puis clonez *votre* fork : `git clone <url-de-votre-fork>`.
2. Installez et testez : `./setup.sh` puis `.venv/bin/python -m pytest`.
3. Configurez votre propre `.env` (jamais commité, voir [Sécurité](#-sécurité)).

**Proposer une modification (pull request)** :

1. Créez une branche depuis `main` : `git checkout -b ma-modification`.
2. Faites des changements ciblés, avec un **test** dans `tests/` pour toute logique de parsing (dates, employeurs, codes OTP…).
3. Vérifiez que `.venv/bin/python -m pytest` passe.
4. Poussez la branche sur votre fork et ouvrez une **pull request** vers ce dépôt, en décrivant le problème résolu et comment vous l'avez testé.

**Signaler un bug (issue)** : indiquez la version de Python, l'OS, la commande lancée et le message d'erreur.

> ⚠️ **Ne publiez jamais de données personnelles**, ni dans une issue ni dans une pull request : pas de `.env`, `state.json`, `rclone.conf`, de PDF, de captures de `debug/` (elles montrent votre nom), ni de logs contenant des identifiants, noms d'employeurs ou chemins perso. Anonymisez les exemples (ex. `ACME`, `Globex`).

**Quelques conventions** :
- Le code reste générique : tout ce qui est propre à un utilisateur (employeur, dossier Drive, topic de notification) passe par des variables du `.env`, jamais en dur.
- Les sélecteurs CSS du site sont dans `fetch.py` et surchargeables via `SEL_*`. Si le site change, une pull request qui les met à jour est très utile.
- Une pull request par sujet, des messages de commit clairs.

## 📜 Licence

[MIT](LICENSE)
