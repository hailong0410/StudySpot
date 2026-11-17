FROM python:3.12-slim AS dependencies
WORKDIR /build
COPY requirements-runtime-lock.txt .
RUN python -m venv /opt/studyspot && \
    /opt/studyspot/bin/pip install --no-cache-dir --no-compile -r requirements-runtime-lock.txt && \
    /opt/studyspot/bin/pip check

FROM python:3.12-slim AS runtime
ARG COMMIT_SHA=local
LABEL org.opencontainers.image.source="https://github.com/hailong0410/StudySpot" \
      org.opencontainers.image.revision="${COMMIT_SHA}"
ENV PATH="/opt/studyspot/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    STUDYSPOT_COMMIT="${COMMIT_SHA}" STUDYSPOT_INSTANCE=/data \
    STUDYSPOT_PORT=5000 STUDYSPOT_JSON_LOGS=1
RUN groupadd --system --gid 10001 studyspot && \
    useradd --system --uid 10001 --gid studyspot studyspot && \
    install -d -m 0700 -o studyspot -g studyspot /data
WORKDIR /app
COPY --from=dependencies /opt/studyspot /opt/studyspot
COPY app.py domain.py schema.sql campus-spaces.json VERSION ./
COPY templates/ templates/
COPY static/ static/
USER 10001:10001
EXPOSE 5000
HEALTHCHECK --interval=15s --timeout=3s --start-period=15s --retries=3 \
    CMD ["python", "-c", "from urllib.request import urlopen; urlopen('http://127.0.0.1:5000/health', timeout=2).close()"]
CMD ["waitress-serve", "--listen=0.0.0.0:5000", "--call", "app:create_app"]
