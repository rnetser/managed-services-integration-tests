FROM quay.io/centos/centos:stream9

RUN dnf -y install epel-release dnf-plugins-core && \
    dnf config-manager --add-repo https://rpm.releases.hashicorp.com/RHEL/hashicorp.repo && \
    dnf -y install --setopt=skip_missing_names_on_install=False \
    python3-pip \
    python3-devel \
    procps-ng \
    rsync \
    gcc \
    git \
    libcurl-devel \
    libxslt-devel \
    libxml2-devel \
    openssl-devel \
    terraform

COPY / managed-services-integration-tests/
WORKDIR managed-services-integration-tests

RUN curl https://mirror.openshift.com/pub/openshift-v4/clients/rosa/latest/rosa-linux.tar.gz -o /tmp/rosa.tar.gz && \
    tar -xvf /tmp/rosa.tar.gz --directory=/usr/bin/ && \
    rm -rf /tmp/oc.tar.gz && \
    python3 -m pip install pip --upgrade && \
    python3 -m pip install poetry && \
    poetry config cache-dir /managed-services-integration-tests && \
    poetry config virtualenvs.in-project true && \
    poetry config installer.max-workers 10 && \
    poetry config --list && \
    poetry env remove --all && \
    poetry install && \
    poetry export --without-hashes -n && \
    poetry show

ENV OPENSHIFT_PYTHON_WRAPPER_LOG_LEVEL=DEBUG

ENTRYPOINT ["poetry", "run", "pytest"]
CMD ["--collect-only"]
