# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import date

class StudentProfile(models.Model):
    _name = 'student.profile'
    _description = 'Student Profile'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='Student Name', required=True, tracking=True)
    code = fields.Char(string='Student ID', readonly=True, copy=False, default='New')
    partner_id = fields.Many2one('res.partner', string='Contact')
    date_of_birth = fields.Date(string='Date of Birth')
    age = fields.Integer(string='Age', compute='_compute_age', store=False)
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
    nationality = fields.Many2one('res.country', string='Nationality')
    religion = fields.Char(string='Religion')
    phone = fields.Char(string='Phone')
    email = fields.Char(string='Email')
    address = fields.Text(string='Address')
    image = fields.Binary(string='Photo')
    
    father_name = fields.Char(string="Father's Name")
    father_phone = fields.Char(string="Father's Phone")
    father_occupation = fields.Char(string="Father's Occupation")
    mother_name = fields.Char(string="Mother's Name")
    mother_phone = fields.Char(string="Mother's Phone")
    guardian_name = fields.Char(string='Guardian Name')
    guardian_phone = fields.Char(string='Guardian Phone')
    guardian_relation = fields.Char(string='Guardian Relation')
    admission_date = fields.Date(string='Admission Date', default=fields.Date.today)
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('enrolled', 'Enrolled'),
        ('active', 'Active'),
        ('graduated', 'Graduated'),
        ('expelled', 'Expelled'),
    ], string='Status', default='draft', tracking=True)
    
    note = fields.Text(string='Notes')

    @api.depends('date_of_birth')
    def _compute_age(self):
        today = date.today()
        for record in self:
            if record.date_of_birth:
                dob = record.date_of_birth
                record.age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            else:
                record.age = 0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('code', 'New') == 'New':
                vals['code'] = self.env['ir.sequence'].next_by_code('student.profile') or 'New'
        return super().create(vals_list)

    def action_enroll(self):
        for record in self:
            if record.state != 'draft':
                raise UserError(_('Only draft students can be enrolled.'))
            record.state = 'enrolled'

    def action_activate(self):
        for record in self:
            if record.state != 'enrolled':
                raise UserError(_('Only enrolled students can be activated.'))
            record.state = 'active'

    def action_graduate(self):
        for record in self:
            if record.state not in ('active', 'enrolled'):
                raise UserError(_('Only active or enrolled students can be graduated.'))
            record.state = 'graduated'

    def action_expel(self):
        for record in self:
            if record.state == 'expelled':
                raise UserError(_('Student is already expelled.'))
            record.state = 'expelled'

    def action_reset(self):
        for record in self:
            record.state = 'draft'
