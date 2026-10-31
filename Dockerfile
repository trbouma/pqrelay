FROM python:3.11-slim-bookworm AS builder
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake git ninja-build pkg-config libssl-dev ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# liboqs 0.16.0: explicit build-time provisioning, never a runtime install.
ARG LIBOQS_REF=5a1a854b0dc9f2141bdc771c555ee60c37950183
RUN git clone https://github.com/open-quantum-safe/liboqs.git /tmp/liboqs \
    && git -C /tmp/liboqs checkout "${LIBOQS_REF}" \
    && cmake -S /tmp/liboqs -B /tmp/liboqs/build -G Ninja \
       -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=ON \
       -DOQS_BUILD_ONLY_LIB=ON -DOQS_USE_OPENSSL=ON \
       '-DOQS_MINIMAL_BUILD=SIG_ml_dsa_44;KEM_ml_kem_768' \
       -DCMAKE_INSTALL_PREFIX=/opt/liboqs \
    && cmake --build /tmp/liboqs/build --parallel 4 \
    && cmake --install /tmp/liboqs/build

WORKDIR /build
COPY requirements.txt .
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

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
