// infra/perf/api.js — scénario k6 des routes métier de l'API v1 (YB-8).
//
// Mesure le KPI du cahier des charges (§10.5) : p95 < 500 ms sur les lectures courantes
// d'un remplaçant (recherche classée, alertes, profil, missions) et d'un cabinet.
// Les connexions sont mesurées à part : le hachage scrypt est lent par conception.
//
// COMPLIANCE (AGENTS.md) : cibler uniquement un environnement à données SYNTHÉTIQUES.
// Le script crée ses propres comptes fictifs (domaine réservé .example) et ne lit rien d'existant.

import http from "k6/http";
import { check, sleep } from "k6";

const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";
const API = `${BASE_URL}/api/v1`;
const JSON_HEADERS = { "Content-Type": "application/json" };
const NANCY = { lat: 48.6921, lon: 6.1844 };

export const options = {
  scenarios: {
    reads: {
      executor: "constant-vus",
      vus: Number(__ENV.VUS || 5),
      duration: __ENV.DURATION || "30s",
    },
  },
  thresholds: {
    "http_req_duration{kind:read}": ["p(95)<500"],
    "http_req_failed{kind:read}": ["rate<0.01"],
    checks: ["rate>0.99"],
  },
};

function luhnDigit(prefix) {
  let total = 0;
  [...prefix].reverse().forEach((char, index) => {
    let digit = Number(char);
    if (index % 2 === 0) {
      digit *= 2;
      if (digit > 9) digit -= 9;
    }
    total += digit;
  });
  return String((10 - (total % 10)) % 10);
}

function rpps() {
  const prefix = String(Math.floor(Math.random() * 1e10)).padStart(10, "0");
  return prefix + luhnDigit(prefix);
}

function siret() {
  const prefix = String(Math.floor(Math.random() * 1e13)).padStart(13, "0");
  return prefix + luhnDigit(prefix);
}

function post(path, body, token, tags = {}) {
  const headers = token ? { ...JSON_HEADERS, Authorization: `Bearer ${token}` } : JSON_HEADERS;
  return http.post(`${API}${path}`, JSON.stringify(body), { headers, tags });
}

function signUp(role) {
  const tag = `${Date.now()}${Math.floor(Math.random() * 1e6)}`;
  const email = `perf-${tag}@perf.example`;
  const password = "Perf-synthetique-2026!";
  const created = post("/auth/register", {
    email,
    password,
    first_name: "Perf",
    last_name: role,
    role,
    order_number: rpps(),
    accept_terms: true,
  });
  check(created, { "inscription 201": (r) => r.status === 201 });
  const login = post("/auth/login", { email, password }, null, { kind: "login" });
  check(login, { "connexion 200": (r) => r.status === 200 });
  return login.json("access_token");
}

export function setup() {
  const holder = signUp("titulaire");
  const substitute = signUp("remplacant");
  const office = post(
    "/offices",
    {
      name: "Cabinet de charge",
      siret: siret(),
      address: "1 rue de la Charge",
      postcode: "54000",
      city: "Nancy",
      latitude: NANCY.lat,
      longitude: NANCY.lon,
    },
    holder,
  ).json();
  const start = Date.now() + 10 * 86400 * 1000;
  for (let i = 0; i < 20; i++) {
    post(
      `/offices/${office.id}/offers`,
      {
        description: `Tournée synthétique ${i}`,
        start_at: new Date(start + i * 86400000).toISOString(),
        end_at: new Date(start + (i + 3) * 86400000).toISOString(),
        valid_till: new Date(start + i * 86400000 - 86400000).toISOString(),
        turnover: 300 + i * 40,
        care_codes: [],
      },
      holder,
    );
  }
  http.put(
    `${API}/profile`,
    JSON.stringify({
      first_name: "Perf",
      last_name: "remplacant",
      city: "Nancy",
      latitude: NANCY.lat,
      longitude: NANCY.lon,
      radius_km: 50,
      care_codes: [],
    }),
    { headers: { ...JSON_HEADERS, Authorization: `Bearer ${substitute}` } },
  );
  return { holder, substitute, officeId: office.id };
}

function read(path, token) {
  const response = http.get(`${API}${path}`, {
    headers: { Authorization: `Bearer ${token}` },
    tags: { kind: "read" },
  });
  check(response, { [`GET ${path.split("?")[0]} 200`]: (r) => r.status === 200 });
}

export default function (data) {
  read("/offers/search?limit=20", data.substitute);
  read("/offers/search?radius_km=20&sort=distance", data.substitute);
  read("/notifications?limit=20", data.substitute);
  read("/profile", data.substitute);
  read("/me/missions", data.substitute);
  read(`/offices/${data.officeId}/offers?limit=20`, data.holder);
  sleep(0.5);
}
