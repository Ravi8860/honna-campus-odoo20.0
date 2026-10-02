# -*- coding: utf-8 -*-
from odoo import models, fields


class StakeholderAssociation(models.Model):
    _inherit = 'stakeholder.association'

    lead_id = fields.Many2one('crm.lead', string='CRM Lead', readonly=True, copy=False)


class StakeholderOrganisation(models.Model):
    _inherit = 'stakeholder.organisation'

    lead_id = fields.Many2one('crm.lead', string='CRM Lead', readonly=True, copy=False)


class StakeholderStudent(models.Model):
    _inherit = 'stakeholder.student'

    lead_id = fields.Many2one('crm.lead', string='CRM Lead', readonly=True, copy=False)


class StakeholderParent(models.Model):
    _inherit = 'stakeholder.parent'

    lead_id = fields.Many2one('crm.lead', string='CRM Lead', readonly=True, copy=False)
