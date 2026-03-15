import time
from netmiko import ConnectHandler, NetmikoTimeoutException, NetmikoAuthenticationException

# 設備連線資訊 (透過 QEMU port forwarding)
sonic_device = {
    'device_type': 'linux',  # SONiC 底層是 Linux
    'host': '127.0.0.1',
    'username': 'admin',
    'password': 'YourPaSsWoRd',
    'port': 2222,
    'global_delay_factor': 2, # 增加延遲容忍度，虛擬機通常較慢
}

# QEMU 資料介面對應的 SONiC 介面名稱及預計配置的 IP
# eth0→Management0 (SSH), eth1→Ethernet0, eth2→Ethernet4, eth3→Ethernet8, eth4→Ethernet12
INTERFACE_IP_MAP = {
    'Ethernet0':  '10.1.0.1/24',
    'Ethernet4':  '10.2.0.1/24',
    'Ethernet8':  '10.3.0.1/24',
    'Ethernet12': '10.4.0.1/24',
}

# QEMU user-mode 各介面的 SLIRP gateway (可 ping 用於驗證連通性)
GATEWAY_MAP = {
    'Ethernet0':  '10.1.0.2',
    'Ethernet4':  '10.2.0.2',
    'Ethernet8':  '10.3.0.2',
    'Ethernet12': '10.4.0.2',
}


def run_interface_sanity(net_connect):
    """介面 Sanity Check：確認介面存在、配置 IP、驗證連通性"""

    print("\n=== 介面 Sanity Check ===")

    # 1. 列出所有介面狀態
    print("\n--- 介面狀態總覽 ---")
    intf_status = net_connect.send_command("show interfaces status")
    print(intf_status)

    # 2. 確認目標介面皆存在
    print("\n--- 確認目標介面存在 ---")
    missing = []
    for intf in INTERFACE_IP_MAP:
        if intf in intf_status:
            print(f"  [OK] {intf} 已偵測到")
        else:
            print(f"  [FAIL] {intf} 未找到！")
            missing.append(intf)
    if missing:
        print(f"警告: 以下介面未偵測到: {missing}")
        print("請確認 QEMU 已加入對應的 -netdev/-device 參數。")

    # 3. 配置 IP 地址 (若尚未設定)
    print("\n--- 配置介面 IP ---")
    for intf, ip_prefix in INTERFACE_IP_MAP.items():
        if intf in missing:
            continue
        # 先啟用介面
        net_connect.send_command_timing(
            f"sudo ip link set {intf} up", strip_prompt=False, strip_command=False
        )
        # 清除舊 IP 再配置 (避免重複)
        net_connect.send_command_timing(
            f"sudo ip addr flush dev {intf}", strip_prompt=False, strip_command=False
        )
        net_connect.send_command_timing(
            f"sudo ip addr add {ip_prefix} dev {intf}", strip_prompt=False, strip_command=False
        )
        print(f"  已設定 {intf}: {ip_prefix}")

    # 4. 顯示配置後的 IP 介面清單
    print("\n--- 配置後的 IP 介面清單 ---")
    ip_intf = net_connect.send_command("show ip interfaces")
    print(ip_intf)

    # 5. Ping SLIRP gateway 驗證各介面連通性
    print("\n--- Ping SLIRP Gateway 連通性測試 ---")
    for intf, gw in GATEWAY_MAP.items():
        if intf in missing:
            print(f"  [SKIP] {intf} 介面不存在，跳過 ping")
            continue
        result = net_connect.send_command(
            f"ping -c 3 -W 2 -I {intf} {gw}", read_timeout=15
        )
        if "3 received" in result or "3 packets received" in result:
            print(f"  [OK]   {intf} → {gw} ping 成功")
        elif "1 received" in result or "2 received" in result:
            print(f"  [WARN] {intf} → {gw} 部分封包遺失")
        else:
            print(f"  [FAIL] {intf} → {gw} ping 失敗")
            print(f"         {result.splitlines()[-1] if result.strip() else '(無輸出)'}")

    # 6. 顯示路由表
    print("\n--- 路由表 ---")
    route = net_connect.send_command("show ip route")
    print(route if route.strip() else net_connect.send_command("ip route"))


def run_smoke_test():
    try:
        print("連線至 SONiC switch...")
        net_connect = ConnectHandler(**sonic_device)
        print("連線成功！\n")

        # 1. 檢查 Docker 狀態 (SONiC 的核心服務都在 Docker 內)
        print("--- Docker 狀態檢查 ---")
        docker_output = net_connect.send_command("sudo docker ps")
        print(docker_output)

        # 2. 獲取預設配置
        print("\n--- 獲取 Running Configuration ---")
        config_output = net_connect.send_command("show runningconfiguration all")
        # 如果指令太長，只印出前 500 個字元作為 Sanity Check
        print(config_output[:500] + "\n...[略]...")

        # 3. 獲取最近的 Syslog
        print("\n--- 獲取最新 20 筆 Syslog ---")
        syslog_output = net_connect.send_command("sudo tail -n 20 /var/log/syslog")
        print(syslog_output)

        # 4. 介面 Sanity Check (新增)
        run_interface_sanity(net_connect)

        # 5. 執行 Reboot 並捕捉斷線
        print("\n--- 準備執行 Reboot ---")
        try:
            # 使用 send_command_timing 因為 reboot 不會返回正常的 prompt
            net_connect.send_command_timing("sudo reboot")
            print("Reboot 指令已發送，設備正在重啟...")
        except Exception as e:
            print(f"預期中的斷線: {e}")

        # 6. 等待重啟並嘗試重新連線 (Polling)
        print("等待設備重啟 (60秒後開始重試連線)...")
        time.sleep(60)
        reconnected = False
        for i in range(10):  # 重試 10 次
            try:
                print(f"嘗試重新連線... (第 {i+1} 次)")
                net_connect = ConnectHandler(**sonic_device)
                print("重新連線成功！設備已完成重啟。")
                reconnected = True
                break
            except (NetmikoTimeoutException, NetmikoAuthenticationException):
                time.sleep(15) # 每次失敗等待 15 秒再試

        if not reconnected:
            print("無法重新連線，請檢查 QEMU 狀態。")
        else:
            # 驗證重啟後的 Uptime
            uptime = net_connect.send_command("uptime")
            print(f"設備 Uptime: {uptime}")
            net_connect.disconnect()

    except Exception as e:
        print(f"連線或執行過程中發生錯誤: {e}")

if __name__ == "__main__":
    run_smoke_test()
