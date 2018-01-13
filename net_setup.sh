#!/bin/bash

shopt -s nullglob

BRIDGE_NAME=sw0

clean() {
    if [[ -e "/sys/class/net/$BRIDGE_NAME" ]]; then
        ip link del $BRIDGE_NAME type bridge || true
    fi

    ip -all netns del || true
    for p in /sys/class/net/veth*a; do
        ip link del dev $(basename $p) type veth
    done

    echo "Done!"
}

set_bridge() {
    ip link add $BRIDGE_NAME type bridge
    ip link set $BRIDGE_NAME up
    ip addr add 172.16.16.1/24 dev $BRIDGE_NAME

    echo Bridge $BRIDGE_NAME created
    ip addr show $BRIDGE_NAME
}

ns_num() {
    ip netns | grep -Po '^net\K[0-9]+' | sort | tail -n1
}

add_ns() {
    if ! [[ -e "/sys/class/net/$BRIDGE_NAME" ]]; then
        clean
        set_bridge
    fi

    num=$(ns_num)
    num=$((num + 1))

    ip netns add net${num}
    ip link add veth${num}a type veth peer name veth${num}b
    ip link set veth${num}b netns net${num}

    ip link set veth${num}a up
    ip link set dev veth${num}a master $BRIDGE_NAME
    ip netns exec net${num} ip link set lo up
    ip netns exec net${num} ip link set veth${num}b up
    ip netns exec net${num} ip addr add 172.16.16.${num}0/24 dev veth${num}b
    ip netns exec net${num} ip route add default via 172.16.16.1

    echo Network namespace net$num created
    ip netns exec net${num} ip addr show veth${num}b
}

if [[ "$1" == "clean" ]]; then
    clean
elif [[ "$1" == "add" ]]; then
    add_ns "$2"
else
    echo "What?"
fi
