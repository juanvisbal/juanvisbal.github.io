# {{ .Title }}

{{ .Params.note }}

This is a [now page](https://nownownow.com/about), and if you have your own site, you should make one too.

{{ .RawContent | strings.TrimSpace }}

{{ partial "site/updated.md" . }}
