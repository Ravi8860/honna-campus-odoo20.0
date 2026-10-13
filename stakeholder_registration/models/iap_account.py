# -*- coding: utf-8 -*-
from odoo import api, models


class IapAccount(models.Model):
    _inherit = 'iap.account'

    @api.model_create_multi
    def create(self, vals_list):
        # Core create() assigns name via a separate write. Internal users only have
        # create+read on iap.account, so Contacts create (partner autocomplete) fails.
        for vals in vals_list:
            if not vals.get('name') and vals.get('service_id'):
                service = self.env['iap.service'].browse(vals['service_id'])
                if service:
                    vals['name'] = service.name
        return super().create(vals_list)

    @api.model
    def get(self, service_name, force_create=True):
        # Bootstrap IAP accounts as system bookkeeping (token/name side-effects).
        return super(IapAccount, self.sudo()).get(service_name, force_create=force_create)
