#!/bin/bash

iface=$1
bw=$2
udp_bw=$3

tc qdisc del dev $1 root
tc qdisc add dev $1 root handle 1: htb default 11
tc class add dev $1 parent 1: classid 1:1 htb rate ${bw}mbit ceil ${bw}mbit
tc class add dev $1 parent 1:1 classid 1:10 htb rate $((bw-udp_bw))bit ceil ${bw}mbit prio 0
tc class add dev $1 parent 1:1 classid 1:11 htb rate ${udp_bw}mbit ceil ${bw}mbit prio 1
tc qdisc add dev $1 parent 1:10 handle 110: sfq
tc qdisc add dev $1 parent 1:11 handle 120: sfq
tc filter add dev $1 parent 1:0 protocol ip prio 1 u32 match ip protocol 0x6 0xff flowid 1:10
