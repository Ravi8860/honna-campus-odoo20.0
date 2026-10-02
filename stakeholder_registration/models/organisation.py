# -*- coding: utf-8 -*-
from odoo import models, fields, api, Command
from odoo.exceptions import UserError
from odoo.tools import sql

EXECUTIVE_ROLE_SELECTION = [
    ('chairman', 'Chairman'),
    ('secretary', 'Secretary'),
    ('treasurer', 'Treasurer'),
    ('committee_members', 'Committee Members'),
    ('principal', 'Principal'),
    ('vice_principal', 'Vice Principal'),
]

ACADEMIC_ROLE_SELECTION = [
    ('coordinator', 'Coordinator'),
    ('teachers', 'Teachers'),
    ('stem_instructor', 'STEM Instructor'),
    ('lab_instructor', 'Lab Instructor'),
]

OPERATIONS_ROLE_SELECTION = [
    ('store_manager', 'Store Manager'),
    ('it_administrator', 'IT Administrator'),
    ('accountant', 'Accountant'),
]

ORGANISATION_CATEGORY_SELECTION = [
    ('honna_staff', 'Honna Staff'),
    ('school', 'School'),
    ('college', 'College'),
    ('academy', 'Academy'),
    ('partner', 'Partner'),
    ('others', 'Others'),
]

class StakeholderOrganisation(models.Model):
    _name = 'stakeholder.organisation'
    _description = 'Organisation / Institution Registration Record'

    active = fields.Boolean(string='Active', default=True)
    category = fields.Selection(
        ORGANISATION_CATEGORY_SELECTION,
        string='Category',
        default='school',
        index=True,
        required=True,
    )
    name = fields.Char(string='Institution Name', required=True)
    phone = fields.Char(string='School Phone')
    email = fields.Char(string='School Email')
    website = fields.Char(string='Website')
    parent_organisation_id = fields.Many2one('stakeholder.association', string='Parent Organisation Name')
    parent_school_id = fields.Many2one(
        'stakeholder.organisation',
        string='Parent School / Head Office',
        index=True,
        domain="[('id', '!=', id)]",
    )
    child_school_ids = fields.One2many(
        'stakeholder.organisation',
        'parent_school_id',
        string='Branch Schools / Campuses',
    )
    is_branch = fields.Boolean(
        string='Is a Branch School',
        compute='_compute_is_branch',
        store=True,
    )
    branch_count = fields.Integer(
        string='Branches Count',
        compute='_compute_branch_count',
    )
    association_ids = fields.Many2many(
        'stakeholder.association',
        'stakeholder_association_stakeholder_organisation_rel',
        'stakeholder_organisation_id',
        'stakeholder_association_id',
        string='Associations',
    )
    org_code = fields.Char(string='Organisation Code / Affiliation Number')
    affiliation_number = fields.Char(string='Affiliation Number')
    vat = fields.Char(string='Tax ID / GSTIN')
    trust_details = fields.Text(string='Note')
    year_established = fields.Char(string='Year Established')

    def _default_country_id(self):
        return self.env.ref('base.in', raise_if_not_found=False) or self.env['res.country'].search([('code', '=', 'IN')], limit=1)

    # Primary Address fields
    street = fields.Char(string='Address Line 1')
    street2 = fields.Char(string='Address Line 2')
    city = fields.Char(string='City')
    district = fields.Char(string='District')
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
    branch_code = fields.Char(string='Branch Code (if multicampus)')

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
    contact_time = fields.Char(string='Preferred Contact Time')

    # Other Details
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
    ], string='Board')
    validation_start = fields.Date(string='Affiliation Start Date')
    validation_end = fields.Date(string='Affiliation Expiry Date')
    accreditation = fields.Char(string='Accreditation')
    medium = fields.Char(string='Medium of Instruction')
    residential = fields.Selection([
        ('boys', 'Boys'),
        ('girls', 'Girls'),
        ('coed', 'Co-ed / Both'),
        ('none', 'Day School / Non-Residential'),
    ], string='Residential')

    principal_name = fields.Char(string='Principal Name')
    principal_phone = fields.Char(string='Principal Phone')
    principal_email = fields.Char(string='Principal Email')
    vp_name = fields.Char(string='Vice Principal Name')
    vp_phone = fields.Char(string='Vice Principal Phone')
    vp_email = fields.Char(string='Vice Principal Email')
    capacity = fields.Integer(string='Total Student Capacity')
    area = fields.Char(string='Campus Area')
    logo = fields.Binary(string='Logo')
    facility_ids = fields.Many2many('stakeholder.facility', string='Facilities')

    # Billing Address fields
    billing_same_as_primary = fields.Boolean(string='Same as Primary Address', default=False)
    billing_street = fields.Char(string='Address Line 1')
    billing_street2 = fields.Char(string='Address Line 2')
    billing_city = fields.Char(string='City')
    billing_district = fields.Char(string='District')
    billing_state_id = fields.Many2one(
        'res.country.state',
        string='State',
        domain="[('country_id.code', '=', 'IN')]",
    )
    billing_country_id = fields.Many2one(
        'res.country',
        string='Country',
        default=_default_country_id,
        domain="[('code', '=', 'IN')]",
    )
    billing_zip = fields.Char(string='PIN Code')

    # Shipping Address fields
    shipping_same_as_primary = fields.Boolean(string='Same as Primary Address', default=False)
    shipping_street = fields.Char(string='Address Line 1')
    shipping_street2 = fields.Char(string='Address Line 2')
    shipping_city = fields.Char(string='City')
    shipping_district = fields.Char(string='District')
    shipping_state_id = fields.Many2one(
        'res.country.state',
        string='State',
        domain="[('country_id.code', '=', 'IN')]",
    )
    shipping_country_id = fields.Many2one(
        'res.country',
        string='Country',
        default=_default_country_id,
        domain="[('code', '=', 'IN')]",
    )
    shipping_zip = fields.Char(string='PIN Code')

    board_member_ids = fields.One2many('stakeholder.organisation.board.member', 'organisation_id', string='Executive')
    dept_head_ids = fields.One2many('stakeholder.organisation.dept.head', 'organisation_id', string='Academic')
    operation_member_ids = fields.One2many('stakeholder.organisation.operation.member', 'organisation_id', string='Operations')
    assoc_memberships_ids = fields.One2many('stakeholder.organisation.association.membership', 'organisation_id', string='Association Partners')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], string='Status', default='draft', required=True)
    partner_id = fields.Many2one('res.partner', string='Approved Partner', readonly=True)
    user_id = fields.Many2one('res.users', string='Related User', compute='_compute_user_id', store=True, readonly=False)

    @api.depends('partner_id', 'email')
    def _compute_user_id(self):
        for rec in self:
            user = False
            if rec.partner_id:
                user = self.env['res.users'].sudo().search([('partner_id', '=', rec.partner_id.id)], limit=1)
            if not user and rec.email:
                user = self.env['res.users'].sudo().search([('login', '=', rec.email)], limit=1) or \
                       self.env['res.users'].sudo().search([('email', '=', rec.email)], limit=1)
            rec.user_id = user

    @api.depends('parent_school_id')
    def _compute_is_branch(self):
        for rec in self:
            rec.is_branch = bool(rec.parent_school_id)

    @api.depends('child_school_ids')
    def _compute_branch_count(self):
        for rec in self:
            rec.branch_count = len(rec.child_school_ids)

    def action_view_branches(self):
        self.ensure_one()
        action = self.env.ref('stakeholder_registration.action_stakeholder_organisation').read()[0]
        action['domain'] = [('parent_school_id', '=', self.id)]
        action['context'] = {
            'default_parent_school_id': self.id,
            'default_parent_organisation_id': self.parent_organisation_id.id if self.parent_organisation_id else False,
        }
        return action

    def action_open_profile(self):
        org = self.env.user.organisation_id
        if not org or org.parent_school_id:
            main_org = self.env['stakeholder.organisation'].sudo().search([
                ('parent_school_id', '=', False),
                '|', '|', '|', '|', '|',
                ('partner_id', '=', self.env.user.partner_id.id),
                ('user_id', '=', self.env.user.id),
                ('partner_id.user_ids', 'in', [self.env.user.id]),
                ('create_uid', '=', self.env.user.id),
                ('email', '=', self.env.user.email),
                ('email', '=', self.env.user.login),
            ], limit=1)
            if main_org:
                org = main_org
        if not org:
            org = self.env['stakeholder.organisation'].sudo().search([
                '|', '|', '|', '|', '|',
                ('partner_id', '=', self.env.user.partner_id.id),
                ('user_id', '=', self.env.user.id),
                ('partner_id.user_ids', 'in', [self.env.user.id]),
                ('create_uid', '=', self.env.user.id),
                ('email', '=', self.env.user.email),
                ('email', '=', self.env.user.login),
            ], limit=1)
        if org and self.env.user.organisation_id != org:
            self.env.user.sudo().write({'organisation_id': org.id})

        form_view = self.env.ref('stakeholder_registration.view_stakeholder_organisation_form', raise_if_not_found=False)
        tree_view = self.env.ref('stakeholder_registration.view_stakeholder_organisation_tree', raise_if_not_found=False)
        views = []
        if form_view:
            views.append((form_view.id, 'form'))
        if tree_view:
            views.append((tree_view.id, 'list'))
        if org:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Profile',
                'res_model': 'stakeholder.organisation',
                'res_id': org.id,
                'view_mode': 'form,list',
                'views': views,
                'target': 'current',
                'context': {'create': True, 'delete': False},
            }
        return {
            'type': 'ir.actions.act_window',
            'name': 'Profile',
            'res_model': 'stakeholder.organisation',
            'view_mode': 'form,list',
            'views': [(form_view.id, 'form'), (tree_view.id, 'list')] if form_view else False,
            'target': 'current',
            'context': {
                'create': True,
                'delete': False,
                'default_name': self.env.user.name,
                'default_email': self.env.user.email or self.env.user.login,
                'default_user_id': self.env.user.id,
                'default_partner_id': self.env.user.partner_id.id,
            },
        }

    @api.depends('primary_contact_first_name', 'primary_contact_last_name')
    def _compute_contact_name(self):
        for rec in self:
            full_name = ' '.join(filter(None, [rec.primary_contact_first_name, rec.primary_contact_last_name])).strip()
            if full_name:
                rec.contact_name = full_name
            elif not rec.contact_name:
                rec.contact_name = False

    @api.depends('primary_contact_first_name', 'primary_contact_last_name', 'contact_phone')
    def _compute_contact_name_phone(self):
        for rec in self:
            name = ' '.join(filter(None, [rec.primary_contact_first_name, rec.primary_contact_last_name])).strip()
            phone = rec.contact_phone or ''
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

    @api.onchange('billing_state_id')
    def _onchange_billing_state_id(self):
        if self.billing_state_id and self.billing_state_id.country_id:
            self.billing_country_id = self.billing_state_id.country_id
        elif not self.billing_country_id:
            self.billing_country_id = self._default_country_id()

    @api.onchange('billing_country_id')
    def _onchange_billing_country_id(self):
        if self.billing_country_id and self.billing_state_id and self.billing_state_id.country_id != self.billing_country_id:
            self.billing_state_id = False

    @api.onchange('shipping_state_id')
    def _onchange_shipping_state_id(self):
        if self.shipping_state_id and self.shipping_state_id.country_id:
            self.shipping_country_id = self.shipping_state_id.country_id
        elif not self.shipping_country_id:
            self.shipping_country_id = self._default_country_id()

    @api.onchange('shipping_country_id')
    def _onchange_shipping_country_id(self):
        if self.shipping_country_id and self.shipping_state_id and self.shipping_state_id.country_id != self.shipping_country_id:
            self.shipping_state_id = False

    @api.model_create_multi
    def create(self, vals_list):
        india = self._default_country_id()
        assoc = self.env.user.association_id
        is_association_user = self.env.user.has_group('stakeholder_registration.group_association_user')
        is_school_user = self.env.user.has_group('stakeholder_registration.group_school_user') or self.env.user.user_category in ('school_college', 'school', 'college', 'academy')
        for vals in vals_list:
            if india:
                if not vals.get('country_id'):
                    vals['country_id'] = india.id
                if not vals.get('billing_country_id'):
                    vals['billing_country_id'] = india.id
                if not vals.get('shipping_country_id'):
                    vals['shipping_country_id'] = india.id
            if is_association_user and assoc:
                if not vals.get('parent_organisation_id') and not vals.get('association_ids'):
                    vals['association_ids'] = [Command.link(assoc.id)]
            if vals.get('parent_school_id') and not vals.get('parent_organisation_id'):
                parent_school = self.env['stakeholder.organisation'].sudo().browse(vals['parent_school_id'])
                if parent_school.parent_organisation_id:
                    vals['parent_organisation_id'] = parent_school.parent_organisation_id.id
            if is_school_user:
                if not vals.get('partner_id') and self.env.user.partner_id:
                    vals['partner_id'] = self.env.user.partner_id.id
                if not vals.get('user_id'):
                    vals['user_id'] = self.env.user.id
        records = super(StakeholderOrganisation, self.sudo()).create(vals_list)
        if is_school_user:
            for rec in records:
                if not self.env.user.organisation_id and not rec.parent_school_id:
                    self.env.user.sudo().write({'organisation_id': rec.id})
        return records

    def write(self, vals):
        return super(StakeholderOrganisation, self.sudo()).write(vals)

    def init(self):
        super().init()
        india = self._default_country_id()
        if india and sql.table_exists(self.env.cr, self._table):
            self.env.cr.execute(
                """UPDATE stakeholder_organisation 
                   SET country_id = COALESCE(country_id, %s),
                       billing_country_id = COALESCE(billing_country_id, %s),
                       shipping_country_id = COALESCE(shipping_country_id, %s)
                   WHERE country_id IS NULL OR billing_country_id IS NULL OR shipping_country_id IS NULL""",
                (india.id, india.id, india.id)
            )

    @api.onchange('billing_same_as_primary', 'street', 'street2', 'city', 'district', 'state_id', 'zip', 'country_id')
    def _onchange_billing_same_as_primary(self):
        if self.billing_same_as_primary:
            self.billing_street = self.street
            self.billing_street2 = self.street2
            self.billing_city = self.city
            self.billing_district = self.district
            self.billing_state_id = self.state_id
            self.billing_zip = self.zip
            self.billing_country_id = self.country_id

    @api.onchange('shipping_same_as_primary', 'street', 'street2', 'city', 'district', 'state_id', 'zip', 'country_id')
    def _onchange_shipping_same_as_primary(self):
        if self.shipping_same_as_primary:
            self.shipping_street = self.street
            self.shipping_street2 = self.street2
            self.shipping_city = self.city
            self.shipping_district = self.district
            self.shipping_state_id = self.state_id
            self.shipping_zip = self.zip
            self.shipping_country_id = self.country_id

    @api.onchange('affiliation_number')
    def _onchange_affiliation_number(self):
        if self.affiliation_number and not self.org_code:
            self.org_code = self.affiliation_number

    def action_approve(self):
        self.ensure_one()
        if not (self.env.user.has_group('stakeholder_registration.group_stakeholder_user') or 
                self.env.user.has_group('stakeholder_registration.group_association_user') or
                self.env.user.has_group('stakeholder_registration.group_school_user') or
                self.env.user.has_group('base.group_system')):
            raise UserError("You do not have rights to approve organisation registrations.")
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
            'user_category': self.category or 'school',
        }
        if partner:
            partner.sudo().write(vals)
        else:
            partner = partner_obj.sudo().create(vals)

        user = False
        if partner.email:
            user_obj = self.env['res.users'].sudo()
            existing_user = user_obj.search([('login', '=', partner.email)], limit=1)
            cat = self.category or 'school'
            group_user = self.env.ref('base.group_user', raise_if_not_found=False)
            if cat == 'honna_staff':
                target_group = self.env.ref('stakeholder_registration.group_stakeholder_user', raise_if_not_found=False)
            else:
                target_group = self.env.ref('stakeholder_registration.group_school_user', raise_if_not_found=False)
            if not existing_user:
                groups = [g.id for g in [group_user, target_group] if g]
                user = user_obj.create({
                    'name': self.contact_name or self.name or partner.name,
                    'login': partner.email,
                    'email': partner.email,
                    'phone': self.phone or partner.phone,
                    'partner_id': partner.id,
                    'group_ids': [(6, 0, groups)],
                    'share': False,
                    'user_category': cat,
                })
                try:
                    user.action_reset_password()
                except Exception:
                    pass
            else:
                user = existing_user
                user_write_vals = {'user_category': cat}
                if target_group and target_group not in existing_user.group_ids:
                    user_write_vals['group_ids'] = [(4, target_group.id)]
                existing_user.write(user_write_vals)

        for bm in self.board_member_ids:
            bm_name = bm.name or ' '.join(filter(None, [bm.first_name, bm.last_name])).strip() or 'Member'
            role_dict = dict(bm._fields['role'].selection) if hasattr(bm._fields['role'], 'selection') else {}
            role_label = role_dict.get(bm.role, bm.role) or bm.designation or 'Member'
            self.env['stakeholder.board.member'].sudo().create({
                'partner_id': partner.id,
                'name': bm_name,
                'designation': role_label,
                'phone': bm.phone,
                'email': bm.email,
            })
        for dh in self.dept_head_ids:
            dh_name = dh.name or ' '.join(filter(None, [dh.first_name, dh.last_name])).strip() or 'Department Head'
            role_dict = dict(dh._fields['role'].selection) if hasattr(dh._fields['role'], 'selection') else {}
            role_label = role_dict.get(dh.role, dh.role) or dh.designation or 'Department Head'
            self.env['stakeholder.dept.head'].sudo().create({
                'partner_id': partner.id,
                'name': dh_name,
                'designation': role_label,
                'phone': dh.phone,
                'email': dh.email,
            })
        for op in self.operation_member_ids:
            op_name = op.name or ' '.join(filter(None, [op.first_name, op.last_name])).strip() or 'Operations Member'
            role_dict = dict(op._fields['role'].selection) if hasattr(op._fields['role'], 'selection') else {}
            role_label = role_dict.get(op.role, op.role) or op.designation or 'Operations Member'
            self.env['stakeholder.dept.head'].sudo().create({
                'partner_id': partner.id,
                'name': op_name,
                'designation': role_label,
                'phone': op.phone,
                'email': op.email,
            })
        for assoc in self.assoc_memberships_ids:
            self.env['stakeholder.organisation.association'].sudo().create({
                'partner_id': partner.id,
                'association_id': assoc.association_id.id,
                'membership_number': assoc.membership_number,
                'expiry_date': assoc.expiry_date,
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
            raise UserError("You do not have rights to reject organisation registrations.")
        self.sudo().write({'state': 'rejected'})

    def action_draft(self):
        self.ensure_one()
        if not (self.env.user.has_group('stakeholder_registration.group_stakeholder_user') or 
                self.env.user.has_group('stakeholder_registration.group_association_user') or
                self.env.user.has_group('stakeholder_registration.group_school_user') or
                self.env.user.has_group('base.group_system')):
            raise UserError("You do not have rights to reset organisation registrations to draft.")
        self.sudo().write({'state': 'draft'})

class StakeholderOrganisationBoardMember(models.Model):
    _name = 'stakeholder.organisation.board.member'
    _description = 'Organisation Executive Member'

    organisation_id = fields.Many2one('stakeholder.organisation', string='Organisation', ondelete='cascade')
    first_name = fields.Char(string='First Name')
    last_name = fields.Char(string='Last Name')
    name = fields.Char(string='Name', compute='_compute_name', store=True, readonly=False)
    role = fields.Selection(EXECUTIVE_ROLE_SELECTION, string='Role')
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
            self.designation = dict(EXECUTIVE_ROLE_SELECTION).get(self.role, self.role)

    def init(self):
        super().init()
        if sql.table_exists(self.env.cr, self._table) and sql.column_exists(self.env.cr, self._table, 'role'):
            self.env.cr.execute("""
                UPDATE stakeholder_organisation_board_member
                SET role = CASE 
                    WHEN LOWER(role) LIKE '%%chair%%' THEN 'chairman'
                    WHEN LOWER(role) LIKE '%%sec%%' THEN 'secretary'
                    WHEN LOWER(role) LIKE '%%treas%%' THEN 'treasurer'
                    WHEN LOWER(role) LIKE '%%commit%%' THEN 'committee_members'
                    WHEN LOWER(role) LIKE '%%vice%%' OR LOWER(role) LIKE '%%vp%%' THEN 'vice_principal'
                    WHEN LOWER(role) LIKE '%%princ%%' THEN 'principal'
                    ELSE LOWER(REPLACE(role, ' ', '_'))
                END
                WHERE role IS NOT NULL;
            """)

class StakeholderOrganisationDeptHead(models.Model):
    _name = 'stakeholder.organisation.dept.head'
    _description = 'Organisation Academic Team Member'

    organisation_id = fields.Many2one('stakeholder.organisation', string='Organisation', ondelete='cascade')
    first_name = fields.Char(string='First Name')
    last_name = fields.Char(string='Last Name')
    name = fields.Char(string='Name', compute='_compute_name', store=True, readonly=False)
    role = fields.Selection(ACADEMIC_ROLE_SELECTION, string='Role')
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
            self.designation = dict(ACADEMIC_ROLE_SELECTION).get(self.role, self.role)

    def init(self):
        super().init()
        if sql.table_exists(self.env.cr, self._table) and sql.column_exists(self.env.cr, self._table, 'role'):
            self.env.cr.execute("""
                UPDATE stakeholder_organisation_dept_head
                SET role = CASE 
                    WHEN LOWER(role) LIKE '%%coord%%' THEN 'coordinator'
                    WHEN LOWER(role) LIKE '%%teach%%' THEN 'teachers'
                    WHEN LOWER(role) LIKE '%%stem%%' THEN 'stem_instructor'
                    WHEN LOWER(role) LIKE '%%lab%%' THEN 'lab_instructor'
                    ELSE LOWER(REPLACE(role, ' ', '_'))
                END
                WHERE role IS NOT NULL;
            """)

class StakeholderOrganisationOperationMember(models.Model):
    _name = 'stakeholder.organisation.operation.member'
    _description = 'Organisation Operations Team Member'

    organisation_id = fields.Many2one('stakeholder.organisation', string='Organisation', ondelete='cascade')
    first_name = fields.Char(string='First Name')
    last_name = fields.Char(string='Last Name')
    name = fields.Char(string='Name', compute='_compute_name', store=True, readonly=False)
    role = fields.Selection(OPERATIONS_ROLE_SELECTION, string='Role')
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
            self.designation = dict(OPERATIONS_ROLE_SELECTION).get(self.role, self.role)

class StakeholderOrganisationAssociationMembership(models.Model):
    _name = 'stakeholder.organisation.association.membership'
    _description = 'Organisation Association Membership'

    organisation_id = fields.Many2one(
        'stakeholder.organisation',
        string='Organisation',
        ondelete='cascade',
    )
    association_id = fields.Many2one(
        'stakeholder.association',
        string='Association',
        required=True,
        ondelete='restrict',
        index=True,
    )
    name = fields.Char(
        string='Association Name',
        related='association_id.name',
        store=True,
        readonly=True,
    )
    membership_number = fields.Char(string='Membership Number')
    expiry_date = fields.Date(string='Expiry Date')
