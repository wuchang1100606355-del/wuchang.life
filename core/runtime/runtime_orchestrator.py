# -*- coding: utf-8 -*-
import subprocess, requests, time

class RuntimeOrchestrator:
    def alive(self, url, timeout=1):
        try:
            r = requests.get(url, timeout=timeout)
            return r.status_code < 500
        except Exception:
            return False

    def ensure_claw(self):
        if self.alive("http://localhost:9004/"):
            return True
        subprocess.run("docker start taiji_claw >/dev/null 2>&1 || true", shell=True)
        time.sleep(2)
        return self.alive("http://localhost:9004/")

    def state(self):
        return {
            "gateway": self.alive("http://localhost:8081/health"),
            "claw": self.ensure_claw(),
            "ollama": self.alive("http://localhost:11434/api/tags")
        }
