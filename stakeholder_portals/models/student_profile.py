# -*- coding: utf-8 -*-
from odoo import models, fields, api

class StudentProfile(models.Model):
    _inherit = 'student.profile'

    # Academic Allocation
    school_partner_id = fields.Many2one('res.partner', string='School/Institution')
    enrolled_school_branch = fields.Char(string='Enrolled School / Branch')
    student_board = fields.Selection([
        ('cbse', 'CBSE'),
        ('icse', 'ICSE'),
        ('ib', 'IB'),
        ('state_en', 'State Board – English Medium'),
        ('state_kn', 'State Board – Kannada Medium')
    ], string='Board')
    grade_standard = fields.Char(string='Grade / Standard')
    section = fields.Char(string='Section')
    academic_year = fields.Char(string='Academic Year')
    house_group = fields.Char(string='House / Group')

    # Parent / Guardian Mapping
    parent_partner_id = fields.Many2one('res.partner', string='Parent Profile')
    parent_profile_id_input = fields.Char(string='Parent Profile ID Input')  # For registration matching if parent is not created yet
    guardian_email = fields.Char(string='Guardian Email')
    emergency_contact = fields.Char(string='Emergency Contact')

    # Skill Programs & Holistic Programs
    skill_program_ids = fields.Many2many(
        'stakeholder.skill.program', 
        'student_enrolled_skills_rel', 
        'student_id', 
        'skill_id', 
        string='Enrolled Skill Programs'
    )
    interested_skill_ids = fields.Many2many(
        'stakeholder.skill.program', 
        'student_interested_skills_rel', 
        'student_id', 
        'skill_id', 
        string='Interested Holistic Skill Programs'
    )

    # Coaching & Mentorship
    pref_academic_subject = fields.Char(string='Preferred Academic Subject')
    pref_sports_skill = fields.Char(string='Preferred Sports / Skill')
    coaching_requirements = fields.Text(string='Coaching / Mentorship Requirements')

    # Health & Safety
    health_profile_id = fields.Many2one('student.health.profile', string='Student Health Profile')

    # Activities & Achievements
    achievement_ids = fields.One2many('student.achievement', 'student_profile_id', string='Activities & Achievements')
