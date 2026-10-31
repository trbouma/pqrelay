FROM python:3.11-slim-bookworm AS builder
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake git ninja-build pkg-config libssl-dev ca-certificates coreutils \
    && rm -rf /var/lib/apt/lists/*

# liboqs 0.16.0: explicit build-time provisioning, never a runtime install.
ARG LIBOQS_REF=5a1a854b0dc9f2141bdc771c555ee60c37950183
# Fail after 60 seconds below 1 KiB/s, or 10 minutes total. Never fetch history.
RUN git init /tmp/liboqs \
    && git -C /tmp/liboqs remote add origin https://github.com/open-quantum-safe/liboqs.git \
    && GIT_TERMINAL_PROMPT=0 timeout --kill-after=30s 600s \
       git -C /tmp/liboqs -c http.lowSpeedLimit=1024 -c http.lowSpeedTime=60 \
       fetch --depth=1 --no-tags --progress origin "${LIBOQS_REF}" \
    && git -C /tmp/liboqs checkout --detach FETCH_HEAD \
    && test "$(git -C /tmp/liboqs rev-parse HEAD)" = "${LIBOQS_REF}"

RUN cmake -S /tmp/liboqs -B /tmp/liboqs/build -G Ninja \
       -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=ON \
       -DOQS_BUILD_ONLY_LIB=ON -DOQS_USE_OPENSSL=ON \
       '-DOQS_MINIMAL_BUILD=SIG_ml_dsa_44;KEM_ml_kem_768' \
       -DCMAKE_INSTALL_PREFIX=/opt/liboqs \
    && cmake --build /tmp/liboqs/build --parallel 4 \
    && cmake --install /tmp/liboqs/build

WORKDIR /build
COPY pyproject.toml poetry.lock ./
RUN pip install --no-cache-dir poetry==1.8.5 \
    && python -m venv /opt/venv
ENV VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_EXPERIMENTAL_SYSTEM_GIT_CLIENT=true
RUN poetry install --only main --no-root --no-interaction --no-ansi

FROM python:3.11-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends libssl3 ca-certificates \
    && rm -rf /var/lib/apt/lists/*
COPY --from=builder /opt/liboqs /opt/liboqs
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    PQRELAY_LIBOQS_PATH=/opt/liboqs/lib/liboqs.so
WORKDIR /app
COPY app /app/app
RUN mkdir -p /app/data \
    && python -c 'import os; from stroma.pq import PQBackend; PQBackend(os.environ["PQRELAY_LIBOQS_PATH"])'
CMD ["python", "app/relay.py"]
