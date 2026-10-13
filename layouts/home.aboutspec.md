{{- /*
  AboutSpec (https://aboutspec.org/): who Juan is, at /.well-known/about.md. summary: the bio, as a
  YAML string; then the Markdown body of content/_index.md. Links and socials are in contact.vcf.
*/ -}}
---
summary: {{ .Params.bio | jsonify }}
---

{{ .RawContent | strings.TrimSpace }}

