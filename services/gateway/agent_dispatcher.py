def choose_agent(prompt):

    text = prompt.lower()

    if any(x in text for x in [

        "voice",
        "audio",
        "speak",
        "microphone"
    ]):

        return "voice_tool"

    if any(x in text for x in [

        "safe",
        "security",
        "sandbox",
        "risk"
    ]):

        return "taiji_claw_safe"

    if any(x in text for x in [

        "recover",
        "resilience",
        "failover"
    ]):

        return "resilience_adapter"

    return "ollama"
