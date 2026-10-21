# {{ .Title }}

{{ .Params.note }}

{{ i18n "blogrollIntroMd" (dict "url" (.OutputFormats.Get "opml").Permalink) }}

## {{ i18n "roll" }}
{{ range partial "site/blogroll.html" . }}
{{- with .name }}

### {{ . }}
{{- end }}
{{ range .feeds }}
- [{{ .title }}]({{ .htmlUrl }}) · [{{ i18n "feed" }}]({{ .xmlUrl }})
{{- end }}
{{- end }}

{{ partial "site/updated.md" . }}
