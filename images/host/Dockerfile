# Host image for CSCI 60 labs: a small Linux box with the usual tools.
FROM alpine:3.22
RUN apk add --no-cache bash iproute2 iproute2-tc net-tools iputils \
        tcpdump iperf iperf3 curl netcat-openbsd busybox-extras \
        traceroute ethtool python3 \
    && echo 'PS1="\\h# "' > /root/.bashrc
CMD ["sleep", "infinity"]
