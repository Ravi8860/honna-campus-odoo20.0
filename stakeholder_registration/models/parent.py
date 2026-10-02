# -*- coding: utf-8 -*-
from odoo import models, fields
from odoo.exceptions import UserError

class StakeholderParent(models.Model):
    _name = 'stakeholder.parent'
    _description = 'Parent Registration Record'

    name = fields.Char(string='Parent Full Name', required=True)
    email = fields.Char(string='Email')
    phone = fields.Char(string='Phone')
    photo = fields.Binary(string='Photo')
    pref_subject = fields.Char(string='Preferred Academic Subject')
    pref_skills = fields.Char(string='Preferred Sports/Skills')
    coaching_req = fields.Text(string='Coaching / Mentorship Requirements')
    enquiry = fields.Char(string='New School Enquiry')
    apply = fields.Char(string='New School Application')
    student_ids = fields.Many2many('student.profile', string='Mapped Students')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], string='Status', default='draft', required=True)
    partner_id = fields.Many2one('res.partner', string='Approved Partner', readonly=True)

    def action_approve(self):
        self.ensure_one()
        if not (self.env.user.has_group('stakeholder_registration.group_stakeholder_user') or 
                self.env.user.has_group('stakeholder_registration.group_association_user') or
                self.env.user.has_group('stakeholder_registration.group_school_user') or
                self.env.user.has_group('base.group_system')):
            raise UserError("You do not have rights to approve parent registrations.")
        partner_obj = self.env['res.partner']
        partner = self.partner_id
        if not partner and self.email:
            partner = partner_obj.sudo().search([('email', '=', self.email)], limit=1)
        if not partner and self.phone:
            partner = partner_obj.sudo().search([('phone', '=', self.phone)], limit=1)
        if not partner:
            partner = partner_obj.sudo().search([('name', '=', self.name)], limit=1)
            
        notes = []
        notes.append(f"Preferred Academic Subject: {self.pref_subject or ''}")
        notes.append(f"Preferred Sports/Skills: {self.pref_skills or ''}")
        notes.append(f"Coaching Requirements: {self.coaching_req or ''}")
        notes.append(f"New School Enquiry: {self.enquiry or ''}")
        notes.append(f"New School Application: {self.apply or ''}")
        
        partner_vals = {
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'comment': "\n".join(notes),
            'is_company': False,
            'user_id': self.env.user.id,
            'user_category': 'parent',
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
                    'user_category': 'parent',
                })
                try:
                    user.action_reset_password()
                except Exception:
                    pass
            elif not existing_user.user_category:
                existing_user.sudo().write({'user_category': 'parent'})

            
        for student_prof in self.student_ids:
            student_prof.sudo().write({
                'parent_partner_id': partner.id
            })
            
        self.sudo().write({
            'partner_id': partner.id,
            'state': 'approved'
        })
        
    def action_reject(self):
        self.ensure_one()
        if not (self.env.user.has_group('stakeholder_registration.group_stakeholder_user') or 
                self.env.user.has_group('stakeholder_registration.group_association_user') or
                self.env.user.has_group('stakeholder_registration.group_school_user') or
                self.env.user.has_group('base.group_system')):
            raise UserError("You do not have rights to reject parent registrations.")
        self.sudo().write({'state': 'rejected'})

    def action_draft(self):
        self.ensure_one()
        if not (self.env.user.has_group('stakeholder_registration.group_stakeholder_user') or 
                self.env.user.has_group('stakeholder_registration.group_association_user') or
                self.env.user.has_group('stakeholder_registration.group_school_user') or
                self.env.user.has_group('base.group_system')):
            raise UserError("You do not have rights to reset parent registrations to draft.")
        self.sudo().write({'state': 'draft'})
