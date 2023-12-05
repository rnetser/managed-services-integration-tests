FROM fedora:39

RUN dnf -y install dnf-plugins-core && \
    dnf config-manager --add-repo https://rpm.releases.hashicorp.com/fedora/hashicorp.repo && \
    dnf config-manager --add-repo https://cli.github.com/packages/rpm/gh-cli.repo && \
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
    terraform \
    vim \
    gh && \
    dnf clean all && \
    rm -rf /var/cache/yum

RUN useradd -ms /bin/bash openshift-cli-installer
ENV USER_HOME=/home/openshift-cli-installer
ENV PATH="${PATH}:$USER_HOME/.local/bin"

# GH_HOST is needed as a workaround to access the repository in GitHub
# https://github.com/cli/cli/issues/2680#issuecomment-1345491083
RUN GH_HOST=dummy gh -R https://github.com/openshift/rosa release download -p 'rosa-linux-amd64' -O /usr/bin/rosa && \
    chmod +x /usr/bin/rosa

COPY . /managed-services-integration-tests/
WORKDIR /managed-services-integration-tests
RUN ln -s /usr/bin/python3 /usr/bin/python
RUN chown -R openshift-cli-installer:openshift-cli-installer /managed-services-integration-tests

RUN python3 -m pip install pip --upgrade && \
    python3 -m pip install poetry

USER openshift-cli-installer

RUN poetry config cache-dir /managed-services-integration-tests && \
    poetry config virtualenvs.in-project true && \
    poetry config installer.max-workers 10 && \
    poetry config --list && \
    poetry install && \
    poetry show && \
    find /managed-services-integration-tests/ -type d -name "__pycache__" -print0 | xargs -0 rm -rfv

ENV OPENSHIFT_PYTHON_WRAPPER_LOG_LEVEL=DEBUG

ENTRYPOINT ["poetry", "run", "pytest"]
CMD ["--collect-only"]
