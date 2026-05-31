from checkpoint_manager import restore_checkpoint

state = restore_checkpoint()

if state:
    print("[✓] Runtime hydration success")
    print(state)
else:
    print("[!] No checkpoint available")
