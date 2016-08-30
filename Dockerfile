FROM	debian
MAINTAINER	Álvaro Justen <https://github.com/turicas>

# install system dependencies
RUN apt-get update
RUN apt-get install -y git build-essential libsnappy-dev locales python-dev \
                       python-pip && apt-get clean

# configure locale (needed to run tests)
RUN echo 'en_US.UTF-8 UTF-8' > /etc/locale.gen
RUN echo 'pt_BR.UTF-8 UTF-8' >> /etc/locale.gen
RUN /usr/sbin/locale-gen

# clone the repository and install Python dependencies
RUN git clone https://github.com/turicas/rows.git ~/rows
RUN cd ~/rows && pip install -r requirements-development.txt && \
    rm -rf ~/.cache/pip/
RUN cd ~/rows && pip install -e .
