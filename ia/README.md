# ia/

AI/ML workbench for Infirmo: experimentation, training pipelines, and model serving.

## Stack

- **Language:** Python (3.x — pinned in the IA scaffold ticket)
- **Notebooks:** Jupyter (`.ipynb`) for exploration
- **Frameworks:** TBD — expected mix of PyTorch, scikit-learn, Hugging Face Transformers
- **Experiment tracking:** TBD (W&B / MLflow are pre-ignored to keep the option open)

This README is a placeholder. Concrete environment setup (`pyproject.toml`/`requirements.txt`, dataset access, model registry) will be filled in by the IA scaffold ticket.

## Conventions (provisional)

- Datasets live under `data/` and are **not** committed (large files use external storage / DVC).
- Trained models live under `models/` or `checkpoints/` and are **not** committed — publish through the model registry instead.
- Notebooks should be cleared of outputs before commit (`nbstripout` is recommended).

## Owner(s)

- TBD

## Versioning

Released independently as `ia-vX.Y.Z`.
