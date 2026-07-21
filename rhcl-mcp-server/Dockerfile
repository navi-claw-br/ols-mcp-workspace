FROM registry.access.redhat.com/ubi9/python-312:latest

USER root

# Download and install oc binary
ADD https://mirror.openshift.com/pub/openshift-v4/clients/oc/latest/linux/oc.tar.gz /tmp/oc.tar.gz
RUN tar -xzf /tmp/oc.tar.gz -C /usr/local/bin/ oc && \
    chmod +x /usr/local/bin/oc && \
    rm -f /tmp/oc.tar.gz && \
    dnf install -y tar gzip && \
    dnf clean all

WORKDIR /app
COPY rhcl_server.py skill.md ./

EXPOSE 8080

USER 1001

CMD ["python3", "/app/rhcl_server.py"]
