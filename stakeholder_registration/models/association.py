# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.tools import sql

class StakeholderAssociation(models.Model):
    _name = 'stakeholder.association'
    _description = 'Association Registration Record'

    active = fields.Boolean(string='Active', default=True)
    name = fields.Char(string='Official Organisation Name', required=True)
    phone = fields.Char(string='Association Phone')
    email = fields.Char(string='Association Email')
    website = fields.Char(string='Website')
    year_established = fields.Char(string='Year Established')
    vat = fields.Char(string='Tax ID / GSTIN')
    trust_details = fields.Text(string='Note')

    def _default_country_id(self):
        return self.env.ref('base.in', raise_if_not_found=False) or self.env['res.country'].search([('code', '=', 'IN')], limit=1)

    # Primary Address fields
    street = fields.Char(string='Address Line 1')
    street2 = fields.Char(string='Address Line 2')
    city = fields.Char(string='City')
    state_id = fields.Many2one(
        'res.country.state',
        string='State',
        domain="[('country_id.code', '=', 'IN')]",
    )
    country_id = fields.Many2one(
        'res.country',
        string='Country',
        default=_default_country_id,
        domain="[('code', '=', 'IN')]",
    )
    zip = fields.Char(string='PIN Code')
    address = fields.Text(string='Registered Office Address')
    geolocation = fields.Char(string='Geo-location Coordinates')

    # Primary Contact fields
    primary_contact_first_name = fields.Char(string='First Name')
    primary_contact_last_name = fields.Char(string='Last Name')
    contact_name = fields.Char(string='First & Last Name', compute='_compute_contact_name', store=True, readonly=False)
    contact_name_phone = fields.Char(string='Primary Contact', compute='_compute_contact_name_phone', store=True)
    contact_role = fields.Char(string='Job Title / Role')
    contact_phone = fields.Char(string='Mobile')
    contact_email = fields.Char(string='Email')
    contact_method = fields.Selection([
        ('email', 'Email'),
        ('whatsapp', 'WhatsApp'),
        ('phone', 'Phone'),
    ], string='Preferred Contact Method', default='email')

    # Legacy / Unused fields kept for database column safety
    assoc_code = fields.Char(string='Association Code')
    branch_code = fields.Char(string='Branch Code (if multicampus)')
    show_other_details = fields.Selection([
        ('no', 'No'),
        ('yes', 'Yes'),
    ], string='Show Other Details', default='no')
    board_affiliation = fields.Selection([
        ('cbse', 'CBSE'),
        ('icse', 'ICSE'),
        ('state', 'State Board'),
        ('ib', 'IB'),
        ('state_en', 'State Board – English Medium'),
        ('state_kn', 'State Board – Kannada Medium'),
    ], string='Board Affiliation')
    accreditation = fields.Char(string='Accreditation')
    medium = fields.Char(string='Medium Offered')
    area = fields.Char(string='Campus Area')
    capacity = fields.Integer(string='Total Student Capacity')
    facility_ids = fields.Many2many('stakeholder.facility', string='Available Facilities')
    residential = fields.Selection([
        ('boys', 'Boys'),
        ('girls', 'Girls'),
        ('coed', 'Co-ed / Both'),
        ('none', 'Day School / Non-Residential'),
    ], string='Residential')
    contact_time = fields.Char(string='Preferred Contact Time')

    logo = fields.Binary(string='Logo')
    member_ids = fields.One2many('stakeholder.association.member', 'association_id', string='Management / Executive Members')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], string='Status', default='draft', required=True)
    partner_id = fields.Many2one('res.partner', string='Approved Partner', readonly=True)
    user_id = fields.Many2one('res.users', string='Related User', compute='_compute_user_id', store=True, readonly=False)
    school_ids = fields.Many2many(
        'stakeholder.organisation',
        'stakeholder_association_stakeholder_organisation_rel',
        'stakeholder_association_id',
        'stakeholder_organisation_id',
        string='School',
    )

    @api.depends('partner_id', 'email', 'name')
    def _compute_user_id(self):
        assoc_group = self.env.ref('stakeholder_registration.group_association_user', raise_if_not_found=False)
        for rec in self:
            user = False
            if rec.partner_id:
                user = self.env['res.users'].sudo().search([('partner_id', '=', rec.partner_id.id)], limit=1)
            if not user and rec.email:
                user = self.env['res.users'].sudo().search([('login', '=', rec.email)], limit=1) or \
                       self.env['res.users'].sudo().search([('email', '=', rec.email)], limit=1)
            if not user and rec.name:
                user = self.env['res.users'].sudo().search([
                    ('name', '=ilike', rec.name),
                    '|',
                    ('user_category', '=', 'association'),
                    ('group_ids', 'in', [assoc_group.id] if assoc_group else [])
                ], limit=1)
            rec.user_id = user

    def action_open_profile(self):
        user = self.env.user
        if hasattr(user, '_sync_association_profile'):
            user._sync_association_profile()
        assoc = user.association_id
        if not assoc:
            domain_parts = []
            if user.partner_id:
                domain_parts.append(('partner_id', '=', user.partner_id.id))
            domain_parts.append(('user_id', '=', user.id))
            domain_parts.append(('partner_id.user_ids', 'in', [user.id]))
            if user.email:
                domain_parts.append(('email', '=', user.email))
            if user.login and '@' in user.login:
                domain_parts.append(('email', '=', user.login))
            if user.name:
                domain_parts.append(('name', '=ilike', user.name))
            if user.partner_id and user.partner_id.name and user.partner_id.name != user.name:
                domain_parts.append(('name', '=ilike', user.partner_id.name))
            domain_parts.append(('create_uid', '=', user.id))

            search_domain = ['|'] * (len(domain_parts) - 1) + domain_parts
            assoc = self.env['stakeholder.association'].sudo().search(search_domain, limit=1)

        if not assoc and user.has_group('stakeholder_registration.group_association_user'):
            assoc = self.env['stakeholder.association'].sudo().create({
                'name': user.name or (user.partner_id.name if user.partner_id else 'Association Profile'),
                'partner_id': user.partner_id.id if user.partner_id else False,
                'user_id': user.id,
                'email': user.email or (user.login if '@' in (user.login or '') else False),
                'phone': user.partner_id.phone if user.partner_id else False,
                'state': 'draft',
            })

        if assoc:
            vals = {}
            if not assoc.user_id or assoc.user_id != user:
                vals['user_id'] = user.id
            if user.partner_id and (not assoc.partner_id or assoc.partner_id != user.partner_id):
                vals['partner_id'] = user.partner_id.id
            if user.email and not assoc.email:
                vals['email'] = user.email
            if vals:
                assoc.sudo().write(vals)
            if user.association_id != assoc:
                user.sudo().write({'association_id': assoc.id})

        form_view = self.env.ref('stakeholder_registration.view_stakeholder_association_form', raise_if_not_found=False)
        tree_view = self.env.ref('stakeholder_registration.view_stakeholder_association_tree', raise_if_not_found=False)
        views = []
        if form_view:
            views.append((form_view.id, 'form'))
        if tree_view:
            views.append((tree_view.id, 'list'))
        if assoc:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Profile',
                'res_model': 'stakeholder.association',
                'res_id': assoc.id,
                'view_mode': 'form,list',
                'views': views,
                'target': 'current',
                'context': {'create': False, 'delete': False},
            }
        return {
            'type': 'ir.actions.act_window',
            'name': 'Profile',
            'res_model': 'stakeholder.association',
            'view_mode': 'list,form',
            'views': [(tree_view.id, 'list'), (form_view.id, 'form')] if tree_view and form_view else False,
            'target': 'current',
            'context': {'create': False, 'delete': False},
        }

    @api.depends('primary_contact_first_name', 'primary_contact_last_name')
    def _compute_contact_name(self):
        for rec in self:
            full_name = ' '.join(filter(None, [rec.primary_contact_first_name, rec.primary_contact_last_name])).strip()
            if full_name:
                rec.contact_name = full_name
            elif not rec.contact_name:
                rec.contact_name = False

    @api.depends('contact_name', 'contact_phone', 'primary_contact_first_name', 'primary_contact_last_name')
    def _compute_contact_name_phone(self):
        for rec in self:
            name = rec.contact_name or ' '.join(filter(None, [rec.primary_contact_first_name, rec.primary_contact_last_name])).strip()
            phone = rec.contact_phone
            if name and phone:
                rec.contact_name_phone = f"{name} | {phone}"
            elif name:
                rec.contact_name_phone = name
            elif phone:
                rec.contact_name_phone = phone
            else:
                rec.contact_name_phone = False

    @api.onchange('state_id')
    def _onchange_state_id(self):
        if self.state_id and self.state_id.country_id:
            self.country_id = self.state_id.country_id
        elif not self.country_id:
            self.country_id = self._default_country_id()

    @api.onchange('country_id')
    def _onchange_country_id(self):
        if self.country_id and self.state_id and self.state_id.country_id != self.country_id:
            self.state_id = False

    def _link_matching_user(self):
        self.ensure_one()
        user = self.user_id
        if not user:
            assoc_group = self.env.ref('stakeholder_registration.group_association_user', raise_if_not_found=False)
            if self.partner_id:
                user = self.env['res.users'].sudo().search([('partner_id', '=', self.partner_id.id)], limit=1)
            if not user and self.email:
                user = self.env['res.users'].sudo().search([
                    '|', ('login', '=', self.email), ('email', '=', self.email)
                ], limit=1)
            if not user and self.name:
                user = self.env['res.users'].sudo().search([
                    ('name', '=ilike', self.name),
                    '|', ('user_category', '=', 'association'),
                    ('group_ids', 'in', [assoc_group.id] if assoc_group else [])
                ], limit=1)
        if user:
            vals = {}
            if self.user_id != user:
                vals['user_id'] = user.id
            if user.partner_id and self.partner_id != user.partner_id:
                vals['partner_id'] = user.partner_id.id
            if vals:
                self.sudo().write(vals)
            if user.association_id != self:
                user.sudo().write({'association_id': self.id})

    @api.model_create_multi
    def create(self, vals_list):
        india = self._default_country_id()
        if india:
            for vals in vals_list:
                if not vals.get('country_id'):
                    vals['country_id'] = india.id
        records = super().create(vals_list)
        for rec in records:
            rec._link_matching_user()
        return records

    def write(self, vals):
        res = super().write(vals)
        if any(f in vals for f in ('name', 'email', 'partner_id', 'user_id')):
            for rec in self:
                rec._link_matching_user()
        return res

    def init(self):
        super().init()
        india = self._default_country_id()
        if india and sql.table_exists(self.env.cr, self._table):
            self.env.cr.execute(
                f"UPDATE {self._table} SET country_id = %s WHERE country_id IS NULL",
                (india.id,)
            )

    def action_approve(self):
        self.ensure_one()
        if not (self.env.user.has_group('stakeholder_registration.group_stakeholder_user') or 
                self.env.user.has_group('stakeholder_registration.group_association_user') or
                self.env.user.has_group('stakeholder_registration.group_school_user') or
                self.env.user.has_group('base.group_system')):
            raise UserError("You do not have rights to approve association registrations.")
        partner_obj = self.env['res.partner']
        partner = self.partner_id
        if not partner and self.email:
            partner = partner_obj.sudo().search([('email', '=', self.email)], limit=1)
        if not partner and self.phone:
            partner = partner_obj.sudo().search([('phone', '=', self.phone)], limit=1)
        if not partner:
            partner = partner_obj.sudo().search([('name', '=', self.name)], limit=1)
            
        vals = {
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'website': self.website,
            'vat': self.vat,
            'street': self.street or self.address,
            'street2': self.street2,
            'city': self.city,
            'state_id': self.state_id.id if self.state_id else False,
            'zip': self.zip,
            'country_id': self.country_id.id if self.country_id else False,
            'is_company': True,
            'user_id': self.user_id.id or self.env.user.id,
            'user_category': 'association',
        }
        if partner:
            partner.sudo().write(vals)
        else:
            partner = partner_obj.sudo().create(vals)

        user = False
        if partner.email:
            user_obj = self.env['res.users'].sudo()
            existing_user = user_obj.search([('login', '=', partner.email)], limit=1)
            if not existing_user and partner:
                existing_user = user_obj.search([('partner_id', '=', partner.id)], limit=1)
            group_user = self.env.ref('base.group_user', raise_if_not_found=False)
            assoc_group = self.env.ref('stakeholder_registration.group_association_user', raise_if_not_found=False)
            if not existing_user:
                groups = [g.id for g in [group_user, assoc_group] if g]
                user = user_obj.with_context(skip_sync_assoc=True).create({
                    'name': self.contact_name or self.name or partner.name,
                    'login': partner.email,
                    'email': partner.email,
                    'phone': self.phone or partner.phone,
                    'partner_id': partner.id,
                    'association_id': self.id,
                    'group_ids': [(6, 0, groups)],
                    'share': False,
                    'user_category': 'association',
                })
                try:
                    user.action_reset_password()
                except Exception:
                    pass
            else:
                user = existing_user
                user_write_vals = {'user_category': 'association'}
                if assoc_group and assoc_group not in existing_user.group_ids:
                    user_write_vals['group_ids'] = [(4, assoc_group.id)]
                if not user.association_id or user.association_id != self:
                    user_write_vals['association_id'] = self.id
                existing_user.with_context(skip_sync_assoc=True).write(user_write_vals)
            
        for member in self.member_ids:
            mem_name = member.name or ' '.join(filter(None, [member.first_name, member.last_name])).strip() or 'Member'
            self.env['stakeholder.team.member'].sudo().create({
                'partner_id': partner.id,
                'name': mem_name,
                'designation': 'ec_member',
                'phone': member.phone,
                'email': member.email,
            })

        write_vals = {
            'partner_id': partner.id,
            'state': 'approved'
        }
        if user:
            write_vals['user_id'] = user.id
        self.sudo().write(write_vals)
        
    def action_reject(self):
        self.ensure_one()
        if not (self.env.user.has_group('stakeholder_registration.group_stakeholder_user') or 
                self.env.user.has_group('stakeholder_registration.group_association_user') or
                self.env.user.has_group('stakeholder_registration.group_school_user') or
                self.env.user.has_group('base.group_system')):
            raise UserError("You do not have rights to reject association registrations.")
        self.sudo().write({'state': 'rejected'})

    def action_draft(self):
        self.ensure_one()
        if not (self.env.user.has_group('stakeholder_registration.group_stakeholder_user') or 
                self.env.user.has_group('stakeholder_registration.group_association_user') or
                self.env.user.has_group('stakeholder_registration.group_school_user') or
                self.env.user.has_group('base.group_system')):
            raise UserError("You do not have rights to reset association registrations to draft.")
        self.sudo().write({'state': 'draft'})

class StakeholderAssociationMember(models.Model):
    _name = 'stakeholder.association.member'
    _description = 'Association Management Member'

    association_id = fields.Many2one('stakeholder.association', string='Association', ondelete='cascade')
    first_name = fields.Char(string='First Name')
    last_name = fields.Char(string='Last Name')
    name = fields.Char(string='Name', compute='_compute_name', store=True, readonly=False)
    role = fields.Char(string='Role')
    designation = fields.Char(string='Designation')
    phone = fields.Char(string='Phone')
    email = fields.Char(string='Email')
    contact_method = fields.Selection([
        ('email', 'Email'),
        ('whatsapp', 'WhatsApp'),
        ('phone', 'Phone'),
    ], string='Preferred Contact Method', default='email')

    @api.depends('first_name', 'last_name')
    def _compute_name(self):
        for rec in self:
            full_name = ' '.join(filter(None, [rec.first_name, rec.last_name])).strip()
            if full_name:
                rec.name = full_name
            elif not rec.name:
                rec.name = False

    @api.onchange('role')
    def _onchange_role(self):
        if self.role and not self.designation:
            self.designation = self.role
