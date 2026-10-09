{{- $blog := site.GetPage "/blog" -}}
# {{ site.Title }}

{{ .Params.bio }}

## Links
{{ range .Params.links }}
- [{{ .name }}]({{ with site.GetPage .url }}{{ with .OutputFormats.Get "markdown" }}{{ .Permalink }}{{ else }}{{ .Permalink }}{{ end }}{{ else }}{{ .url | absURL }}{{ end }}){{ if .feeds }} ([RSS]({{ ($blog.OutputFormats.Get "rss").Permalink }}), [JSON Feed]({{ ($blog.OutputFormats.Get "json").Permalink }})){{ end }}
{{- end }}

## Elsewhere
{{ range .Params.elsewhere }}
- [{{ .name }}]({{ .url }})
{{- end }}

---

He/They · 🏳️‍🌈 · Bogotá, Colombia
