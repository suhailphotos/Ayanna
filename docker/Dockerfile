FROM python:3.11-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      build-essential \
      libpq-dev \
      wget \
      ffmpeg \
      git \
      curl \
      gpg \
      apt-transport-https \
      ca-certificates && \
    # Download the PostgreSQL signing key and convert to .gpg (IMPORTANT!) \
    wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | \
      gpg --dearmor > /usr/share/keyrings/postgresql-archive-keyring.gpg && \
    # Use 'signed-by' with the new key file \
    echo "deb [signed-by=/usr/share/keyrings/postgresql-archive-keyring.gpg] http://apt.postgresql.org/pub/repos/apt/ bookworm-pgdg main" > /etc/apt/sources.list.d/pgdg.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends postgresql-client-16 && \
    # 1Password CLI setup (unchanged) \
    curl -sS https://downloads.1password.com/linux/keys/1password.asc | \
      gpg --dearmor --output /usr/share/keyrings/1password-archive-keyring.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/1password-archive-keyring.gpg] https://downloads.1password.com/linux/debian/$(dpkg --print-architecture) stable main" \
      > /etc/apt/sources.list.d/1password.list && \
    mkdir -p /etc/debsig/policies/AC2D62742012EA22/ && \
    curl -sS https://downloads.1password.com/linux/debian/debsig/1password.pol | \
      tee /etc/debsig/policies/AC2D62742012EA22/1password.pol && \
    mkdir -p /usr/share/debsig/keyrings/AC2D62742012EA22 && \
    curl -sS https://downloads.1password.com/linux/keys/1password.asc | \
      gpg --dearmor --output /usr/share/debsig/keyrings/AC2D62742012EA22/debsig.gpg && \
    apt-get update && \
    apt-get install -y --no-install-recommends 1password-cli && \
    rm -rf /var/lib/apt/lists/*

# Poetry install
RUN pip install poetry

# Set workdir
WORKDIR /app

# Copy oauthManager credential files
RUN mkdir -p /root/.config/oauthmanager
COPY docker/creds_config.json /root/.config/oauthmanager/creds_config.json


# Copy poetry files
COPY pyproject.toml poetry.lock ./
COPY README.md LICENSE ./

# Copy source
COPY src ./src
COPY scripts ./scripts
COPY docker ./docker

# Install deps
RUN poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi

# Set env
ENV PYTHONPATH=/app/src

# (Optional) default command for dev
CMD [ "bash" ]
