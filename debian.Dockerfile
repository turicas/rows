FROM debian:testing
WORKDIR /app
VOLUME /data

RUN apt update && \
    apt upgrade -y && \
    apt install --no-install-recommends -y adduser ca-certificates git python-is-python3 vim && \
    apt clean

# Create a non-root user
RUN addgroup --gid ${GID:-1000} python \
  && adduser --disabled-password --gecos "" --home /app --uid ${UID:-1000} --gid ${GID:-1000} python \
  && chown -R python:python /app

RUN git clone https://salsa.debian.org/debian/rows.git /opt/debian-rows && \
    apt-get build-dep -y /opt/debian-rows && \
    apt clean

USER python
