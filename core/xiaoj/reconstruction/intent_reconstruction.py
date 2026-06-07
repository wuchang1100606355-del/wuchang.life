from core.xiaoj.discovery.intent_discovery import IntentDiscovery
from core.xiaoj.completion.gap_analysis import GapAnalysis
from core.xiaoj.completion.intent_completion import IntentCompletion
from core.xiaoj.redteam.redteam_check import RedTeamCheck
from core.xiaoj.compiler.tensor_compiler import TensorCompiler

class IntentReconstructionEngine:

    def run(self,text):

        discovery=IntentDiscovery()

        result=discovery.discover(text)

        payload={
            "intent":text
        }

        missing=GapAnalysis().analyze(payload)

        payload=IntentCompletion().complete(payload)

        redteam=RedTeamCheck().validate(payload)

        tensor=TensorCompiler().compile(payload)

        return {
            "discovery":result,
            "missing":missing,
            "redteam":redteam,
            "tensor":tensor
        }
