# -*- coding: utf-8 -*-
from odoo import api, SUPERUSER_ID
import sys

# Direct execution in shell
param = env['ir.config_parameter'].sudo()

# 1. Set canonical host to wuchang.life
current = param.get_param('website.canonical_host')
target = 'wuchang.life'

if current != target:
    print(f"Updating website.canonical_host from '{current}' to '{target}'")
    param.set_param('website.canonical_host', target)
else:
    print(f"website.canonical_host is already correct: {target}")

# 2. Ensure base.url matches too
base_url = param.get_param('web.base.url')
target_base = 'https://wuchang.life'
if base_url != target_base:
    print(f"Updating web.base.url from '{base_url}' to '{target_base}'")
    param.set_param('web.base.url', target_base)

env.cr.commit()
print("Compliance fix applied successfully.")
