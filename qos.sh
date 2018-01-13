#!/bin/bash

iface=$1
bw=$2

tc qdisc del dev $1 root || true

# global bandwidth limit
tc qdisc add dev $1 root handle 1: htb default 16
tc class add dev $1 parent 1: classid 1:1 htb rate ${bw}mbit ceil ${bw}mbit

# SVC enhance layer class
tc class add dev $1 parent 1:1 classid 1:10 htb rate $((bw-1))bit ceil ${bw}mbit prio 0
tc class add dev $1 parent 1:1 classid 1:11 htb rate 512kbit ceil ${bw}mbit prio 1
tc class add dev $1 parent 1:1 classid 1:12 htb rate 256kbit ceil ${bw}mbit prio 2
tc class add dev $1 parent 1:1 classid 1:13 htb rate 128kbit ceil ${bw}mbit prio 3
tc class add dev $1 parent 1:1 classid 1:14 htb rate 64kbit ceil ${bw}mbit prio 4
tc class add dev $1 parent 1:1 classid 1:15 htb rate 32kbit ceil ${bw}mbit prio 5
tc class add dev $1 parent 1:1 classid 1:16 htb rate 32kbit ceil ${bw}mbit prio 6

# optionally attach SFQ below each class
tc qdisc add dev $1 parent 1:10 handle 100: sfq
tc qdisc add dev $1 parent 1:11 handle 110: sfq
tc qdisc add dev $1 parent 1:12 handle 120: sfq
tc qdisc add dev $1 parent 1:13 handle 130: sfq
tc qdisc add dev $1 parent 1:14 handle 140: sfq
tc qdisc add dev $1 parent 1:15 handle 150: sfq
tc qdisc add dev $1 parent 1:16 handle 160: sfq

# match each layer according to TOS field
tc filter add dev $1 parent 1:0 protocol ip prio 1 u32 match ip protocol 0x6 0xff flowid 1:10
tc filter add dev $1 parent 1:0 protocol ip prio 1 u32 match ip tos 0x60 0xff flowid 1:11
tc filter add dev $1 parent 1:0 protocol ip prio 1 u32 match ip tos 0x50 0xff flowid 1:12
tc filter add dev $1 parent 1:0 protocol ip prio 1 u32 match ip tos 0x40 0xff flowid 1:13
tc filter add dev $1 parent 1:0 protocol ip prio 1 u32 match ip tos 0x30 0xff flowid 1:14
tc filter add dev $1 parent 1:0 protocol ip prio 1 u32 match ip tos 0x20 0xff flowid 1:15
tc filter add dev $1 parent 1:0 protocol ip prio 1 u32 match ip tos 0x10 0xff flowid 1:16
