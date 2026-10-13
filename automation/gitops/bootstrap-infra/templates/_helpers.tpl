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

{{/* Public host of the shared RHOAI Gateway. */}}
{{- define "infra.gatewayHost" -}}
{{- default (printf "data-science-gateway.%s" .Values.deployer.domain) .Values.mcpGateway.publicHost -}}
{{- end }}

{{/* True when the GPU model-serving pieces should render. */}}
{{- define "infra.serving" -}}
{{- if and .Values.gpu.enabled .Values.modelServing.enabled .Values.rhoai.enabled -}}true{{- end -}}
{{- end }}
