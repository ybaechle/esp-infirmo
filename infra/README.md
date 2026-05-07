# infra/

Infrastructure-as-code, container images, and deployment manifests for Infirmo.

## Stack

- **IaC:** Terraform (cloud provider TBD)
- **Local dev:** Docker / Docker Compose
- **Orchestration:** Kubernetes (manifests + Helm charts as workloads grow)

This README is a placeholder. Module layout (`terraform/<env>/`, `compose/`, `k8s/`, `charts/`), CI/CD wiring, and secrets handling will be filled in by the infra scaffold ticket.

## Owner(s)

- TBD

## Notes

- State files (`*.tfstate`) and variable files (`*.tfvars`) are ignored — commit `*.tfvars.example` instead.
- Local `docker-compose.override.yml` is ignored to allow per-developer tweaks.
- `kubeconfig` and `secrets/` are ignored — use a secret manager (Vault / SOPS / cloud-native) rather than committing secrets.

## Versioning

Versioned alongside the package(s) being deployed. There is no separate `infra-v*` tag.
