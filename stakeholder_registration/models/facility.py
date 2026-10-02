# -*- coding: utf-8 -*-
from odoo import models, fields

class StakeholderFacility(models.Model):
    _name = 'stakeholder.facility'
    _description = 'School Facility'

    name = fields.Char(string='Facility Name', required=True)
    code = fields.Char(string='Facility Code', required=True)
