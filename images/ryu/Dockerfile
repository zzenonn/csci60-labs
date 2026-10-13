# Ryu SDN controller for CSCI 60 labs.
# Ryu 4.34 is the last release. It needs Python <= 3.9, setuptools < 58
# and eventlet 0.30.2, which is why it runs in a container rather than on
# the server's own Python.
FROM python:3.9-slim
RUN pip install --no-cache-dir "setuptools<58" wheel \
    && pip install --no-cache-dir eventlet==0.30.2 ryu==4.34 \
    && ryu-manager --version
WORKDIR /apps
CMD ["ryu-manager", "--help"]
