# {{ .Title }}

{{ .Params.note }}

{{ .Params.summary }}

[{{ i18n "resumeDownload" }}]({{ site.Params.resumePdf | absURL }})

## {{ i18n "resumeWork" }}
{{ range .Params.roles }}
### {{ .title }}
{{ range .items }}
- {{ . }}
{{- end }}
{{ end }}
## {{ i18n "resumeSkills" }}

| | |
|---|---|
{{- range .Params.skills }}
| {{ .name }} | {{ .value }} |
{{- end }}

## {{ i18n "resumeEducation" }}
{{ range .Params.education }}
- {{ . }}
{{- end }}

## {{ i18n "resumeLanguages" }}
{{ range .Params.languages }}
- {{ . }}
{{- end }}

## {{ i18n "resumeAbout" }}

| | |
|---|---|
{{- range .Params.about }}
| {{ .name }} | {{ .value }} |
{{- end }}

## {{ i18n "resumePortfolio" }}
{{ range .Params.portfolio }}
- {{ .name }}{{ with .url }} — [{{ partial "site/bare-url.html" . }}]({{ . }}){{ end }}
{{- end }}
