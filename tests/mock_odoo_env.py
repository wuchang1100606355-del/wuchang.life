import sys
from unittest.mock import MagicMock

# 強制攔截所有對 odoo 的 import 呼叫，防止宿主機崩潰
sys.modules['odoo'] = MagicMock()
sys.modules['odoo.models'] = MagicMock()
sys.modules['odoo.fields'] = MagicMock()
sys.modules['odoo.exceptions'] = MagicMock()
