class W7TPNodeRegistry:
    def __init__(self):
        self.nodes = {
            "local": "taiji01",
            "cloud": "external_cloud_llm",
            "ollama": "local_ollama",
        }

    def resolve(self, route):
        if "cloud" in str(route):
            return "cloud"

        if "voice" in str(route):
            return "local"

        if "local" in str(route):
            return "local"

        if "llm" in str(route):
            return "ollama"

        return "local"
