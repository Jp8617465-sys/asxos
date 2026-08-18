# asxos Cloud Agent base image.
# Ubuntu 24.04 ships Python 3.12 (the version pinned by .python-version / pyproject).
# System packages only — Python deps are installed from the checked-out source by
# .cursor/install.sh, which runs the same `pip install -e ".[ml,dev]"` as CI's
# full-check workflow, so this image never pins the dependency set.
FROM ubuntu:24.04

# TZ=UTC is load-bearing, not cosmetic. 25 files under jobs/ derive their `as_of`
# partition key from a NAIVE `date.today()`, which reads the container's local zone
# (e.g. jobs/sync_prices.py, jobs/snapshot_portfolio.py, jobs/detect_theme_stages.py).
# CI and every cron run UTC. Under Australia/Sydney (UTC+10/+11) the 20:30 UTC
# daily-brief instant is already the NEXT calendar day locally, so a job run manually
# from this container against a real DATABASE_URL would write next-day `as_of` rows
# into the same keyspace as production. Keep this UTC.
ENV DEBIAN_FRONTEND=noninteractive \
    TZ=UTC \
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
