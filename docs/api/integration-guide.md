# Guide d'intégration de l'API Infirmo (v1)

Public : l'équipe mobile et toute personne qui consomme le backend. Le contrat machine est [`openapi.json`](openapi.json), régénéré par `uv run python -m app.export_openapi` depuis `backend/` et vérifié par un test à chaque exécution de la CI. Ce guide explique ce que le contrat ne dit pas : les flux, les règles et les pièges.

Toutes les routes ci-dessous sont préfixées par `/api/v1`. La démonstration v0.1 (`/api/auth/login`, `/api/profile`, `/api/auth/logout`) reste disponible tant que `INFIRMO_DEMO_MODE=true`, sans lien avec cette API.

**Données synthétiques uniquement** : l'hébergement HDS n'est pas validé (voir `AGENTS.md`).

## 1. Authentification

```text
POST /auth/register   → 201 compte créé (actif)
POST /auth/login      → 200 { access_token, refresh_token, expires_in: 900, token_type: "bearer" }
POST /auth/refresh    → 200 nouvelle paire ; l'ancien refresh est consommé
POST /auth/logout     → 204 révoque toute la session (access + refresh)
GET  /auth/me         → profil minimal du compte connecté
```

- Envoyer `Authorization: Bearer <access_token>`. Il vit **15 minutes**, le refresh **7 jours**.
- Sur `401 authentication_required`, appeler `/auth/refresh` **une seule fois**, puis rejouer la requête. Sur `401 invalid_refresh_token` ou `refresh_token_reused`, renvoyer l'utilisateur à l'écran de connexion.
- **Rotation** : chaque refresh donne un nouveau refresh. Rejouer un refresh déjà utilisé révoque toute la session (signe de vol) : ne jamais réessayer un refresh en parallèle, sérialiser les appels.
- Conserver les jetons en mémoire ou dans le stockage sécurisé de l'appareil, jamais dans les journaux ni dans une URL.
- Inscription : `order_number` = numéro RPPS à 11 chiffres (somme de Luhn valide), mot de passe de 12 à 128 caractères, `accept_terms: true` obligatoire (consentement RGPD), `role` = `titulaire` ou `remplacant`. Le numéro est vérifié par un **mock** tant que l'API publique de l'Ordre n'est pas branchée (F1.3).

### 2FA optionnelle (e-mail / SMS)

1. `POST /auth/2fa/enable { channel: "email" | "sms", phone? }` → `202 { challenge_id }`. Un code à 6 chiffres est envoyé. `phone` au format E.164 (`+33612345678`) est exigé pour le SMS.
2. `POST /auth/2fa/confirm { challenge_id, code }` → `204`, la 2FA est active.
3. Ensuite `POST /auth/login` renvoie `{ two_factor_required: true, challenge_id }` **sans jetons** ; terminer par `POST /auth/2fa/verify { challenge_id, code }` qui renvoie les jetons.
4. `POST /auth/2fa/disable { password }` la désactive.

Un code vit 5 minutes, sert une fois et s'invalide après 5 essais. **Aucun fournisseur d'e-mail ou de SMS n'est branché** : tant qu'il ne l'est pas, `enable` et la connexion d'un compte déjà protégé répondent `503 otp_unavailable`. Ne pas proposer la 2FA dans l'interface avant l'ouverture du fournisseur.

## 2. Format des erreurs

Toute erreur est `{ "detail": "<texte indicatif>", "code": "<identifiant stable>" }`. **Se brancher sur `code`**, jamais sur `detail`. Les erreurs de validation (`422`) ne renvoient que `{ "detail": "Invalid request" }`, sans écho des valeurs.

| Statut | Codes courants |
| --- | --- |
| 401 | `authentication_required`, `invalid_credentials`, `invalid_refresh_token`, `refresh_token_reused`, `invalid_code` |
| 403 | `forbidden_role`, `account_inactive`, `admin_required`, `owner_required`, `not_connected` |
| 404 | `*_not_found` (une ressource d'un autre cabinet ou d'un autre utilisateur est aussi un 404, jamais un 403) |
| 409 | `account_exists`, `already_applied`, `already_decided`, `offer_closed`, `offer_not_editable`, `invalid_transition`, `too_early`, `cannot_resign`, `active_missions`, `siret_exists` |
| 413 | `file_too_large` |
| 422 | `order_number_invalid`, `unknown_care`, `not_a_pdf`, `not_an_image`, `not_audio`, `phone_required`, `coordinates_incomplete` |
| 429 | `too_many_attempts` (en-tête `Retry-After`) |
| 503 | `service_unavailable`, `encryption_unavailable`, `otp_unavailable`, `ordre_unavailable` |

Limites de débit : 5 connexions par minute et par adresse e-mail, 30 par adresse IP, 10 inscriptions par minute et par IP.

## 3. Pagination

Toute liste renvoie `{ items, total, limit, offset }`. Paramètres : `limit` de 1 à 100 (20 par défaut), `offset` ≥ 0. L'ordre est déterministe : paginer par `offset` est sûr.

## 4. Parcours métier

| Besoin | Appels |
| --- | --- |
| Compléter son profil (F1.5) | `GET /cares` puis `PUT /profile` (remplacement complet : prénom, nom, ville, `latitude`+`longitude`, `radius_km` 1–200, `min_turnover`, `bio`, `care_codes`) |
| Disponibilités (remplaçant) | `POST /availabilities`, `GET /availabilities`, `DELETE /availabilities/{id}` (fenêtres avec fuseau, 1 an max) |
| Cabinet (titulaire) | `POST /offices`, `GET /offices`, `PUT /offices/{id}`, `POST /offices/{id}/members`, `DELETE /offices/{id}/members/{user}` |
| Publier une offre | `POST /offices/{id}/offers`, modifiable tant qu'elle est `open` via `PUT /offers/{id}` |
| Chercher des offres (F2.1, F2.2) | `GET /offers/search` : `lat`, `lon`, `radius_km`, `min_turnover`, `care` (répétable), `window_start`, `window_end`, `sort` = `relevance` (défaut) \| `distance` \| `turnover` \| `date` |
| Candidater | `POST /offers/{id}/applications`, retrait `DELETE /applications/{id}` (en attente), `GET /me/applications` |
| Décider (titulaire) | `GET /offers/{id}/applications`, `PATCH /offers/{id}/applications/{app}` avec `decision` = `accepted` \| `rejected` |
| Suivre une mission (F3.4) | `POST /offers/{id}/status` avec `action` = `start` \| `complete` \| `cancel` ; `POST /applications/{id}/resign` ; `GET /me/missions` pour le calendrier |

**Recherche** : les coordonnées et le rayon retombent sur ceux du profil quand ils sont omis ; sans coordonnées du tout, aucun filtre de distance n'est appliqué. Chaque résultat porte `distance_km`, `score` (0–100), `availability` (part de l'offre couverte par les disponibilités) et `matched_cares`. Le classement porte sur les 300 offres les plus proches ; restreindre les filtres au-delà. Les offres déjà candidatées, déjà pourvues ou propres au cabinet de l'utilisateur n'apparaissent pas.

**Statuts d'une offre** : `open` → `filled` (candidature acceptée) → `in_progress` → `completed`, avec `cancelled` depuis `open` ou `filled`. `start` n'est possible qu'à partir de `start_at` (`409 too_early`). Une offre `open` dont `valid_till` est dépassé porte `expired: true` : elle n'est plus candidatable, sans changer de statut. Accepter une candidature rejette toutes les autres en attente.

**Rôles** : seuls les `titulaire` créent cabinets, offres et patients ; seuls les `remplacant` cherchent, candidatent et gèrent des disponibilités. Un remplaçant membre d'un cabinet ne voit pas ses propres offres dans la recherche.

## 5. Messagerie

- `POST /conversations { user_id }` ouvre (201) ou retrouve (200) l'échange. Il n'est permis qu'entre professionnels liés : même cabinet, ou l'un a candidaté à une offre du cabinet de l'autre (`403 not_connected` sinon).
- Texte : `POST /conversations/{id}/messages { text }` (1–4000 caractères). Lecture : `GET /conversations/{id}/messages` (plus récents d'abord), `POST /conversations/{id}/read` met à zéro le compteur `unread`.
- Photo : `POST /conversations/{id}/photos` en `multipart/form-data` (`file` JPEG ou PNG de 5 Mo max, `text` optionnel). Le type est lu dans le **contenu**, pas dans l'en-tête. Téléchargement : `GET /messages/{id}/photo`.
- Vocal : `POST /conversations/{id}/voice` (`file` OGG, WebM, MP3, M4A ou WAV, 10 Mo max). La transcription est demandée au service IA ; le message porte `transcript_status` = `ready` (à relire), `unavailable` (IA absente ou en panne, relançable par `POST /messages/{id}/transcript/retry`) ou `validated`. **L'auteur doit valider** (`POST /messages/{id}/transcript/validate`, texte corrigé optionnel) : l'IA ne fait que proposer. Écoute : `GET /messages/{id}/audio`.
- Les messages sont **chiffrés au repos** côté serveur. Ce n'est pas du chiffrement de bout en bout, que le cahier des charges (F4.1) mentionne : il suppose des clés générées sur les appareils et reste à concevoir avec l'équipe mobile.

## 6. Patients et transmissions

`POST /offices/{id}/patients` (titulaire du cabinet, `consent: true` obligatoire), `POST` et `GET /patients/{id}/transmissions`. Accès : membres du cabinet et remplaçant **retenu** sur une mission du cabinet, jusqu'à 30 jours après la fin. Une transmission disparaît 30 jours après sa création. `DELETE /patients/{id}` efface l'identité et toutes les transmissions (droit à l'oubli). Identité et textes sont chiffrés au repos.

## 7. Temps réel et notifications

**WebSocket** `wss://…/api/v1/ws`. Après la connexion, envoyer dans les 5 secondes `{"type": "auth", "token": "<access_token>"}` (jamais dans l'URL). Réponse : `{"type": "ready"}`. Fermeture avec le code `4401` si le jeton est refusé ou expire : se reconnecter après un refresh.

Événements reçus (identifiants seulement, jamais de contenu) :

| `type` | Champs |
| --- | --- |
| `message.new` | `conversation_id`, `message_id` |
| `notification.new` | `notification_type`, plus les identifiants concernés |

Un événement perdu n'est pas rejoué : à la reconnexion, relire `GET /notifications` et les conversations. L'API REST reste la source de vérité.

**Boîte d'alertes** : `GET /notifications` (`unread_only`), `GET /notifications/unread-count`, `POST /notifications/read`, `POST /notifications/{id}/read`. Types : `offer.match` (offre correspondant au profil), `application.received`, `application.decided`, `mission.status`.

**Push** : `PUT /devices { platform, token }` enregistre l'appareil (`DELETE /devices/{token}` l'oublie). Aucun fournisseur FCM/APNs n'est branché pour l'instant ; en attendant, utiliser le WebSocket et la boîte d'alertes.

## 8. Documents légaux

`POST /documents` en `multipart/form-data` : `doc_type` = `carte_pro` \| `rib` \| `assurance`, `file` PDF de 5 Mo max (signature `%PDF-` vérifiée). Un nouvel envoi du même type remplace le précédent et remet le statut à `pending` ; un administrateur le passe à `approved` ou `rejected`. `GET /documents`, `GET /documents/{id}/file`, `DELETE /documents/{id}`.

## 9. Compte et conformité

- `GET /me/export` : tout ce que l'utilisateur a fourni, en JSON (portabilité).
- `DELETE /me { password }` : anonymise le compte et supprime profil, documents, disponibilités, conversations et sessions. Refusé avec `409 active_missions` s'il reste une mission en cours ou une offre ouverte d'un cabinet dont on est titulaire.
- Un administrateur est désigné par `python -m app.promote_admin <email>` (jamais par l'API).

## 10. Exploitation côté client

- Aucune donnée de santé dans les journaux de l'application, les rapports de plantage ni les notifications locales.
- Les fichiers téléversés sont rejetés sur leur contenu, pas sur l'extension : ne pas se fier au nom du fichier.
- Les dates sont en ISO 8601 **avec fuseau**. Une date sans fuseau est refusée (`422`).
