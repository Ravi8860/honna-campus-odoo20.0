# -*- coding: utf-8 -*-
from odoo import models, fields

class CampusPartner(models.Model):
    _name = 'honna.campus.partner'
    _description = 'Partner School or Institution'
    _order = 'sequence, id'

    name = fields.Char(string='Institution Name', required=True)
    location = fields.Char(string='Location / City')
    website_url = fields.Char(string='Website Link')
    logo = fields.Binary(string='Logo Image')
    logo_filename = fields.Char(string='Static Logo Filename')
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)
