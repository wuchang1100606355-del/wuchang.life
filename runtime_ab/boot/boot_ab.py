from runtime_ab.bridge.ab_bridge import ABBridge

def main():
    os = ABBridge()

    packet = {
        "intent_type": "test",
        "target": "taiji01",
        "action": "run",
        "payload": {}
    }

    result = os.dispatch(packet)

    print("=== A/B OS RESULT ===")
    print(result)

if __name__ == "__main__":
    main()
