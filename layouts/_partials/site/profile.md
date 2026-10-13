{{- /*
  Home profile in Markdown, with absolute links, for /index.md and /.well-known/about.md.
  (dict "page" <home> "format" "markdown"): site pages link to their copy in that output format (Markdown for /index.md, "html" for people).
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
