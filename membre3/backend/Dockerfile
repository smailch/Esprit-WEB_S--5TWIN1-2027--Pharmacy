# Contexte de build = racine du dépôt (pour inclure ontologie/pharma.ttl)
FROM python:3.11-slim
WORKDIR /repo/membre3/backend
COPY membre3/backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY ontologie /repo/ontologie
COPY membre3/ontology-extension /repo/membre3/ontology-extension
COPY membre3/backend /repo/membre3/backend
RUN python scripts/setup_models.py
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
