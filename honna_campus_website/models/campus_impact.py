# -*- coding: utf-8 -*-
from odoo import models, fields

class CampusImpact(models.Model):
    _name = 'honna.campus.impact'
    _description = 'Honna Campus Impact Statistics and Timeline'
    _order = 'sequence, year asc, id'

    name = fields.Char(string='Metric Name', required=True)
    metric_type = fields.Selection([
        ('counter', 'Hero / Metric Counter'),
        ('growth', 'Yearly Growth Point'),
    ], string='Type', default='counter', required=True)
    value = fields.Char(string='Display Value (e.g. 28000+, 95%)', required=True)
    label = fields.Char(string='Label / Description', required=True)
    year = fields.Integer(string='Year (for growth points)', default=2024)
    percentage = fields.Integer(string='Growth Percentage %', default=0)
    sequence = fields.Integer(string='Sequence', default=10)
