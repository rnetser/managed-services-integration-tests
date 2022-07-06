FROM quay.io/centos/centos:stream8

RUN yum -y install epel-release
RUN yum -y install --setopt=skip_missing_names_on_install=False \
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

RUN : \
  && curl https://mirror.openshift.com/pub/openshift-v4/x86_64/clients/ocp/stable/openshift-client-linux.tar.gz -o /tmp/oc.tar.gz \
  && tar -xvf /tmp/oc.tar.gz --directory=/usr/bin/ \
  && rm -rf /usr/local/bin/README.md /tmp/oc.tar.gz \
  && :

RUN pip3 install pipenv

COPY / managed-services-integration-tests/
WORKDIR managed-services-integration-tests

ENV OPENSHIFT_PYTHON_WRAPPER_LOG_LEVEL=DEBUG
ENV PIPENV_VENV_IN_PROJECT=1
RUN pipenv install --skip-lock
RUN pipenv run pip freeze

ENTRYPOINT ["pipenv", "run", "pytest"]
CMD ["--collect-only"]
