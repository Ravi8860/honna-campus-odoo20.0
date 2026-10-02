# -*- coding: utf-8 -*-
from odoo import models, fields

class StakeholderSkillProgram(models.Model):
    _name = 'stakeholder.skill.program'
    _description = 'Skill Program'

    name = fields.Char(string='Program Name', required=True)
    code = fields.Char(string='Program Code', required=True)
    type = fields.Selection([
        ('skill', 'Skill Program'),
        ('holistic', 'Holistic Skill Program')
    ], string='Type', default='skill')
