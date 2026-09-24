# Vídeo completo do Observa

`observa-complete-walkthrough.mp4` apresenta, em um único vídeo, a navegação e os
principais recursos da plataforma: visão FinOps, busca global, produtos,
inventário, budgets, governança, catálogo de conexões, GitHub, alertas,
dashboards, observabilidade, logs, traces, monitores, RUM, GCP Monitoring,
Mapa Vivo, remediações, autenticação, companies/tenancies, CLI e mobile.

As telas web e os resultados da CLI são capturados da instância local em
execução com dados de demonstração. Nenhuma chave, segredo de conector ou dado
de cliente é desenhado nos frames ou gravado no vídeo.

## Regenerar

Com web e API em execução:

```powershell
$env:OBSERVA_DEMO_API_KEY = (Get-Content data/api_key -Raw).Trim()
python scripts/capture_demo.py
python scripts/render_demo_video.py
Remove-Item Env:OBSERVA_DEMO_API_KEY
```

O render exige FFmpeg no `PATH`. Frames e imagens de verificação são temporários
e ignorados pelo Git; somente o MP4 final é versionado.
