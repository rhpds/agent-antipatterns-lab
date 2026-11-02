{{/* Sync-wave + dry-run-skip annotations for CRs whose CRD arrives with an operator. */}}
{{- define "infra.crAnnotations" -}}
argocd.argoproj.io/sync-wave: {{ .wave | quote }}
argocd.argoproj.io/sync-options: SkipDryRunOnMissingResource=true
{{- end }}

{{/* Namespace + OperatorGroup + Subscription. Args: dict ns, name, channel, source, targetNamespaces (bool) */}}
{{- define "infra.operator" -}}
apiVersion: v1
kind: Namespace
metadata:
  name: {{ .ns }}
  annotations:
    argocd.argoproj.io/sync-wave: "-20"
---
apiVersion: operators.coreos.com/v1
kind: OperatorGroup
metadata:
  name: {{ .name }}
  namespace: {{ .ns }}
  annotations:
    argocd.argoproj.io/sync-wave: "-20"
spec:
{{- if .ownNamespaceOnly }}
  targetNamespaces:
    - {{ .ns }}
{{- else }}
  upgradeStrategy: Default
{{- end }}
---
apiVersion: operators.coreos.com/v1alpha1
kind: Subscription
metadata:
  name: {{ .name }}
  namespace: {{ .ns }}
  annotations:
    argocd.argoproj.io/sync-wave: "-15"
spec:
  channel: {{ .channel }}
  installPlanApproval: Automatic
  name: {{ .name }}
  source: {{ .source }}
  sourceNamespace: openshift-marketplace
{{- end }}

{{/* MCP host: the shared RHOAI Gateway's in-cluster address unless publicHost is set. */}}
{{- define "infra.gatewayHost" -}}
{{- $gw := .Values.mcpGateway.gateway -}}
{{- default (printf "%s-%s.%s.svc.cluster.local" $gw.name $gw.className $gw.namespace) .Values.mcpGateway.publicHost -}}
{{- end }}

{{/* True when the GPU model-serving pieces should render. */}}
{{- define "infra.serving" -}}
{{- if and .Values.gpu.enabled .Values.modelServing.enabled .Values.rhoai.enabled -}}true{{- end -}}
{{- end }}
