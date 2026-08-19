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

echo "=== Kuadrant CR (cascades Authorino + Limitador data-plane instances) ==="
oc delete kuadrant kuadrant -n mcp-system --ignore-not-found --wait=false

echo "=== MCP Gateway CRs ==="
oc delete mcpvirtualserver rh1-catalog -n redhat-ods-applications --ignore-not-found --wait=false
oc delete mcpserverregistration rh1-mcp-server -n redhat-ods-applications --ignore-not-found --wait=false
oc delete mcpgatewayextension rh1-mcp-gateway -n redhat-ods-applications --ignore-not-found --wait=false

echo "=== MCP Gateway supporting infra (redhat-ods-applications) ==="
oc delete deploy,svc rh1-mcp-server --ignore-not-found -n redhat-ods-applications --wait=false
oc delete deploy,svc rh1-mcp-redis --ignore-not-found -n redhat-ods-applications --wait=false
oc delete configmap rh1-mcp-server-script --ignore-not-found -n redhat-ods-applications --wait=false
oc delete secret rh1-mcp-session-store rh1-mcp-trusted-headers --ignore-not-found -n redhat-ods-applications --wait=false
oc delete httproute rh1-mcp-server --ignore-not-found -n redhat-ods-applications --wait=false
oc delete networkpolicy allow-mcp-gateway-extproc --ignore-not-found -n redhat-ods-applications --wait=false
oc delete referencegrant allow-rh1-mcp-gateway-ext --ignore-not-found -n openshift-ingress --wait=false

echo "=== MLflow (this deletes the tracked experiments/runs — the CR + its PVC) ==="
oc delete mlflow mlflow --ignore-not-found -n redhat-ods-applications --wait=false
oc delete route mlflow --ignore-not-found -n redhat-ods-applications --wait=false

echo "=== rh1-lab-eval namespace (EvalHub, NeMoGuardrails, GuardrailsOrchestrator, mock-target, RBAC — everything in it) ==="
oc delete namespace rh1-lab-eval --ignore-not-found --wait=false

echo
echo "Deletes issued (mostly async). Check progress with:"
echo "  oc get namespace rh1-lab-eval"
echo "  oc get pods -n redhat-ods-applications -n mcp-system"
echo "  oc describe node <node> | grep -A6 'Allocated resources'"
