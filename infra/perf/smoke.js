// infra/perf/smoke.js — test de fumée k6 (INF-17).
//
// Vérifie que /health et /health/ready répondent dans des délais corrects
// sous une charge légère. Ce n'est PAS un test de charge/capacité : voir
// infra/perf/README.md pour la trajectoire vers des scénarios plus lourds.
//
// COMPLIANCE (AGENTS.md §5) : ne cibler QUE des environnements à données
// SYNTHÉTIQUES (local, staging). Ne jamais lancer de test de charge contre
// un environnement contenant de vraies données de santé sans autorisation
// explicite — un afflux de requêtes peut dégrader un service en production
// et /health(/ready) ne renvoie aucune donnée de santé, mais la cible doit
// rester non-HDS / synthétique par principe de précaution.

import http from "k6/http";
import { check, sleep } from "k6";

// URL de base de l'API à tester, ex. http://backend:8000 (réseau Docker
// Compose) ou http://localhost:8010 (hôte, avec BACKEND_PORT du .env local).
const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";

export const options = {
  vus: 5,
  duration: "30s",
  thresholds: {
    // 95% des requêtes doivent répondre en moins de 500ms.
    http_req_duration: ["p(95)<500"],
    // Moins de 1% des requêtes en échec (statut hors 2xx/3xx ou erreur réseau).
    http_req_failed: ["rate<0.01"],
  },
};

export default function () {
  const healthRes = http.get(`${BASE_URL}/health`);
  check(healthRes, {
    "/health renvoie 200": (r) => r.status === 200,
  });

  const readyRes = http.get(`${BASE_URL}/health/ready`);
  check(readyRes, {
    // 200 attendu : postgres et redis doivent être joignables dans un
    // environnement sain (sinon http_req_failed le remonte via le seuil).
    "/health/ready renvoie 200": (r) => r.status === 200,
  });

  sleep(1);
}
