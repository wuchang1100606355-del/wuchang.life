class ExecutionBridge:
    def execute_packet(self, route):
        if route == "cloud":
            return {"exec": "cloud_llm", "node": "external_cloud"}

        if route == "ollama":
            return {"exec": "local_llm", "node": "ollama_runtime"}

        if route == "local":
            return {"exec": "local_runtime", "node": "taiji01"}

        return {"exec": "fallback_local", "node": "taiji01"}
