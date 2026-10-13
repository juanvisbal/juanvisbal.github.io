{{- /*
  Home profile in Markdown, with absolute links, for /index.md (/.well-known/about.md is prose instead:
  home.aboutspec.md). (dict "page" <home> "format" "markdown"): site pages link to their copy in
  that output format.
*/ -}}
{{- $format := .format -}}
{{- with .page -}}
{{- $blog := site.GetPage "/blog" -}}
{{ .Params.bio }}

## Links
{{ range .Params.links }}
- [{{ .name }}]({{ with site.GetPage .url }}{{ with .OutputFormats.Get $format }}{{ .Permalink }}{{ else }}{{ .Permalink }}{{ end }}{{ else }}{{ .url | absURL }}{{ end }}){{ if .feeds }} ([RSS]({{ ($blog.OutputFormats.Get "rss").Permalink }}), [JSON Feed]({{ ($blog.OutputFormats.Get "json").Permalink }})){{ end }}
{{- end }}

## Elsewhere
{{ range .Params.elsewhere }}
- [{{ .name }}]({{ .url }})
{{- end }}

---

He/They · 🏳️‍🌈 · Bogotá, Colombia
{{- end -}}
