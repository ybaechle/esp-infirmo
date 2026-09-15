"""Recalculate sprint evidence using Python's standard library only."""

import argparse
import csv
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent


def number(value):
    if value is None or str(value).strip() == "":
        return None
    parsed = float(value)
    if not math.isfinite(parsed) or parsed < 0:
        raise ValueError(f"Expected a finite non-negative measurement, got {value!r}")
    return parsed


def percentage(part, whole):
    return None if part is None or whole is None or whole == 0 else part / whole * 100


def display(value, suffix=""):
    return "Non mesuré" if value is None else f"{value:.2f}{suffix}"


def effort_metrics(rows):
    ids = [row["id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate task identifiers")
    result = []
    for row in rows:
        baseline, actual, etc = (number(row[key]) for key in ("baseline_hours", "actual_hours", "etc_hours"))
        if row["status"] == "Done" and (actual is None or etc != 0 or not row["evidence"]):
            raise ValueError(f"{row['id']}: Done requires actual hours, ETC=0 and evidence")
        forecast = None if actual is None or etc is None else actual + etc
        variance = None if forecast is None or baseline is None else forecast - baseline
        result.append({**row, "baseline": baseline, "actual": actual, "etc": etc,
                       "forecast": forecast, "variance": variance,
                       "variance_pct": percentage(variance, baseline)})
    committed = [row for row in result if row["sprint"] == "1" and row["committed"] == "yes"]
    complete_baseline = committed and all(row["baseline"] is not None for row in committed)
    planned = sum(row["baseline"] for row in committed) if complete_baseline else None
    delivered = sum(row["baseline"] for row in committed if row["status"] == "Done") if complete_baseline else None
    return result, planned, delivered


def ci_counts(runs):
    counts = Counter()
    for run in runs:
        if run.get("infrastructure_blocked"):
            counts["blocked"] += 1
        elif run["status"] != "completed":
            counts["pending"] += 1
        else:
            counts[run.get("conclusion") or "unknown"] += 1
    return counts


def gh(*args):
    result = subprocess.run(["gh", *args], cwd=ROOT.parent, check=True, capture_output=True, text=True, encoding="utf-8")
    return json.loads(result.stdout)


def refresh_github():
    repo = gh("repo", "view", "--json", "nameWithOwner")["nameWithOwner"]
    runs = gh("run", "list", "--branch", "develop", "--limit", "100", "--json",
              "databaseId,workflowName,headSha,status,conclusion,createdAt,updatedAt,url")
    for run in runs:
        annotations = []
        jobs = []
        if run["conclusion"] == "failure":
            jobs = gh("api", f"repos/{repo}/actions/runs/{run['databaseId']}/jobs")["jobs"]
            for job in jobs:
                if job["conclusion"] == "failure" and not job["steps"]:
                    annotations.extend(gh("api", f"repos/{repo}/check-runs/{job['id']}/annotations"))
        run["infrastructure_blocked"] = bool(jobs) and all(not job["steps"] for job in jobs) and any(
            "Actions budget" in item["message"] for item in annotations
        )
        run["blocker_messages"] = list(dict.fromkeys(item["message"] for item in annotations))
    snapshot = {"collected_at": datetime.now(timezone.utc).isoformat(), "repository": repo,
                "branch": "develop", "window": "latest 100 runs (or fewer if unavailable)", "runs": runs}
    target = ROOT / "evidence" / "github.json"
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def read_csv(name):
    with (ROOT / name).open(encoding="utf-8-sig", newline="") as source:
        return list(csv.DictReader(source))


def render():
    rows, planned, delivered = effort_metrics(read_csv("effort.csv"))
    lines = ["# Tableau de bord - sprint 1", "", "Généré par `python reporting/dashboard.py`; ne pas modifier à la main.", "",
             "## Charge et avancement", "",
             f"- Charge engagée confirmée du sprint : {display(planned, ' h')}.",
             f"- Vélocité acceptée selon la DoD : {display(delivered, ' h')}.",
             f"- Réalisation de l'engagement : {display(percentage(delivered, planned), ' %')}.",
             f"- Tickets avec heures réelles déclarées : {sum(row['actual'] is not None for row in rows)}/{len(rows)}.",
             f"- Tickets avec ETC déclaré : {sum(row['etc'] is not None for row in rows)}/{len(rows)}.", "",
             "Les estimations initiales sont celles des tickets complets du cadrage. Les cellules inconnues ne valent pas zéro.", "",
             "| Tâche | Responsable | Initial (h) | Réel (h) | ETC (h) | Prévision (h) | Écart (h) | Écart (%) | Statut |",
             "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |"]
    for row in rows:
        if row["status"] in {"In Progress", "In Review", "Done", "Blocked"} or row["sprint"] == "1":
            values = [row["id"], row["owner"], *(display(row[key]) for key in ("baseline", "actual", "etc", "forecast", "variance", "variance_pct")), row["status"]]
            lines.append("| " + " | ".join(values) + " |")
    lines.extend(["", "## Dérive et onboarding", ""])
    runs = read_csv("runs.csv")
    if not runs:
        lines.append("PDR et durée d'installation : **non mesurés**. Aucun protocole complet chronométré enregistré.")
    for run in runs:
        prescribed, adjustments = number(run["prescribed_actions"]), number(run["unprescribed_actions"])
        if prescribed == 0:
            raise ValueError(f"{run['run_id']}: baseline must contain at least one action")
        lines.append(f"- {run['run_id']} ({run['kind']}, {run['result']}) : PDR {display(percentage(adjustments, prescribed), ' %')}; durée {display(number(run['duration_minutes']), ' min')}. Preuve : {run['evidence']}.")
    lines.extend(["", "## Intégration continue", ""])
    snapshot_path = ROOT / "evidence" / "github.json"
    if snapshot_path.exists():
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        counts = ci_counts(snapshot["runs"])
        total = len(snapshot["runs"])
        executed = counts["success"] + counts["failure"]
        other = total - sum(counts[key] for key in ("success", "failure", "blocked", "skipped", "cancelled", "pending"))
        lines.extend([f"Instantané : {snapshot['collected_at']}; `{snapshot['repository']}`, branche `{snapshot['branch']}`, {snapshot['window']}.", "",
                      f"- Succès : {counts['success']}/{total}; taux global {display(percentage(counts['success'], total), ' %')}.",
                      f"- Échecs exécutés : {counts['failure']}; blocages d'infrastructure : {counts['blocked']}.",
                      f"- Ignorés : {counts['skipped']}; annulés : {counts['cancelled']}; en cours : {counts['pending']}.",
                      f"- Autres résultats terminaux (timeouts, approbations requises, etc.) : {other}.",
                      f"- Taux de succès des runs exécutés succès/échec : {display(percentage(counts['success'], executed), ' %')}.",
                      "- Durée cible : moins de 15 minutes; un job bloqué avant démarrage ne valide pas cette cible."])
    else:
        lines.append("Non mesurée : aucun instantané GitHub collecté.")
    lines.extend(["", "## Qualité et gouvernance", "",
                  "Les résultats locaux, leur périmètre et leurs limites figurent dans [la preuve de vérification](evidence/verification.md).",
                  "La couverture backend doit atteindre 70 %. Les rapports CI sont conservés en artefacts; une couverture du service IA de santé ne prouve pas Whisper.",
                  "La validation indépendante, le coût des réunions et les décisions de rétrospective restent dans [le bilan](sprint-1.md).", ""])
    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh-github", action="store_true", help="Read GitHub evidence using the current gh identity")
    args = parser.parse_args()
    if args.refresh_github:
        refresh_github()
    (ROOT / "dashboard.md").write_text(render(), encoding="utf-8")
    print("Updated reporting/dashboard.md")
