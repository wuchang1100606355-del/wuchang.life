"""Evidence-gated native ADI candidate interfaces.

This package is not a second Total Field runtime.  Native mathematical
functions remain fail-closed until Founder source evidence confirms them.
"""

from .errors import NativeRuleEvidenceMissing
from .models import StatePacket8D

__all__ = ["NativeRuleEvidenceMissing", "StatePacket8D"]
