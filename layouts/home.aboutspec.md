{{- /*
  AboutSpec (https://aboutspec.org/): who Juan is, at /.well-known/about.md. summary: the bio, as a
  YAML string; then the About page's text (content/about.md). Links and socials are in contact.vcf.
*/ -}}
---
summary: {{ .Params.bio | jsonify }}
---

### {{ i18n "aboutHeading" (dict "name" (index (split site.Title " ") 0)) }}

{{ (partial "site/english-page.html" (dict "path" "/about")).RawContent | strings.TrimSpace }}

