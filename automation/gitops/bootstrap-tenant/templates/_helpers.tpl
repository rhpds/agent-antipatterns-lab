{{/* RHDP supplies tenant.user.name; standalone installs may supply username explicitly. */}}
{{- define "tenant.username" -}}
{{- $tenant := default dict .Values.tenant -}}
{{- $user := default dict $tenant.user -}}
{{- $explicit := default "" .Values.username -}}
{{- $provided := default "" $user.name -}}
{{- if and $explicit $provided (ne $explicit $provided) -}}
{{- fail "participant identity conflict: username and tenant.user.name must identify the same participant" -}}
{{- end -}}
{{- $name := required "participant identity is required: set username or tenant.user.name" (default $provided $explicit) -}}
{{- if or (gt (len $name) 59) (not (regexMatch "^[a-z0-9]([a-z0-9-]*[a-z0-9])?$" $name)) -}}
{{- fail "participant identity must be a lowercase DNS label of at most 59 characters (the namespace adds -app)" -}}
{{- end -}}
{{- $name -}}
{{- end -}}
