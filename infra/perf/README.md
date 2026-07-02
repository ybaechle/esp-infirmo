# infra/perf/ — tests de performance k6 (INF-17)

Test de fumée (« smoke test ») de charge légère sur les endpoints de santé
du backend, pour détecter une régression de latence/disponibilité avant
qu'elle n'atteigne staging/production.

## Portée & garde-fou de conformité

**Ne cibler que des environnements à données SYNTHÉTIQUES** (local,
staging — voir AGENTS.md §5 et `infra/hds/README.md`). Ne jamais lancer de
test de charge contre un environnement contenant de vraies données de santé
sans autorisation explicite : même un test « léger » génère du trafic
soutenu qui peut dégrader un service en production, et le principe de
précaution s'applique tant qu'aucune procédure d'autorisation formelle n'a
été définie pour un futur environnement HDS.

## Lancer le test

Le script cible `db`/`redis`/`backend` déjà démarrés (`docker compose up
-d`, voir `../README.md`). Il se lance via l'image officielle `grafana/k6`,
sans installation locale.

```bash
# Vérifier le nom du réseau Docker Compose du projet (généralement
# "infirmo_default" — le préfixe suit le nom du dossier/projet compose) :
docker network ls

# Lancer le smoke test contre le backend via le réseau Docker (nom de
# service DNS "backend", port interne 8000 — pas le port publié sur l'hôte) :
docker run --rm --network infirmo_default \
  -e BASE_URL=http://backend:8000 \
  -v "$(pwd)/infra/perf:/scripts:ro" \
  grafana/k6:1.5.0 run /scripts/smoke.js
```

> Sous Git Bash (Windows), le chemin `/scripts/smoke.js` peut être réécrit
> en chemin Windows par MSYS avant d'atteindre le conteneur : si `k6`
> renvoie une erreur "couldn't be found on local disk", préfixer la commande
> avec `MSYS_NO_PATHCONV=1`.

Alternative sans montage de volume (stdin) :

```bash
docker run --rm --network infirmo_default \
  -e BASE_URL=http://backend:8000 \
  grafana/k6:1.5.0 run - < infra/perf/smoke.js
```

Depuis l'hôte (sans Docker, si `k6` est installé localement) :

```bash
BASE_URL=http://localhost:${BACKEND_PORT:-8000} k6 run infra/perf/smoke.js
```

## Paramètres du scénario

| Paramètre | Valeur | Sens |
| --------- | ------ | ---- |
| VUs (utilisateurs virtuels) | 5 | Charge légère, volontairement modeste (budget DevOps 21 JH, projet étudiant) |
| Durée | 30s | Suffisant pour un smoke test, pas une étude de capacité |
| `BASE_URL` | `__ENV.BASE_URL` | URL de base de l'API, ex. `http://backend:8000` (réseau Docker) |

## Seuils (thresholds)

| Seuil | Signification |
| ----- | -------------- |
| `http_req_duration: p(95)<500ms` | 95% des requêtes doivent répondre en moins de 500ms — au-delà, le run k6 échoue (utile en CI comme garde-fou de régression). |
| `http_req_failed: rate<0.01` | Moins de 1% des requêtes en échec (statut ≥400 ou erreur réseau/timeout) — détecte une instabilité, pas seulement une lenteur. |

Un run qui dépasse un seuil se termine avec un code de sortie non nul :
utilisable tel quel comme step CI bloquant.

## Quand passer à des scénarios plus lourds

Ce smoke test couvre uniquement la disponibilité/latence de base des
health checks. Il ne remplace pas une vraie étude de charge. À envisager
plus tard (hors périmètre INF-17, note pour un ticket futur) :

- scénarios ciblant les endpoints métier réels une fois qu'ils existent
  (recherche de remplacement, candidatures, messagerie), avec des profils
  de charge réalistes (ramp-up/ramp-down, pics) ;
- tests de montée en charge (« stress test ») pour identifier le point de
  rupture, à réserver à staging (données synthétiques), jamais à un
  environnement contenant de vraies données de santé sans autorisation ;
- intégration des résultats k6 dans Prometheus/Grafana (`infra/monitoring/`,
  INF-15) via le output `k6 run --out experimental-prometheus-rw` pour
  visualiser les tendances de latence dans le temps.
