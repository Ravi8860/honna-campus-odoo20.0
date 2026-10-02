# -*- coding: utf-8 -*-
from odoo import models, fields
from odoo.exceptions import UserError

class StakeholderStudent(models.Model):
    _name = 'stakeholder.student'
    _description = 'Student Registration Record'

    name = fields.Char(string='Student Full Name', required=True)
    dob = fields.Date(string='Date of Birth')
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ], string='Gender')
    blood_group = fields.Selection([
        ('A+', 'A+'), ('A-', 'A-'),
        ('B+', 'B+'), ('B-', 'B-'),
        ('O+', 'O+'), ('O-', 'O-'),
        ('AB+', 'AB+'), ('AB-', 'AB-'),
    ], string='Blood Group')
    email = fields.Char(string='Student Email')
    phone = fields.Char(string='Student Phone')
    address = fields.Text(string='Student Address')
    photo = fields.Binary(string='Photo')
    roll = fields.Char(string='Roll / Admission Number')
    school_id = fields.Many2one('res.partner', string='School/Institution')
    branch = fields.Char(string='Enrolled School / Branch')
    board = fields.Selection([
        ('cbse', 'CBSE'),
        ('icse', 'ICSE'),
        ('ib', 'IB'),
        ('state_en', 'State Board – English Medium'),
        ('state_kn', 'State Board – Kannada Medium')
    ], string='Board')
    grade = fields.Char(string='Grade / Standard')
    section = fields.Char(string='Section')
    academic_year = fields.Char(string='Academic Year')
    house_group = fields.Char(string='House / Group')
    parent_id = fields.Many2one('res.partner', string='Parent/Guardian')
    guardian_email = fields.Char(string='Guardian Email')
    emergency_contact = fields.Char(string='Emergency Contact')
    
    # Health Profile fields
    allergies = fields.Text(string='Allergies')
    medical_history = fields.Text(string='Medical History')
    vaccination = fields.Text(string='Vaccination Status')
    height = fields.Float(string='Height')
    weight = fields.Float(string='Weight')

    # Skill program mappings
    enrolled_skills = fields.Many2many('stakeholder.skill.program', 'stakeholder_student_enrolled_skills_rel', 'student_id', 'skill_id', string='Enrolled Skill Programs')
    interested_skills = fields.Many2many('stakeholder.skill.program', 'stakeholder_student_interested_skills_rel', 'student_id', 'skill_id', string='Interested Skills')

    # Preferences
    subject_preferences = fields.Text(string='Preferred Academic Subjects')
    sports_preferences = fields.Text(string='Preferred Sports/Skills')
    coaching_requirements = fields.Text(string='Coaching/Mentorship Requirements')
    
    # Custom items JSON
    achievements_json = fields.Text(string='Achievements JSON')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], string='Status', default='draft', required=True)
    partner_id = fields.Many2one('res.partner', string='Approved Partner', readonly=True)
    student_profile_id = fields.Many2one('student.profile', string='Approved Student Profile', readonly=True)

    def action_approve(self):
        self.ensure_one()
        if not (self.env.user.has_group('stakeholder_registration.group_stakeholder_user') or 
                self.env.user.has_group('stakeholder_registration.group_association_user') or
                self.env.user.has_group('stakeholder_registration.group_school_user') or
                self.env.user.has_group('base.group_system')):
            raise UserError("You do not have rights to approve student registrations.")
        partner_obj = self.env['res.partner']
        partner = self.partner_id
        if not partner and self.email:
            partner = partner_obj.sudo().search([('email', '=', self.email)], limit=1)
        if not partner and self.phone:
            partner = partner_obj.sudo().search([('phone', '=', self.phone)], limit=1)
        if not partner:
            partner = partner_obj.sudo().search([('name', '=', self.name)], limit=1)
            
        partner_vals = {
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'street': self.address,
            'is_company': False,
            'user_id': self.env.user.id,
            'user_category': 'student',
        }
        if self.photo:
            partner_vals['image_1920'] = self.photo
            
        if partner:
            partner.sudo().write(partner_vals)
        else:
            partner = partner_obj.sudo().create(partner_vals)

        if partner.email:
            user_obj = self.env['res.users'].sudo()
            existing_user = user_obj.search([('login', '=', partner.email)], limit=1)
            if not existing_user:
                portal_group = self.env.ref('base.group_portal', raise_if_not_found=False)
                groups = [(6, 0, [portal_group.id])] if portal_group else []
                user = user_obj.create({
                    'name': partner.name,
                    'login': partner.email,
                    'email': partner.email,
                    'phone': partner.phone,
                    'partner_id': partner.id,
                    'group_ids': groups,
                    'share': True,
                    'user_category': 'student',
                })
                try:
                    user.action_reset_password()
                except Exception:
                    pass
            elif not existing_user.user_category:
                existing_user.sudo().write({'user_category': 'student'})

            
        student_profile_obj = self.env['student.profile']
        student_profile = student_profile_obj.sudo().search([
            ('email', '=', self.email)
        ], limit=1) if self.email else student_profile_obj
        if not student_profile and self.phone:
            student_profile = student_profile_obj.sudo().search([('phone', '=', self.phone)], limit=1)
        if not student_profile and self.roll:
            student_profile = student_profile_obj.sudo().search([('code', '=', self.roll)], limit=1)

        health_profile = self.env['student.health.profile'].sudo().create({
            'blood_group': self.blood_group,
            'allergies': self.allergies,
            'medical_history': self.medical_history,
            'vaccination_status': self.vaccination,
            'height': self.height,
            'weight': self.weight,
        })
        
        profile_vals = {
            'name': self.name,
            'partner_id': partner.id,
            'date_of_birth': self.dob,
            'gender': self.gender,
            'blood_group': self.blood_group,
            'email': self.email,
            'phone': self.phone,
            'address': self.address,
            'image': self.photo,
            'school_partner_id': self.school_id.id if self.school_id else None,
            'enrolled_school_branch': self.branch,
            'student_board': self.board,
            'grade_standard': self.grade,
            'section': self.section,
            'academic_year': self.academic_year,
            'house_group': self.house_group,
            'parent_partner_id': self.parent_id.id if self.parent_id else None,
            'guardian_email': self.guardian_email,
            'emergency_contact': self.emergency_contact,
            'pref_academic_subject': self.subject_preferences,
            'pref_sports_skill': self.sports_preferences,
            'coaching_requirements': self.coaching_requirements,
            'health_profile_id': health_profile.id,
            'skill_program_ids': [(6, 0, self.enrolled_skills.ids)],
            'interested_skill_ids': [(6, 0, self.interested_skills.ids)],
        }
        if self.roll:
            profile_vals['code'] = self.roll

        if student_profile:
            student_profile.sudo().write(profile_vals)
        else:
            student_profile = student_profile_obj.sudo().create(profile_vals)
            
        if self.achievements_json:
            import json
            try:
                achievements = json.loads(self.achievements_json)
                for a in achievements:
                    if a.get('name') and a.get('type'):
                        self.env['student.achievement'].sudo().create({
                            'student_profile_id': student_profile.id,
                            'type': a.get('type'),
                            'name': a.get('name'),
                            'date': a.get('date') or None,
                            'achievement_details': a.get('details')
                        })
            except Exception:
                pass
                
        self.sudo().write({
            'partner_id': partner.id,
            'student_profile_id': student_profile.id,
            'state': 'approved'
        })
        
    def action_reject(self):
        self.ensure_one()
        if not (self.env.user.has_group('stakeholder_registration.group_stakeholder_user') or 
                self.env.user.has_group('stakeholder_registration.group_association_user') or
                self.env.user.has_group('stakeholder_registration.group_school_user') or
                self.env.user.has_group('base.group_system')):
            raise UserError("You do not have rights to reject student registrations.")
        self.sudo().write({'state': 'rejected'})

    def action_draft(self):
        self.ensure_one()
        if not (self.env.user.has_group('stakeholder_registration.group_stakeholder_user') or 
                self.env.user.has_group('stakeholder_registration.group_association_user') or
                self.env.user.has_group('stakeholder_registration.group_school_user') or
                self.env.user.has_group('base.group_system')):
            raise UserError("You do not have rights to reset student registrations to draft.")
        self.sudo().write({'state': 'draft'})
