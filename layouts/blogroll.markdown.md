# {{ .Title }}

{{ .Params.note }}

Inspired by old-school blogrolls. You can subscribe to this same list via [OPML export]({{ (.OutputFormats.Get "opml").Permalink }}).

## Roll
{{ range partial "site/blogroll.html" . }}
- [{{ .title }}]({{ .htmlUrl }}) · [feed]({{ .xmlUrl }})
{{- end }}

{{ partial "site/updated.md" . }}
