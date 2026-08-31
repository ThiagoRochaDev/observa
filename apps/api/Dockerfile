FROM python:3.12-slim

WORKDIR /observa

# Instala os dois pacotes locais (connector SDK + API) em modo editável,
# igual ao scripts/dev-local.sh — a API depende do observa-connectors por
# nome de pacote, não por caminho, então a ordem importa.
COPY packages/connectors /observa/packages/connectors
COPY apps/api /observa/apps/api

RUN pip install --no-cache-dir -e "/observa/packages/connectors[all]" \
    && pip install --no-cache-dir -e "/observa/apps/api"

ENV DATA_DIR=/data

# Non-root: /data is chowned here (before the VOLUME instruction) so a
# freshly-created volume inherits appuser ownership instead of root's.
RUN useradd -u 1000 -m appuser \
    && mkdir -p /data \
    && chown -R appuser:appuser /data /observa
USER appuser

VOLUME ["/data"]

EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--app-dir", "/observa/apps/api"]
