#!/usr/bin/env bash
# pingall.sh: ping every host from every other host, like Mininet's pingall.
#
# Containerlab has no pingall of its own. With 20 hosts that is 380 pings, too
# many to type, so this script runs them for you and prints one line per host:
#
#   node1 -> node2 node3 X node5 ...      (X = that host did not answer)
#
# Run it after you deploy, on your VM:
#   sudo bash pingall.sh            # every running Containerlab host
#   sudo bash pingall.sh topo       # only the hosts of the lab named "topo"
#
# Each pair gets up to 5 pings, and counts as reachable if any one answers.
# On a link with packet loss (netem "loss 10%") a single ping can fail even
# when the network is fine; the extra tries keep that from showing up as an X.
# An X that stays after you run it again means a real problem.
#
# A host with no address of its own on the lab's cables shows as X everywhere.
#
# The script only reads your network and sends pings. It changes nothing.
# All hosts ping at the same time, so it takes seconds, not minutes.

lab="$1"
filter="label=containerlab"
[ -n "$lab" ] && filter="label=containerlab=$lab"

hosts=$(docker ps --filter "$filter" --format '{{.Names}}' | sort -V)
if [ -z "$hosts" ]; then
    echo "No Containerlab hosts are running${lab:+ in lab \"$lab\"}. Deploy first." >&2
    exit 1
fi

# Each host's first IPv4 address on the lab's own cables, as "name=address"
# pairs. Addresses Docker gave the host (Containerlab's management network,
# 172.20.20.x unless you leave out "network-mode: none") are skipped: pings
# over that network would succeed even if your cables and switches were wrong.
targets=""
for h in $hosts; do
    mgmt=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}} {{end}}' "$h" 2>/dev/null)
    a=$(docker exec "$h" ip -4 -o addr show scope global 2>/dev/null \
        | awk -v skip=" $mgmt " '{split($4, p, "/"); if (index(skip, " " p[1] " ") == 0) {print p[1]; exit}}')
    targets="$targets $h=${a:-none}"
done

# Runs inside one host: ping every other host, print its name or X.
probe='
for t in $TARGETS; do
    name=${t%%=*}; ip=${t#*=}
    [ "$name" = "$SELF" ] && continue
    ok=0
    if [ "$ip" != none ]; then
        for try in 1 2 3 4 5; do
            ping -c1 -W1 "$ip" >/dev/null 2>&1 && { ok=1; break; }
        done
    fi
    [ $ok = 1 ] && printf " %s" "$name" || printf " X"
done
'

out=$(mktemp -d)
for h in $hosts; do
    docker exec -e SELF="$h" -e TARGETS="$targets" "$h" sh -c "$probe" \
        > "$out/$h" 2>/dev/null &
done
wait

echo "*** Ping: testing ping reachability"
sent=0; lost=0
for h in $hosts; do
    line=$(cat "$out/$h")
    echo "$h ->$line"
    for w in $line; do
        sent=$((sent + 1))
        [ "$w" = X ] && lost=$((lost + 1))
    done
done
rm -rf "$out"
echo "*** Results: $lost of $sent pings failed ($((sent - lost))/$sent received)"
[ "$lost" -eq 0 ]
