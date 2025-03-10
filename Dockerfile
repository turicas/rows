ARG PYTHON_IMAGE="python"
ARG PYTHON_VERSION="3.13"
ARG DEBIAN_VERSION="bookworm"
FROM ${PYTHON_IMAGE}:${PYTHON_VERSION}-slim-${DEBIAN_VERSION}
LABEL org.opencontainers.image.authors="Álvaro Justen <alvarojusten@gmail.com>"
LABEL org.opencontainers.image.url="https://github.com/turicas/rows/"

ENV PYTHONUNBUFFERED=1
WORKDIR /app
VOLUME /data

# Create a non-root user
RUN addgroup --gid ${GID:-1000} python \
  && adduser --disabled-password --gecos "" --home /app --uid ${UID:-1000} --gid ${GID:-1000} python \
  && chown -R python:python /app

# Configure locale (required to run tests)
RUN echo -e 'en_US.UTF-8 UTF-8\npt_BR.UTF-8 UTF-8' > /etc/locale.gen

# Upgrade and install required system packages
RUN apt update \
  && apt upgrade -y \
  && apt install --no-install-recommends -y build-essential libfreetype-dev libmagic1 libmupdf-dev libpq-dev \
                                            libsnappy-dev libxml2-dev libxslt-dev libz-dev locales postgresql-client \
                                            python3-dev wget \
  && apt purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
  && apt clean \
  && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install (if needed) expensive-to-build, big packages and the ones from other indexes (for caching)
RUN --mount=type=cache,target=/var/cache/pip pip install --cache-dir /var/cache/pip -U pip

# Install requirements
COPY --chown=python:python requirements.txt requirements-development.txt /app/
RUN --mount=type=cache,target=/var/cache/pip \
    pip install --cache-dir /var/cache/pip -Ur /app/requirements.txt \
    && pip install --cache-dir /var/cache/pip -Ur /app/requirements-development.txt

# Copy all needed files and set permissions
COPY --chown=python:python . /app/
RUN pip install -e .
USER python
CMD ["rows"]
