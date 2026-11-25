#!/usr/bin/env bash
# Reverse of deploy.sh — removes everything back to the "operators installed,
# no instances deployed" baseline. Safe to run even if only some components
# were deployed, or none were.
set -uo pipefail

if ! command -v oc >/dev/null; then
  echo "oc CLI not found" >&2
  exit 1
fi
oc whoami >/dev/null || { echo "not logged in — set KUBECONFIG" >&2; exit 1; }

echo "=== MLflow (this deletes the tracked experiments/runs — the CR + its PVC) ==="
oc delete mlflow mlflow --ignore-not-found -n redhat-ods-applications --wait=false
oc delete route mlflow --ignore-not-found -n redhat-ods-applications --wait=false

echo "=== rh1-lab-eval namespace (EvalHub, NeMoGuardrails, GuardrailsOrchestrator, mock-target, RBAC — everything in it) ==="
oc delete namespace rh1-lab-eval --ignore-not-found --wait=false

echo
echo "Deletes issued (mostly async). Check progress with:"
echo "  oc get namespace rh1-lab-eval"
echo "  oc get pods -n redhat-ods-applications"
echo "  oc describe node <node> | grep -A6 'Allocated resources'"
