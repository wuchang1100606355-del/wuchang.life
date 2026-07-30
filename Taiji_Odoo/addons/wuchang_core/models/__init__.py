from . import wuchang_task_force
from . import ai_guard
from . import ai_memory
from . import res_partner
from . import ai_index_mixin
from . import task
from . import ai_prompt
from . import property_management
from . import finance
from . import coin_ledger
from . import volunteer
from . import delivery_team
from . import order
from . import pos_expense
from . import delivery
from . import supervisor_description_patch
from . import pos_config_ext
# The product member model is owned by wuchang_member_registration.
# Do not load the legacy transient device-gate model under the same Odoo name.
from . import pos_sms_receipt_compat
