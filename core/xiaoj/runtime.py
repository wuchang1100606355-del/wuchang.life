from core.xiaoj.reconstruction.intent_reconstruction import (
    IntentReconstructionEngine
)

class XiaoJRuntime:

    def __init__(self):
        self.engine = IntentReconstructionEngine()

    def run(self,text:str):
        return self.engine.run(text)
