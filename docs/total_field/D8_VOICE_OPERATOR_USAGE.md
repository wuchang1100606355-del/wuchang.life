# D8 Voice Operator Usage

This is a text-mode voice operator. It does not access a microphone, does not record audio, and does not store raw audio.

Future STT output can be passed as text:

```bash
python tools/d8_voice_operator.py --text "查狀態"
python tools/d8_voice_operator.py --text "看告警"
python tools/d8_voice_operator.py --text "安全讀取"
python tools/d8_voice_operator.py --interactive
```

Use `--dry-run` to preview routing without calling the console:

```bash
python tools/d8_voice_operator.py --text "查狀態" --dry-run
```

The operator only routes to local D8 console commands. It does not call external STT, external APIs, production services, deploys, or payment/order actions.
