FROM ubuntu:24.04

ARG SPEC_URL
ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash ca-certificates curl wget sudo git gh \
    build-essential cmake ninja-build pkg-config ccache \
    unzip zip xz-utils bzip2 pigz pbzip2 tar \
    software-properties-common ansifilter python3 \
    && rm -rf /var/lib/apt/lists/*

COPY tools/spec.py /usr/local/bin/atcoder-spec
COPY tools/run_submission.py /usr/local/bin/run-submission
RUN chmod +x /usr/local/bin/atcoder-spec /usr/local/bin/run-submission \
    && test -n "$SPEC_URL" \
    && apt-get update \
    && atcoder-spec install "$SPEC_URL" \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
    
WORKDIR /opt/atcoder-toolchain
ENTRYPOINT ["/usr/local/bin/run-submission"]
