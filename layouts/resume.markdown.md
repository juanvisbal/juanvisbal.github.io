# {{ .Title }}

{{ .Params.note }}

{{ .Params.summary }}

[Download PDF]({{ "resume.pdf" | absURL }})

## Work Experience
{{ range .Params.roles }}
### {{ .title }}
{{ range .items }}
- {{ . }}
{{- end }}
{{ end }}
## Skills

| | |
|---|---|
{{- range .Params.skills }}
| {{ .name }} | {{ .value }} |
{{- end }}

## Education & Training
{{ range .Params.education }}
- {{ . }}
{{- end }}

## Languages
{{ range .Params.languages }}
- {{ . }}
{{- end }}

## About

| | |
|---|---|
{{- range .Params.about }}
| {{ .name }} | {{ .value }} |
{{- end }}

## Portfolio
{{ range .Params.portfolio }}
- {{ .name }}{{ with .url }} — [{{ partial "site/bare-url.html" . }}]({{ . }}){{ end }}
{{- end }}
