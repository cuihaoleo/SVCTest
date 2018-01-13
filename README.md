# SimpleSVC

## Encode SimpleSVC video

Command:
```
python3 jpsvc.py data/original.flv -t result/raw.tcp -u result/raw.udp
```

where `data/original.flv` is the input video for encoding, and `result/raw.tcp` and `result/raw.udp` are SimpleSVC base layer and enhance layer, respectively.

Note: The command takes very long time to encode. On my computer, it takes half an hour to encode `original.flv`. If you don't want to wait, simply copy `data/raw.tcp` and `data/raw.udp` to `result/` folder to continue next step.

== Network setup ==

Note: You must use a recent Linux system (eg: Ubuntu 16.04 or later), and have root permission.

Create two network namespace for network simulation:
```
sudo bash net_setup.sh add
sudo bash net_setup.sh add
```

Repeat the command to create more. But two is enough for simple experiments. We will use net1 as server and net2 as client.

Setup QoS for client. You can skip this step but then no packet drop:

```
# following command set bandwidth of net2 to 25
sudo bash qos.sh veth2a 25
```

## Video transfer

You need two terminals for this step.

In the first terminal, run server program in net1:
```
sudo ip netns exec net1 python3 sender.py -t result/raw.tcp -u result/raw.udp -b 0.0.0.0:5554
```

In the second terminal, run client program in net2:
```
sudo ip netns exec net2 python3 receiver.py -t result/recv.tcp -u result/recv.udp 172.16.16.10:5554
```

When you see `INFO:SVCServer:EOF in TCP file at XXX bytes`, then transfer is over. Sometimes the program won't exit automatically. Simply Ctrl-C to exit.

You can check the size of your received SimpleSVC video files:
```
$ ls -al result/*.{tcp,udp}
-rw-r--r-- 1 cuihao cuihao 75675529 Jan 12 21:23 data/raw.tcp
-rw-r--r-- 1 cuihao cuihao 95407642 Jan 12 21:23 data/raw.udp
-rw-r--r-- 1 root   root   75675529 Jan 13 10:30 data/recv.tcp
-rw-r--r-- 1 root   root   22974740 Jan 13 10:30 data/recv.udp
```

`recv.udp` should be smaller than `raw.udp` because some layers are dropped. `recv.tcp` and `raw.tcp` should be the same if no base layer data are dropped. Note that my decoder cannot decode broken base layer.

## Decode SimpleSVC video

Run following command to convert received SimpleSVC video to raw Y8 format AVI:
```
python3 jpsvc_dec.py -t result/recv.tcp -u result/recv.udp result/dec.avi
```

If you want to watch actual video, set `-b N` parameter:
```
python3 jpsvc_dec.py -t result/recv.tcp -u result/recv.udp -b 10 result/dec.avi
```

To decode base layer only, omit `-u` parameter:
```
python3 jpsvc_dec.py -t result/recv.tcp -b 10 result/dec_base.avi
```

## Compare videos (MSE/PSNR)

I write a simple python scripts for this. If you want to reproduce the data, run:
```
python3 compare_video.py result/dec.avi data/original.flv
```

The script will compare every frame in `result/dec.avi` with `data/original.flv`, and output MSE/PSNR.
