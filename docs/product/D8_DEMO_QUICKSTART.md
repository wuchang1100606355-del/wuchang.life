# D8 Demo Quickstart

```bash
cd /home/taiji_admin/Taiji_Hub

tools/d8_product_demo_launcher.sh status
tools/d8_product_demo_launcher.sh doctor
tools/d8_product_demo_launcher.sh smoke-test
tools/d8_product_demo_launcher.sh voice-demo --text "查狀態"
tools/d8_product_demo_launcher.sh pos-bridge-demo
tools/d8_product_demo_launcher.sh dashboard --host 127.0.0.1 --port 8787 --timeout 3
tools/d8_product_demo_launcher.sh package
tools/d8_product_demo_launcher.sh seal
```

The dashboard binds to loopback only. The bridge is read-only. The voice operator accepts text and does not record audio.
