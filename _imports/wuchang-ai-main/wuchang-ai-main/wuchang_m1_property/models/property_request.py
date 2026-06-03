from odoo import fields, models, _


class PropertyRequest(models.Model):
    _name = 'property.request'
    _description = 'Property Service Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='報修主題', required=True, tracking=True)
    resident_id = fields.Many2one('res.partner', string='報修住戶', tracking=True)
    location = fields.Char(string='地點')
    request_type = fields.Selection(
        selection=[
            ('public', '公共設施'),
            ('private', '住戶服務'),
        ],
        string='報修類型',
        default='public',
    )
    description = fields.Html(string='問題描述')
    image = fields.Binary(string='現場照片', attachment=True)
    state = fields.Selection(
        selection=[
            ('draft', '草稿'),
            ('submitted', '已提交'),
            ('assigned', '處理中'),
            ('done', '已完修'),
            ('cancel', '取消'),
        ],
        string='狀態',
        default='draft',
        tracking=True,
    )
    task_id = fields.Many2one('project.task', string='關聯任務', readonly=True, tracking=True)
    required_skill_id = fields.Many2one('wuchang.skill', string='所需技能')

    def action_submit(self):
        self.write({'state': 'submitted'})
        return True

    def action_mark_done(self):
        self.write({'state': 'done'})
        return True

    def action_cancel(self):
        self.write({'state': 'cancel'})
        return True

    def action_reset_to_draft(self):
        self.write({'state': 'draft'})
        return True

    def _handle_submission(self):
        self.ensure_one()
        task = self.task_id
        if not task:
            task_vals = {
                'name': self.name,
                'description': self.description,
            }
            task = self.env['project.task'].create(task_vals)
            self.with_context(skip_property_request_auto=True).write({'task_id': task.id})

        volunteer_domain = [('x_is_volunteer', '=', True)]
        if self.required_skill_id:
            volunteer_domain.append(('x_volunteer_skills', 'in', self.required_skill_id.id))

        volunteers = self.env['hr.employee'].search(volunteer_domain)
        eligible_message = False
        if self.required_skill_id and not volunteers:
            eligible_message = _('目前沒有符合技能「%s」的志工。') % self.required_skill_id.name
        elif volunteers:
            eligible_names = ', '.join(volunteers.mapped('name'))
            eligible_message = _('符合條件的志工：%s') % eligible_names

        volunteer_with_user = volunteers.filtered(lambda v: v.user_id)[:1]
        if volunteer_with_user:
            task.write({'user_id': volunteer_with_user.user_id.id})
        if eligible_message:
            task.message_post(body=eligible_message)

        self.with_context(skip_property_request_auto=True).write({'state': 'assigned'})

    def write(self, vals):
        if self.env.context.get('skip_property_request_auto'):
            return super().write(vals)

        records_to_submit = self.env['property.request']
        if 'state' in vals:
            records_to_submit = self.filtered(lambda r: r.state == 'draft')
        res = super().write(vals)

        if 'state' in vals and vals.get('state') == 'submitted':
            for record in records_to_submit.filtered(lambda r: r.state == 'submitted'):
                record._handle_submission()
        return res
