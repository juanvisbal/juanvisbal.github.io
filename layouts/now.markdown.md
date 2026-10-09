# {{ .Title }}

What I’m focused on now.

This is a [now page](https://nownownow.com/about), and if you have your own site, you should make one too.
{{ range .Params.sections }}
## {{ .title }}
{{ range .items }}
- {{ partial "site/md-link.md" . }}{{ with .by }} by {{ range $i, $a := . }}{{ if $i }} and {{ end }}{{ partial "site/md-link.md" (dict "title" $a.name "url" $a.url) }}{{ end }}{{ end }}
{{- end }}
{{ end }}
{{ partial "site/updated.md" . }}
