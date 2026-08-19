#!/usr/bin/env bash
# Stand up lab-verification instances of the RH1 lab's RHOAI components on the
# homelab SNO dev cluster, with correct low resource requests and every
# gotcha discovered during 2026-08-19 verification already fixed — see
# publishing-house/worklog.yaml entries 2026-08-19-020 through -023 for the
# full story behind each fix, and the comments in manifests/ for the specific
# "why".
#
# Usage:
#   KUBECONFIG=~/.kube/sno.kubeconfig ./deploy.sh [component ...]
#   components: mock-target mlflow nemoguardrails evalhub mcp-gateway guardrailsorchestrator all
#   (default: all)
#
# This is DEV/VERIFICATION scaffolding, not the delivered lab content. Run
# teardown.sh when you're done to give the CPU back — this cluster runs at
# ~90%+ CPU requested even at idle, and every instance here has a real cost.
set -euo pipefail

if ! command -v oc >/dev/null; then
  echo "oc CLI not found" >&2
  exit 1
fi
oc whoami >/dev/null || { echo "not logged in — set KUBECONFIG" >&2; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MANIFESTS="$SCRIPT_DIR/manifests"
COMPONENTS=("${@:-all}")

want() {
  local c="$1"
  [[ " ${COMPONENTS[*]} " == *" all "* ]] || [[ " ${COMPONENTS[*]} " == *" $c "* ]]
}

wait_for() {
  local kind=$1 name=$2 ns=$3 jsonpath=$4 want_val=$5 tries=${6:-30}
  for ((i = 1; i <= tries; i++)); do
    local val
    val=$(oc get "$kind" "$name" -n "$ns" -o jsonpath="$jsonpath" 2>/dev/null || true)
    [[ "$val" == "$want_val" ]] && return 0
    sleep 5
  done
  echo "WARNING: $kind/$name in $ns did not reach $jsonpath=$want_val after $((tries * 5))s" >&2
  return 1
}

oc apply -f "$MANIFESTS/00-namespace.yaml"

if want mock-target; then
  echo "=== mock-target (OpenAI-compatible stand-in for the real vLLM endpoint) ==="
  oc create configmap mock-target-script -n rh1-lab-eval \
    --from-file=mock-target.py="$MANIFESTS/mock-target.py" \
    --dry-run=client -o yaml | oc apply -f -
  oc apply -f "$MANIFESTS/mock-target-deploy.yaml"
fi

if want mlflow; then
  echo "=== MLflow (Round 3) ==="
  oc apply -f "$MANIFESTS/mlflow.yaml"
  wait_for mlflow mlflow redhat-ods-applications '{.status.conditions[?(@.type=="Available")].status}' True 24
  echo "Route: https://$(oc get route mlflow -n redhat-ods-applications -o jsonpath='{.spec.host}')"
fi

if want nemoguardrails; then
  echo "=== NeMo Guardrails (Round 4, GA in 3.4, no GPU dependency) ==="
  oc create configmap rh1-nemo-config -n rh1-lab-eval \
    --from-file=config.yaml="$MANIFESTS/nemoguardrails-config.yaml" \
    --from-file=rails.co="$MANIFESTS/nemoguardrails-rails.co" \
    --dry-run=client -o yaml | oc apply -f -
  oc apply -f "$MANIFESTS/nemoguardrails.yaml"
fi

if want evalhub; then
  echo "=== EvalHub + Garak (Round 4 priority verification gate) ==="
  oc apply -f "$MANIFESTS/evalhub.yaml"
  wait_for evalhub rh1-evalhub rh1-lab-eval '{.status.phase}' Ready 24
  echo "Call the API with: X-Tenant: rh1-lab-eval header + a token from"
  echo "  oc create token evalhub-tester -n rh1-lab-eval"
fi

if want guardrailsorchestrator; then
  echo "=== GuardrailsOrchestrator (Round 4 — WILL fail until a real InferenceService exists, see manifest comment) ==="
  oc apply -f "$MANIFESTS/guardrailsorchestrator.yaml"
fi

if want mcp-gateway; then
  echo "=== MCP Gateway (Round 2) ==="

  # Discover the shared AI Gateway's actual public hostname from the mlflow
  # CR's own status.url, rather than hardcoding it, so this works on any
  # cluster. NOTE: this is NOT the same as the classic OpenShift Route named
  # "mlflow" (mlflow-redhat-ods-applications.apps...) — that's a separate
  # Route object with its own auto-generated hostname. The Gateway API traffic
  # (dashboard, /mlflow via Gateway, /mcp) all shares one hostname, which only
  # a component's own status field reliably exposes.
  GATEWAY_HOST=$(oc get mlflow mlflow -n redhat-ods-applications -o jsonpath='{.status.url}' 2>/dev/null \
    | sed -E 's#^https?://([^/]+).*#\1#')
  if [[ -z "$GATEWAY_HOST" ]]; then
    echo "Could not auto-discover the Gateway hostname (deploy mlflow first, or set GATEWAY_HOST manually)." >&2
    exit 1
  fi
  echo "Using Gateway host: $GATEWAY_HOST"

  oc apply -f "$MANIFESTS/mcp-kuadrant.yaml"
  oc apply -f "$MANIFESTS/mcp-redis.yaml"
  oc apply -f "$MANIFESTS/mcp-referencegrants.yaml"
  oc apply -f "$MANIFESTS/mcp-networkpolicy.yaml"
  oc apply -f "$MANIFESTS/mcp-session-secret.yaml"

  oc create configmap rh1-mcp-server-script -n redhat-ods-applications \
    --from-file=mcp-server.py="$MANIFESTS/mock-mcp-server.py" \
    --dry-run=client -o yaml | oc apply -f -
  oc apply -f "$MANIFESTS/mcp-server-deploy.yaml"

  sed "s/__GATEWAY_HOST__/$GATEWAY_HOST/" "$MANIFESTS/mcp-httproute.yaml.tmpl" | oc apply -f -
  sed "s/__GATEWAY_HOST__/$GATEWAY_HOST/" "$MANIFESTS/mcp-gateway-extension.yaml.tmpl" | oc apply -f -

  wait_for mcpgatewayextension rh1-mcp-gateway redhat-ods-applications '{.status.conditions[?(@.type=="Ready")].status}' True 24

  oc apply -f "$MANIFESTS/mcp-server-registration.yaml"
  wait_for mcpserverregistration rh1-mcp-server redhat-ods-applications '{.status.conditions[?(@.type=="Ready")].status}' True 24

  oc apply -f "$MANIFESTS/mcp-virtualserver.yaml"

  oc create serviceaccount evalhub-tester -n rh1-lab-eval --dry-run=client -o yaml | oc apply -f -
  oc create serviceaccount rh1-mcp-admin -n rh1-lab-eval --dry-run=client -o yaml | oc apply -f -

  echo "MCP_URL: https://$GATEWAY_HOST/mcp"
  echo "Auth: Authorization: Bearer \$(oc create token <sa> -n rh1-lab-eval)"
  echo "Regular identity (evalhub-tester) sees only rh1_public_echo."
  echo "Admin identity (rh1-mcp-admin) additionally sees rh1_admin_reset."
fi

echo
echo "Done. Run ./teardown.sh when finished to reclaim CPU."
