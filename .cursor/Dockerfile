# asxos Cloud Agent base image.
# Ubuntu 24.04 ships Python 3.12 (the version pinned by .python-version / pyproject).
# System packages only — Python deps are installed from the checked-out source by
# .cursor/install.sh so they track pyproject.toml + uv.lock, not this image.
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive \
    TZ=Australia/Sydney \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python3.12 \
        python3.12-venv \
        python3.12-dev \
        build-essential \
        libpq-dev \
        make \
        git \
        curl \
        ca-certificates \
        tzdata \
    # Makefile's PY default is /usr/local/bin/python3.12; alias it so `make` targets work.
    && ln -sf /usr/bin/python3.12 /usr/local/bin/python3.12 \
    && rm -rf /var/lib/apt/lists/*

# ubuntu:24.04 ships a non-root `ubuntu` user (uid 1000); the environment runs as it.
USER ubuntu
