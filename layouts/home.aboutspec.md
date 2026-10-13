{{- /* AboutSpec (https://aboutspec.org/): the home profile at /.well-known/about.md. summary: the bio, as a YAML string. */ -}}
---
summary: {{ .Params.bio | jsonify }}
---

{{ partial "site/profile.md" (dict "page" . "format" "html") }}
