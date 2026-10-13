# OpenFlow controller for CSCI 60 Lab 2: os-ken
# (https://opendev.org/openstack/os-ken). Pinned so a future release cannot
# change the lab's behaviour underneath it.
FROM python:3.12-slim
RUN pip install --no-cache-dir os-ken==4.2.2 \
    && python -c "import os_ken; from os_ken.ofproto import ofproto_v1_3"
WORKDIR /lab
CMD ["python3", "sw_tutorial.py"]
