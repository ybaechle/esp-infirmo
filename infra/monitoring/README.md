# infra/monitoring/ — Prometheus + Grafana (INF-15)

Profil Docker Compose optionnel `monitoring`, désactivé par défaut, qui
ajoute Prometheus (collecte de métriques) et Grafana (visualisation) à
l'environnement de développement local décrit dans
[`../README.md`](../README.md#démarrage-local-docker-compose).

## Démarrer

```bash
# GRAFANA_ADMIN_PASSWORD est requis (pas de défaut) : renseigner une valeur
# dans .env (voir .env.example à la racine), locale uniquement.

# Démarrer db/redis/backend/ia + prometheus/grafana.
docker compose --profile monitoring up -d --build

# Arrêter (inclut le profil monitoring).
docker compose --profile monitoring down
```

## URLs

| Service | URL (hôte) | Identifiants |
| ------- | ---------- | ------------- |
| Backend `/metrics` | `http://localhost:${BACKEND_PORT:-8000}/metrics` | — |
| Prometheus | `http://localhost:${PROMETHEUS_PORT:-9090}` | — |
| Grafana | `http://localhost:${GRAFANA_PORT:-3001}` | `admin` / `$GRAFANA_ADMIN_PASSWORD` |

Ports par défaut choisis pour ne pas entrer en conflit avec d'autres projets
Docker sur la même machine (ex. 3000/9000/9001 déjà pris ailleurs) ; à
ajuster via `.env` (`PROMETHEUS_PORT`, `GRAFANA_PORT`) si besoin.

## Ce qui est scrapé

Prometheus scrape uniquement `backend:8000/metrics` toutes les 15s (voir
[`prometheus.yml`](prometheus.yml)). `ia` et `db`/`redis` n'exposent pas
(encore) de `/metrics` et ne sont pas scrapés.

Grafana est provisionné automatiquement (pas de config manuelle dans l'UI) :

- une datasource Prometheus ([`grafana/provisioning/datasources/`](grafana/provisioning/datasources/)) ;
- un dashboard minimal « Infirmo backend — vue d'ensemble »
  ([`grafana/provisioning/dashboards/infirmo-backend.json`](grafana/provisioning/dashboards/infirmo-backend.json))
  avec deux panneaux : débit de requêtes (`rate(http_requests_total[5m])`
  par route/statut) et latence p95
  (`histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))`
  par route).
- accès anonyme désactivé (`GF_AUTH_ANONYMOUS_ENABLED=false`), authentification
  admin obligatoire.

## Règle PHI dans les métriques (AGENTS.md)

**Aucune donnée de santé ni secret ne doit jamais apparaître dans une
métrique, un label ou un dashboard.** Le backend expose `/metrics` via
`prometheus-fastapi-instrumentator`, configuré avec ses métriques par défaut
uniquement (`Instrumentator().instrument(app).expose(app)` dans
`backend/app/main.py`) :

- `http_requests_total{handler,method,status}` — compteur par route/verbe/code ;
- `http_request_duration_seconds{handler,method}` — histogramme de latence ;
- tailles de requêtes/réponses en octets.

Ce sont des métadonnées d'infrastructure (route, verbe HTTP, code de statut,
durée, taille) — **jamais le corps** d'une requête/réponse, ni un identifiant
patient/infirmier, ni un token. Si une métrique métier personnalisée est
ajoutée plus tard, elle doit suivre la même règle : labels/valeurs limités à
des identifiants techniques ou pseudonymisés, jamais de contenu de
transmission ni de PHI (voir aussi `secure-coding-sante`).

## Portée

Comme le reste de `docker-compose.yml`, ce profil est pour le **dev local
avec données synthétiques uniquement** — pas l'environnement HDS (voir
`infra/hds/README.md` et AGENTS.md). L'équivalent en staging/production
n'est pas encore mis en place (hors périmètre INF-15).
