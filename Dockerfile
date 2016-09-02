FROM	debian
MAINTAINER	Álvaro Justen <https://github.com/turicas>

# install system dependencies
RUN apt-get update
RUN apt-get install --no-install-recommends -y build-essential git locales \
                                               python-dev python-lxml \
                                               python-pip python-snappy \
                                               python-thrift && \
    apt-get clean

#thrift (used by parquet plugin) is the only which needs build-essential and
#python-dev to be installed (installing python-thrift doesn't do the job).

#You can build other Python libraries from source by installing:
#  libsnappy-dev libxml2-dev libxslt-dev libz-dev
#and not installing:
#  python-lxml python-snappy

# configure locale (needed to run tests)
RUN echo 'en_US.UTF-8 UTF-8' > /etc/locale.gen
RUN echo 'pt_BR.UTF-8 UTF-8' >> /etc/locale.gen
RUN /usr/sbin/locale-gen

# clone the repository and install Python dependencies
RUN git clone https://github.com/turicas/rows.git ~/rows
RUN cd ~/rows && pip install -r requirements-development.txt && \
    rm -rf ~/.cache/pip/
RUN cd ~/rows && pip install -e .
