# syntax=docker/dockerfile:1
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DATABASE_URL=sqlite:////data/database.db

WORKDIR /app

# Код өзгергенде тәуелділіктер қабаты қайта жиналмайды.
COPY requirements-backend.txt ./requirements.txt
# Cloud-та proxy_ca secret беруге болады; жергілікті жинақта ол қажет емес.
RUN --mount=type=secret,id=proxy_ca \
    if [ -f /run/secrets/proxy_ca ]; then \
        PIP_CERT=/run/secrets/proxy_ca pip install --no-cache-dir -r requirements.txt; \
    else \
        pip install --no-cache-dir -r requirements.txt; \
    fi

RUN groupadd --gid 10001 staybook \
    && useradd --uid 10001 --gid staybook --home-dir /app \
        --shell /usr/sbin/nologin staybook \
    && mkdir -p /data \
    && chown staybook:staybook /app /data

COPY --chown=staybook:staybook app ./app
COPY --chown=staybook:staybook seed.py ./seed.py

USER staybook
EXPOSE 8000

# Мысал деректер тек бос базаға қосылады; кейін пайдаланушының өзгерістері сақталады.
CMD ["sh", "-c", "python seed.py --if-empty && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
