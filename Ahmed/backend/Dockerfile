# Contexte de build = racine du dépôt (pour inclure ontologie/pharma.ttl)
FROM python:3.11-slim
WORKDIR /repo/Ahmed/backend
COPY Ahmed/backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY ontologie /repo/ontologie
COPY Ahmed/ontology-extension /repo/Ahmed/ontology-extension
COPY Ahmed/backend /repo/Ahmed/backend
RUN python scripts/setup_models.py
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
