# infra/backup/ — sauvegarde & restauration PostgreSQL (INF-16)

Scripts de sauvegarde/restauration pour la base `db` (PostgreSQL/PostGIS) des
environnements **local** et **staging** — voir la note de conformité
ci-dessous pour l'environnement HDS.

## Prérequis

- La stack `docker compose` est démarrée (`docker compose up -d`), le
  service `db` est `healthy`.
- Bash (Git Bash sous Windows, natif sous Linux/macOS).

## Sauvegarde (`backup.sh`)

```bash
# Depuis la racine du repo, ou depuis infra/backup/ :
bash infra/backup/backup.sh

# Conserver 14 dumps au lieu de 7 (rotation) :
BACKUP_KEEP=14 bash infra/backup/backup.sh
```

- Format : `pg_dump -Fc` (format « custom » compressé, restaurable avec
  `pg_restore`), exécuté **dans** le conteneur `db` via
  `docker compose exec` (pas de client `pg_dump` requis sur l'hôte).
- Fichier produit : `infra/backup/dumps/infirmo-<db>-<horodatage-UTC>.dump`.
- **Rotation** : seuls les `BACKUP_KEEP` dumps les plus récents sont
  conservés (défaut **7**, override via la variable d'environnement
  `BACKUP_KEEP`).
- `infra/backup/dumps/` est **gitignored** (voir `.gitignore` local) : ces
  fichiers ne doivent jamais être committés.

## Restauration (`restore.sh`)

```bash
# Avec confirmation interactive :
bash infra/backup/restore.sh infra/backup/dumps/infirmo-infirmo-20260702T140000Z.dump

# Sans confirmation (scripts/CI) :
bash infra/backup/restore.sh -y infra/backup/dumps/infirmo-infirmo-20260702T140000Z.dump
```

- Utilise `pg_restore --clean --if-exists` : supprime les objets existants
  de la base cible avant de recréer ceux du dump (`--if-exists` évite une
  erreur si un objet du dump est absent de la base cible).
- **Opération destructive** : sauf `-y`, une confirmation explicite
  (`oui`) est demandée avant d'écraser la base.

## Select the target environment

Defaults are the root `docker-compose.yml` and `.env`. The scripts read the
database identity from the selected running container. For staging, set all paths
explicitly (Bash):

```sh
COMPOSE_FILE="$HOME/infirmo/docker-compose.staging.yml" ENV_FILE="$HOME/infirmo/.env" IMAGES_ENV_FILE="$HOME/infirmo/.images.env" bash infra/backup/backup.sh
COMPOSE_FILE="$HOME/infirmo/docker-compose.staging.yml" ENV_FILE="$HOME/infirmo/.env" IMAGES_ENV_FILE="$HOME/infirmo/.images.env" bash infra/backup/restore.sh path/to/backup.dump
```

Restore requires confirmation unless `-y`, and fails on its first error within a
single transaction. Failed backups remain `.partial` and do not enter rotation.
Rotation includes only completed dumps for the selected database. The historical
verification below does not validate these changes; repeat the restore test.

## Sauvegardes de vraies données de santé — activité HDS n°6

**Ces scripts ne doivent JAMAIS être utilisés pour sauvegarder de vraies
données de santé.** La sauvegarde de données de santé à caractère personnel
est l'**activité 6** de la certification HDS (Art. R1111-9 CSP — voir
[`../hds/README.md`](../hds/README.md) §2). Sur l'environnement HDS cible,
c'est le **dispositif de sauvegarde certifié de l'hébergeur** (activité 6)
qui s'applique, avec chiffrement au repos et résidence EEE garantis par le
certificat — pas ce script `bash` local.

`backup.sh` / `restore.sh` sont prévus pour :

- l'environnement **local** (`docker-compose.yml`, données synthétiques) ;
- l'environnement **staging** (`infra/deploy/`, données synthétiques
  uniquement — voir AGENTS.md et `infra/hds/README.md` §1).

## Test de restauration (vérification effectuée — INF-16)

Procédure exécutée pour valider la chaîne complète sauvegarde → restauration
sur l'environnement local, avec des données **synthétiques** :

1. Création d'une table de test avec quelques lignes synthétiques dans `db`
   (`docker compose exec db psql ... -c "CREATE TABLE ..."`).
2. `bash infra/backup/backup.sh` → un fichier `.dump` non trivial est
   généré dans `infra/backup/dumps/`.
3. Suppression de la table de test (`DROP TABLE ...`), pour simuler une
   perte de données.
4. `bash infra/backup/restore.sh -y <dump>` → la table et ses lignes sont
   restaurées.
5. Vérification du contenu restauré (`SELECT * FROM ...` renvoie les mêmes
   lignes synthétiques qu'à l'étape 1).
6. Suppression de la table de test pour laisser la base propre.

Résultat : sauvegarde et restauration fonctionnelles de bout en bout sur
l'environnement local. À rejouer périodiquement (et à chaque changement du
schéma applicatif) pour garder cette garantie à jour.
