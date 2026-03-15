#!/bin/bash
# SONiC QEMU 啟動腳本
# 參考: https://github.com/sonic-net/SONiC/wiki/SONiC-on-virtual-machine-for-Windows
#
# 網路介面配置說明:
#   net0 (eth0) → Management0  — SSH 管理介面，hostfwd 轉發 host:2222 → VM:22
#   net1 (eth1) → Ethernet0    — 資料介面 #1，SLIRP gateway: 10.1.0.2/24
#   net2 (eth2) → Ethernet4    — 資料介面 #2，SLIRP gateway: 10.2.0.2/24
#   net3 (eth3) → Ethernet8    — 資料介面 #3，SLIRP gateway: 10.3.0.2/24
#   net4 (eth4) → Ethernet12   — 資料介面 #4，SLIRP gateway: 10.4.0.2/24
#
# 使用方式:
#   chmod +x start_sonic.sh
#   ./start_sonic.sh [sonic-vs.img 路徑]

SONIC_IMG="${1:-./sonic-vs.img}"

if [ ! -f "$SONIC_IMG" ]; then
    echo "錯誤: 找不到 SONiC 映像檔: $SONIC_IMG"
    echo "用法: $0 [sonic-vs.img 路徑]"
    exit 1
fi

echo "啟動 SONiC QEMU (映像: $SONIC_IMG)..."
echo "SSH 連線: ssh -p 2222 admin@127.0.0.1"
echo "Serial console: telnet 127.0.0.1 5001"
echo ""

qemu-system-x86_64 \
    -name sonic-vs \
    -m 4096M \
    -smp cpus=4 \
    -drive file="$SONIC_IMG",index=0,media=disk,id=drive0 \
    -serial telnet:127.0.0.1:5001,server,nowait \
    -monitor tcp:127.0.0.1:44001,server,nowait \
    -display none \
    \
    -device e1000,netdev=net0 \
    -netdev user,id=net0,hostfwd=tcp::2222-:22 \
    \
    -device e1000,netdev=net1 \
    -netdev user,id=net1,net=10.1.0.0/24,host=10.1.0.2 \
    \
    -device e1000,netdev=net2 \
    -netdev user,id=net2,net=10.2.0.0/24,host=10.2.0.2 \
    \
    -device e1000,netdev=net3 \
    -netdev user,id=net3,net=10.3.0.0/24,host=10.3.0.2 \
    \
    -device e1000,netdev=net4 \
    -netdev user,id=net4,net=10.4.0.0/24,host=10.4.0.2
