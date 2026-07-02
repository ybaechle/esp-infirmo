<!--
INFIRMO — Pull Request
Fill every section. PRs target `develop` (never `main` directly).
Conventional Commits + a green DoD are required to merge.
-->

## Résumé / Summary

<!-- What does this PR change and why? One or two sentences. -->

## Ticket lié / Linked issue

Closes #<!-- INF-XX or issue number -->

## Type de changement / Change type

- [ ] `feat` — nouvelle fonctionnalité
- [ ] `fix` — correction de bug
- [ ] `docs` — documentation
- [ ] `chore` / `ci` / `refactor` / `test` / `perf`

## Module(s)

- [ ] `mobile/` (Flutter)
- [ ] `backend/` (FastAPI)
- [ ] `ia/` (Whisper)
- [ ] `infra/` (Docker / CI/CD / K8s / HDS)
- [ ] `docs/`

## Comment tester / How to test

<!-- Steps or commands a reviewer runs to verify the change. -->

---

## Definition of Done (DoD)

- [ ] Le code respecte les conventions du projet (voir `CONTRIBUTING.md` / `AGENTS.md`).
- [ ] Commits en **Conventional Commits** (`git cz`).
- [ ] Tests ajoutés/à jour et **verts** ; données de test **synthétiques uniquement**.
- [ ] Lint / type-check passent en CI.
- [ ] Pas de secret, token, ni fichier sensible commité (`.env`, `*.tfvars`, `secrets/`…).
- [ ] Documentation / README du module à jour si nécessaire.

### Conformité données de santé / Health-data compliance — `AGENTS.md §5`

> Cocher **N/A** uniquement si le changement ne touche **aucune** donnée personnelle
> ou de santé (y compris logs, fixtures, audio/voix, config d'hébergement).

- [ ] **N/A** — ce PR ne touche aucune donnée personnelle ou de santé.

Sinon (si des données personnelles / de santé sont concernées) :

- [ ] Données traitées comme **catégorie particulière (RGPD Art. 9)** ; minimisation appliquée.
- [ ] Aucune donnée de santé / **secret médical** / secret / token dans les logs, métriques, traces ou rapports d'erreur.
- [ ] Chiffrement **en transit (TLS)** et **au repos** assuré ; résidence **UE / France**.
- [ ] Toute nouvelle dépendance/SaaS traitant des données personnelles a un **DPA (Art. 28)** et reste en UE.
- [ ] Audio/transcription : pas d'envoi de données de santé réelles à une IA externe sans hébergement **HDS** + DPA.
- [ ] Revue **`compliance-reviewer`** demandée pour ce PR.

<!--
Astuce : lancer l'agent `compliance-reviewer` sur le diff avant de demander la revue humaine.
Tip: run the `compliance-reviewer` agent on the diff before requesting human review.
-->
