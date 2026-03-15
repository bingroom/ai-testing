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

        # 4. 執行 Reboot 並捕捉斷線
        print("\n--- 準備執行 Reboot ---")
        try:
            # 使用 send_command_timing 因為 reboot 不會返回正常的 prompt
            net_connect.send_command_timing("sudo reboot")
            print("Reboot 指令已發送，設備正在重啟...")
        except Exception as e:
            print(f"預期中的斷線: {e}")

        # 5. 等待重啟並嘗試重新連線 (Polling)
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