# Post Quantum Relay

An experimental relay accepting ordinary secp256k1 events and nonstandard
ML-DSA-44-signed events. Stroma provides key generation, canonical event hashing,
classical verification and the optional PQ backend. Monstr remains responsible
for the relay server, SQLite storage and subscriptions.

This is not standard NIP-01 interoperability or Stroma's proposed encrypted
envelope. Signatures provide authenticity, not confidentiality: this relay does
not encrypt records or solve harvest-now-decrypt-later exposure.

## Supported format

- Classical keys: 32 bytes; signatures: 64 bytes.
- ML-DSA-44 keys: 1,312 bytes; signatures: 2,420 bytes.
- Keys and signatures are lowercase hex in event JSON.
- The event ID is SHA-256 of the usual canonical event serialization.
- ML-DSA signs the 32-byte event ID with an empty context, retaining the previous
  ML-DSA experiment's signing convention.
- Both classical and PQ validation recompute the event ID before verifying.
- Malformed fields and other key/signature sizes are rejected explicitly.

Falcon-512 is no longer supported for publishing or verification. Existing
database rows are not deleted or migrated; old Falcon rows may still be returned
by historical queries, but are not valid under the new verifier. Use a separate
database if a clean ML-DSA-only experiment is needed.

## Dependencies

Python 3.11–3.13 is required by Stroma. The old Python 3.10 virtual environment
must not be reused.

Poetry 1.8 or newer manages dependencies using `pyproject.toml` and the committed
`poetry.lock`. This is an application-only project (`package-mode = false`), so
Poetry installs dependencies without packaging the `app` directory. Runtime pins
are preserved from the existing requirements files; development tests are in the
`dev` group. The requirements files remain available for existing pip workflows,
but Poetry and Docker use the lockfile.

Stroma is pinned to commit
`51496fa6094a126311e9ea59ea06081cd8fbf9f7` with its `pq` extra.
That extra pins liboqs-python 0.16.0.2; native liboqs must be 0.16.0.
The application never imports `oqs` or compiles native code at startup.
The Stroma adapter loads only the explicitly configured native library.

## Docker

```sh
docker compose build --progress plain pqrelay
docker compose up -d pqrelay
```

The builder compiles pinned liboqs commit
`5a1a854b0dc9f2141bdc771c555ee60c37950183` (0.16.0), enabling ML-DSA-44
and ML-KEM-768. ML-KEM is required by the fixed Stroma backend but is not used
for relay events. Poetry installs locked runtime dependencies in the builder;
development dependencies and Poetry itself are not copied into the runtime image.
The runtime image contains no compiler or Git client and checks backend loading
during its build.

`PQRELAY_LIBOQS_PATH=/opt/liboqs/lib/liboqs.so` is set in the image.
The relay listens at `ws://localhost:8735`; Compose preserves `./data`.
A missing or incompatible native library prevents startup rather than triggering
a download or algorithm downgrade.

## Local development

First provision native liboqs 0.16.0 explicitly, or use the Docker build above.
Do not overwrite a native installation used by another application without
checking compatibility.

```sh
python3.12 -m venv .venv-pq
source .venv-pq/bin/activate
poetry install
export PQRELAY_LIBOQS_PATH=/absolute/path/to/liboqs.dylib
mkdir -p data
poetry run python app/relay.py
```

Use the appropriate `.so` or `.dll` path on other platforms. In another terminal
with the same environment:

```sh
poetry run python app/nostr.py
```

The demo uses Stroma's acknowledgement-aware publishing. Its local `pqclient`
query helper verifies both signature formats; standard Stroma queries intentionally
accept only classical NIP-01 events. `app/create.py` creates a disposable ML-DSA
event without publishing it.
The older `app/query.py` utility retains Monstr's alias/NIP-04 behavior and is not
a PQ verification boundary.

## Tests

```sh
poetry run pytest -q
```

With `PQRELAY_LIBOQS_PATH` set, this includes real ML-DSA operations and a
temporary local relay/SQLite publish-and-query test. Without it, native tests
skip while classical and malformed-input checks run. Tests never use the
existing relay database or wallet keys.

For runtime dependencies only, use `poetry install --only main`. After changing
dependencies, regenerate and commit `poetry.lock` and keep the pip compatibility
files synchronized. Installing with Poetry does not install or compile native
liboqs; provision it separately or use Docker.

This remains unaudited experimental software. Passing tests is not a production
security claim, and a signed plaintext record is still publicly readable.
