FROM quay.io/centos/centos:stream9

RUN yum -y install epel-release && \
    yum -y install --setopt=skip_missing_names_on_install=False \
    python3-pip \
    python3-devel \
    procps-ng \
    rsync \
    gcc \
    git \
    libcurl-devel \
    libxslt-devel \
    libxml2-devel \
    openssl-devel

COPY / managed-services-integration-tests/
WORKDIR managed-services-integration-tests

RUN curl https://mirror.openshift.com/pub/openshift-v4/clients/oc/latest/linux/oc.tar.gz -o /tmp/oc.tar.gz && \
    tar -xvf /tmp/oc.tar.gz --directory=/usr/bin/ && \
    rm -rf /usr/local/bin/README.md /tmp/oc.tar.gz && \
    python3 -m pip install pip --upgrade && \
    python3 -m pip install poetry && \
    poetry config cache-dir /managed-services-integration-tests && \
    poetry config virtualenvs.in-project true && \
    poetry config --list && \
    poetry env remove --all && \
    poetry install && \
    poetry export --without-hashes -n && \
    poetry show

ENV OPENSHIFT_PYTHON_WRAPPER_LOG_LEVEL=DEBUG

ENTRYPOINT ["poetry", "run", "pytest"]
CMD ["--collect-only"]
