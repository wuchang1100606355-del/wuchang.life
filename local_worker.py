import os, time, json, subprocess

BASE = "/tmp/mnt/usb_big/taiji/queue"

while True:
    inbox = os.listdir(f"{BASE}/inbox")
    if not inbox:
        time.sleep(2)
        continue

    task = inbox[0]

    os.rename(f"{BASE}/inbox/{task}", f"{BASE}/processing/{task}")

    with open(f"{BASE}/processing/{task}") as f:
        data = json.load(f)

    cmd = data.get("cmd")

    try:
        out = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT).decode()

        with open(f"{BASE}/done/{task}.out", "w") as f:
            f.write(out)

        os.rename(f"{BASE}/processing/{task}", f"{BASE}/done/{task}")
        print("DONE")

    except Exception as e:
        with open(f"{BASE}/deadletter/{task}.err", "w") as f:
            f.write(str(e))

        os.rename(f"{BASE}/processing/{task}", f"{BASE}/deadletter/{task}")
        print("FAIL")
