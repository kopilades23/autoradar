# La Bonne Occaz en ligne (mode « http », sans navigateur) : image légère.
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 AUTORADAR_HOTE=0.0.0.0 AUTORADAR_PORT=8000 TZ=Europe/Paris
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
# AUTORADAR_MOT_DE_PASSE doit être fourni au lancement (le serveur refuse de démarrer sans).
CMD ["python", "server.py", "--no-browser"]
