# -*- coding: utf-8 -*-
from odoo import models, fields


class StakeholderJoinNetwork(models.Model):
    _name = 'stakeholder.join.network'
    _description = 'Registration Join Network'
    _order = 'sequence, id'

    name = fields.Char(string='Network', required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)


class StakeholderRegistrationRole(models.Model):
    _name = 'stakeholder.registration.role'
    _description = 'Registration Role (I am an)'
    _order = 'sequence, id'

    name = fields.Char(string='Label', required=True, translate=True)
    portal_type = fields.Selection(
        selection=lambda self: self.env['crm.lead']._fields['portal_type'].selection,
        string='Portal Type', required=True,
        help='Defines which portal, access rights and registration record are created for this role.',
    )
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
