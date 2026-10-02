# -*- coding: utf-8 -*-
from odoo import models, fields

class CampusTestimonial(models.Model):
    _name = 'honna.campus.testimonial'
    _description = 'Stakeholder Testimonial & Feedback'
    _order = 'sequence, id'

    name = fields.Char(string='Stakeholder / Author Name', required=True)
    role = fields.Char(string='Role / Subtitle')
    target_group = fields.Selection([
        ('school', 'Schools'),
        ('educator', 'Educators'),
        ('parent', 'Parents'),
    ], string='Target Group', default='school', required=True)
    quote = fields.Text(string='Quote / Feedback', required=True)
    avatar = fields.Binary(string='Avatar Image')
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)
