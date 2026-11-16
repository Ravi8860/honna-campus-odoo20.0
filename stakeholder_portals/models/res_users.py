# -*- coding: utf-8 -*-
from odoo import models, fields


class ResUsers(models.Model):
    _inherit = 'res.users'

    join_network_id = fields.Many2one('stakeholder.join.network', string='Join Network', copy=False)

    def _action_reset_password(self, signup_type="reset"):
        """ Send the network invitation mail instead of the default Odoo invite
        to users created from the registration page with a selected network. """
        if not self.env.context.get('create_user') or self.env.context.get('install_mode') or self.env.context.get('import_file'):
            return super()._action_reset_password(signup_type=signup_type)

        network_users = self.filtered(lambda u: u.join_network_id and u.email and u.active)
        template = self.env.ref('stakeholder_portals.mail_template_network_invitation', raise_if_not_found=False)
        if not network_users or not template:
            return super()._action_reset_password(signup_type=signup_type)

        network_users.mapped('partner_id').signup_prepare(signup_type=signup_type)
        for user in network_users:
            template.send_mail(user.id, force_send=True, raise_exception=True, email_values={
                'email_to': user.email,
                'email_cc': False,
                'recipient_ids': [],
                'partner_ids': [],
                'auto_delete': True,
                'message_type': 'user_notification',
                'scheduled_date': False,
            })

        other_users = self - network_users
        if other_users:
            return super(ResUsers, other_users)._action_reset_password(signup_type=signup_type)
