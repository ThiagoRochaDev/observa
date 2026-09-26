# Demonstrações do Observa

A gravação anterior foi retirada da versão atual do repositório. Não reutilize
seus frames. Novas capturas devem seguir a [política de mídia](../DEMO_MEDIA_POLICY.md)
e mostrar apenas dados fictícios de produtos TGR.

Use uma instância local descartável e somente conexões Mock Demo. A validação
automática é uma barreira inicial; revise cada imagem antes de publicar. Não
use um ambiente real, mesmo que contenha um conector Mock Demo.

## Regenerar

Com web e API em execução:

```powershell
$env:OBSERVA_DEMO_API_KEY = (Get-Content data/api_key -Raw).Trim()
$env:OBSERVA_DEMO_SYNTHETIC_ONLY = '1'
python scripts/capture_demo.py
python scripts/render_demo_video.py
Remove-Item Env:OBSERVA_DEMO_API_KEY
Remove-Item Env:OBSERVA_DEMO_SYNTHETIC_ONLY
```

O render exige FFmpeg no `PATH`. Frames e imagens de verificação são temporários
e ignorados pelo Git; somente o MP4 final é versionado.
