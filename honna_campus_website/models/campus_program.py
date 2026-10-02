# -*- coding: utf-8 -*-
from odoo import models, fields

class CampusProgram(models.Model):
    _name = 'honna.campus.program'
    _description = 'Honna Campus Educational Program'
    _order = 'sequence, id'

    name = fields.Char(string='Program Name', required=True)
    code = fields.Char(string='Code')
    category = fields.Selection([
        ('stem', 'STEM Education'),
        ('pixel', 'Pixel Studio'),
        ('content', '3D/2D Content'),
        ('language', 'Language Studio'),
        ('holistic', 'Holistic Tech Education'),
        ('other', 'Other'),
    ], string='Category', default='holistic', required=True)
    description = fields.Text(string='Description')
    icon = fields.Char(string='Icon Class or Identifier', help='CSS class or icon identifier (e.g. bi-cpu, fa-robot)')
    image = fields.Binary(string='Image')
    image_url = fields.Char(string='Static Image URL')
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)
