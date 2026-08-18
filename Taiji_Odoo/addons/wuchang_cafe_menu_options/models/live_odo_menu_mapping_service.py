from odoo import models

from ..utils.menu_readonly_mapping_core import collect_readonly_menu_snapshot_from_env


class WuchangCafeReadonlyMenuMappingService(models.AbstractModel):
    _name = "wuchang.cafe.readonly.menu.mapping.service"
    _description = "WuChang Cafe Live Odoo Menu Readonly Mapping Service"

    def live_odo_menu_data_readonly_mapping_v1(self, limit=200):
        return collect_readonly_menu_snapshot_from_env(self.env, limit=limit)

