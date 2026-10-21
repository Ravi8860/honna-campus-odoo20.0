# -*- coding: utf-8 -*-
from odoo import api, fields, models, Command


USER_CATEGORY_SELECTION = [
    ('association', 'Organisation'),
    ('school', 'School'),
    ('parent', 'Parent'),
    ('academy', 'Academy'),
    ('student', 'Student'),
    ('partner', 'Vendor'),
]


class ResUsers(models.Model):
    _inherit = 'res.users'

    user_category = fields.Selection(
        selection=USER_CATEGORY_SELECTION,
        string='User Category',
        index=True,
        help='Category selected during website registration or assigned by administrator.',
    )


    is_association = fields.Boolean(
        string='Is Organisation User',
        compute='_compute_is_association',
        inverse='_inverse_is_association',
        help='When enabled, the user belongs to Organisation Users and can access '
             'Organisation and School only (Student and Parent menus are hidden).',
    )

    is_school = fields.Boolean(
        string='Is School User',
        compute='_compute_is_school',
        inverse='_inverse_is_school',
        help='When enabled, the user belongs to School Users and can access '
             'School and Profile only (Organisation, Student and Parent menus are hidden).',
    )

    association_id = fields.Many2one(
        'stakeholder.association',
        string='Related Association',
        compute='_compute_association_id',
        store=True,
        readonly=False,
    )

    organisation_id = fields.Many2one(
        'stakeholder.organisation',
        string='Related School / Organisation',
        compute='_compute_organisation_id',
        store=True,
        readonly=False,
    )

    @api.depends('partner_id', 'email', 'login', 'name')
    def _compute_association_id(self):
        for user in self:
            assoc = False
            if user.partner_id:
                assoc = self.env['stakeholder.association'].sudo().search([
                    ('partner_id', '=', user.partner_id.id)
                ], limit=1)
            if not assoc and user.email:
                assoc = self.env['stakeholder.association'].sudo().search([
                    ('email', '=', user.email)
                ], limit=1)
            if not assoc and user.login:
                assoc = self.env['stakeholder.association'].sudo().search([
                    ('email', '=', user.login)
                ], limit=1)
            if not assoc and user.name:
                assoc = self.env['stakeholder.association'].sudo().search([
                    ('name', '=ilike', user.name)
                ], limit=1)
            if not assoc and user.partner_id and user.partner_id.name and user.partner_id.name != user.name:
                assoc = self.env['stakeholder.association'].sudo().search([
                    ('name', '=ilike', user.partner_id.name)
                ], limit=1)
            if not assoc:
                assoc = self.env['stakeholder.association'].sudo().search([
                    ('user_id', '=', user.id)
                ], limit=1)
            user.association_id = assoc

    @api.depends('partner_id', 'email', 'login')
    def _compute_organisation_id(self):
        for user in self:
            org = False
            if user.partner_id:
                org = self.env['stakeholder.organisation'].sudo().search([
                    ('partner_id', '=', user.partner_id.id),
                    ('parent_school_id', '=', False),
                ], limit=1) or self.env['stakeholder.organisation'].sudo().search([
                    ('partner_id', '=', user.partner_id.id),
                ], limit=1)
            if not org and user.email:
                org = self.env['stakeholder.organisation'].sudo().search([
                    ('email', '=', user.email),
                    ('parent_school_id', '=', False),
                ], limit=1) or self.env['stakeholder.organisation'].sudo().search([
                    ('email', '=', user.email),
                ], limit=1)
            if not org and user.login:
                org = self.env['stakeholder.organisation'].sudo().search([
                    ('email', '=', user.login),
                    ('parent_school_id', '=', False),
                ], limit=1) or self.env['stakeholder.organisation'].sudo().search([
                    ('email', '=', user.login),
                ], limit=1)
            if not org:
                org = self.env['stakeholder.organisation'].sudo().search([
                    ('user_id', '=', user.id),
                    ('parent_school_id', '=', False),
                ], limit=1) or self.env['stakeholder.organisation'].sudo().search([
                    ('user_id', '=', user.id),
                ], limit=1)
            if not org:
                org = self.env['stakeholder.organisation'].sudo().search([
                    ('create_uid', '=', user.id),
                    ('parent_school_id', '=', False),
                ], limit=1) or self.env['stakeholder.organisation'].sudo().search([
                    ('create_uid', '=', user.id),
                ], limit=1)
            user.organisation_id = org

    @api.onchange('user_category')
    def _onchange_user_category(self):
        if self.user_category == 'association':
            self.is_association = True
            self.is_school = False
        elif self.user_category == 'school':
            self.is_school = True
            self.is_association = False
        elif self.user_category:
            self.is_association = False
            self.is_school = False

    @api.depends('group_ids')
    def _compute_is_association(self):
        group = self.env.ref(
            'stakeholder_registration.group_association_user',
            raise_if_not_found=False,
        )
        for user in self:
            user.is_association = bool(group and group in user.all_group_ids)

    def _inverse_is_association(self):
        association_group = self.env.ref('stakeholder_registration.group_association_user')
        school_group = self.env.ref('stakeholder_registration.group_school_user', raise_if_not_found=False)
        stakeholder_group = self.env.ref('stakeholder_registration.group_stakeholder_user', raise_if_not_found=False)
        for user in self:
            commands = []
            if user.is_association:
                commands.append(Command.link(association_group.id))
                if school_group:
                    commands.append(Command.unlink(school_group.id))
                if stakeholder_group:
                    commands.append(Command.unlink(stakeholder_group.id))
                if not user.user_category:
                    user.user_category = 'association'
            else:
                commands.append(Command.unlink(association_group.id))
            if commands:
                user.sudo().write({'group_ids': commands})
        self._sync_association_profile()

    def _ensure_main_company_access(self):
        """Keep Association/School users on main company so Contacts multi-company rules pass."""
        main = self.env.ref('base.main_company', raise_if_not_found=False)
        if not main:
            return
        assoc_group = self.env.ref('stakeholder_registration.group_association_user', raise_if_not_found=False)
        school_group = self.env.ref('stakeholder_registration.group_school_user', raise_if_not_found=False)
        for user in self:
            is_restricted = (
                (assoc_group and assoc_group in user.all_group_ids)
                or (school_group and school_group in user.all_group_ids)
                or user.user_category == 'association'
                or getattr(user, 'is_association', False)
                or getattr(user, 'is_school', False)
            )
            if not is_restricted or user.has_group('stakeholder_registration.group_stakeholder_user'):
                continue
            vals = {}
            if user.company_id != main:
                vals['company_id'] = main.id
            if main not in user.company_ids:
                vals['company_ids'] = [Command.link(main.id)]
            if vals:
                user.sudo().with_context(skip_sync_assoc=True).write(vals)

    def _sync_association_profile(self):
        if self.env.context.get('skip_sync_assoc'):
            return
        assoc_group = self.env.ref('stakeholder_registration.group_association_user', raise_if_not_found=False)
        self._ensure_main_company_access()
        for user in self:
            is_assoc = (
                user.user_category == 'association' or
                user.is_association or
                bool(assoc_group and assoc_group in user.all_group_ids)
            )
            if not is_assoc:
                continue

            assoc = user.association_id
            if not assoc:
                domain_parts = []
                if user.partner_id:
                    domain_parts.append(('partner_id', '=', user.partner_id.id))
                domain_parts.append(('user_id', '=', user.id))
                if user.email:
                    domain_parts.append(('email', '=', user.email))
                if user.login and '@' in user.login:
                    domain_parts.append(('email', '=', user.login))
                if user.name:
                    domain_parts.append(('name', '=ilike', user.name))
                if user.partner_id and user.partner_id.name and user.partner_id.name != user.name:
                    domain_parts.append(('name', '=ilike', user.partner_id.name))

                if domain_parts:
                    search_domain = ['|'] * (len(domain_parts) - 1) + domain_parts
                    assoc = self.env['stakeholder.association'].sudo().search(search_domain, limit=1)

            if not assoc:
                assoc = self.env['stakeholder.association'].sudo().create({
                    'name': user.name or (user.partner_id.name if user.partner_id else 'Association Profile'),
                    'partner_id': user.partner_id.id if user.partner_id else False,
                    'user_id': user.id,
                    'email': user.email or (user.login if '@' in (user.login or '') else False),
                    'phone': user.partner_id.phone if user.partner_id else False,
                    'state': 'draft',
                })

            vals = {}
            if not assoc.user_id or assoc.user_id != user:
                vals['user_id'] = user.id
            if user.partner_id and (not assoc.partner_id or assoc.partner_id != user.partner_id):
                vals['partner_id'] = user.partner_id.id
            if user.email and not assoc.email:
                vals['email'] = user.email
            if vals:
                assoc.sudo().with_context(skip_sync_assoc=True).write(vals)

            if user.association_id != assoc:
                user.sudo().with_context(skip_sync_assoc=True).write({'association_id': assoc.id})

    @api.depends('group_ids')
    def _compute_is_school(self):
        group = self.env.ref(
            'stakeholder_registration.group_school_user',
            raise_if_not_found=False,
        )
        for user in self:
            user.is_school = bool(group and group in user.all_group_ids)

    def _inverse_is_school(self):
        school_group = self.env.ref('stakeholder_registration.group_school_user')
        association_group = self.env.ref('stakeholder_registration.group_association_user', raise_if_not_found=False)
        stakeholder_group = self.env.ref('stakeholder_registration.group_stakeholder_user', raise_if_not_found=False)
        for user in self:
            commands = []
            if user.is_school:
                commands.append(Command.link(school_group.id))
                if association_group:
                    commands.append(Command.unlink(association_group.id))
                if stakeholder_group:
                    commands.append(Command.unlink(stakeholder_group.id))
                if not user.user_category:
                    user.user_category = 'school'
            else:
                commands.append(Command.unlink(school_group.id))
            if commands:
                user.sudo().write({'group_ids': commands})

    @api.model_create_multi
    def create(self, vals_list):
        school_group = self.env.ref('stakeholder_registration.group_school_user', raise_if_not_found=False)
        assoc_group = self.env.ref('stakeholder_registration.group_association_user', raise_if_not_found=False)
        honna_group = self.env.ref('stakeholder_registration.group_stakeholder_user', raise_if_not_found=False)
        for vals in vals_list:
            if vals.get('user_category') == 'honna_staff' and honna_group:
                existing = vals.get('group_ids', [])
                vals['group_ids'] = existing + [Command.link(honna_group.id)]
            elif vals.get('user_category') in ('school_college', 'school', 'college', 'academy', 'partner', 'others', 'parent', 'student') and school_group:
                existing = vals.get('group_ids', [])
                if honna_group:
                    existing = [cmd for cmd in existing if not (isinstance(cmd, (tuple, list)) and len(cmd) >= 2 and cmd[1] == honna_group.id)]
                    existing.append(Command.unlink(honna_group.id))
                vals['group_ids'] = existing + [Command.link(school_group.id)]
            elif vals.get('user_category') == 'association' and assoc_group:
                existing = vals.get('group_ids', [])
                vals['group_ids'] = existing + [Command.link(assoc_group.id)]
        users = super().create(vals_list)
        for u in users:
            if u.user_category and u.partner_id and u.partner_id.user_category != u.user_category:
                u.partner_id.sudo().write({'user_category': u.user_category})
        users._sync_association_profile()
        return users

    def write(self, vals):
        res = super().write(vals)
        if 'user_category' in vals:
            for user in self:
                if user.user_category and user.partner_id and user.partner_id.user_category != user.user_category:
                    user.partner_id.sudo().write({'user_category': user.user_category})
        if 'user_category' in vals:
            school_group = self.env.ref('stakeholder_registration.group_school_user', raise_if_not_found=False)
            assoc_group = self.env.ref('stakeholder_registration.group_association_user', raise_if_not_found=False)
            honna_group = self.env.ref('stakeholder_registration.group_stakeholder_user', raise_if_not_found=False)
            for user in self:
                if user.user_category == 'honna_staff' and honna_group:
                    unlink_cmds = []
                    if school_group and school_group in user.group_ids:
                        unlink_cmds.append(Command.unlink(school_group.id))
                    if assoc_group and assoc_group in user.group_ids:
                        unlink_cmds.append(Command.unlink(assoc_group.id))
                    if honna_group not in user.group_ids or unlink_cmds:
                        user.sudo().write({'group_ids': [Command.link(honna_group.id)] + unlink_cmds})
                elif user.user_category in ('school_college', 'school', 'college', 'academy', 'partner', 'others', 'parent', 'student') and school_group:
                    unlink_cmds = []
                    if honna_group and honna_group in user.group_ids:
                        unlink_cmds.append(Command.unlink(honna_group.id))
                    if assoc_group and assoc_group in user.group_ids:
                        unlink_cmds.append(Command.unlink(assoc_group.id))
                    if school_group not in user.group_ids or unlink_cmds:
                        user.sudo().write({'group_ids': [Command.link(school_group.id)] + unlink_cmds})
                elif user.user_category == 'association' and assoc_group:
                    unlink_cmds = []
                    if honna_group and honna_group in user.group_ids:
                        unlink_cmds.append(Command.unlink(honna_group.id))
                    if school_group and school_group in user.group_ids:
                        unlink_cmds.append(Command.unlink(school_group.id))
                    if assoc_group not in user.group_ids or unlink_cmds:
                        user.sudo().write({'group_ids': [Command.link(assoc_group.id)] + unlink_cmds})
        if any(f in vals for f in ('user_category', 'group_ids', 'name', 'email', 'login', 'partner_id', 'is_association')):
            self._sync_association_profile()
        return res


    @api.model
    def _init_association_users(self):
        """Ensure all users marked as Association have a linked Association profile and correct groups."""
        assoc_group = self.env.ref('stakeholder_registration.group_association_user', raise_if_not_found=False)
        school_group = self.env.ref('stakeholder_registration.group_school_user', raise_if_not_found=False)
        honna_group = self.env.ref('stakeholder_registration.group_stakeholder_user', raise_if_not_found=False)

        users = self.sudo().search([
            '|',
            ('user_category', '=', 'association'),
            ('group_ids', 'in', [assoc_group.id] if assoc_group else [])
        ])
        for user in users:
            vals = {}
            if user.user_category != 'association':
                vals['user_category'] = 'association'
            cmds = []
            if assoc_group and assoc_group not in user.group_ids:
                cmds.append(Command.link(assoc_group.id))
            if school_group and school_group in user.group_ids:
                cmds.append(Command.unlink(school_group.id))
            if honna_group and honna_group in user.group_ids:
                cmds.append(Command.unlink(honna_group.id))
            if cmds:
                vals['group_ids'] = cmds
            if vals:
                user.sudo().write(vals)
        school_users = self.sudo().search([
            ('group_ids', 'in', [school_group.id]),
        ]) if school_group else self.browse()

        # Ensure non-staff users (e.g. academy, school, partner) do not have full access group
        if honna_group and school_group:
            non_staff_users = self.sudo().search([
                ('user_category', 'in', ('school_college', 'school', 'college', 'academy', 'partner', 'others', 'parent', 'student')),
            ])
            admin_user = self.env.ref('base.user_admin', raise_if_not_found=False)
            for non_staff in non_staff_users:
                if admin_user and non_staff.id == admin_user.id:
                    continue
                cmds = []
                if honna_group in non_staff.group_ids:
                    cmds.append(Command.unlink(honna_group.id))
                if school_group not in non_staff.group_ids:
                    cmds.append(Command.link(school_group.id))
                if cmds:
                    non_staff.sudo().write({'group_ids': cmds})

        (users | school_users)._ensure_main_company_access()
        users._sync_association_profile()

        # Clean up legacy duplicate unrestricted ir.access records that conflict with domain rules
        obsolete_xml_ids = [
            'stakeholder_registration.access_stakeholder_organisation_association_user',
            'stakeholder_registration.access_stakeholder_association_association_user',
            'stakeholder_registration.access_stakeholder_association_member_association_user',
            'stakeholder_registration.access_stakeholder_organisation_school_user',
            'stakeholder_registration.rule_res_partner_association_user_write',
            'stakeholder_registration.access_stakeholder_association_school_user',
            'stakeholder_registration.access_stakeholder_association_member_school_user',
        ]
        for xml_id in obsolete_xml_ids:
            rec = self.env.ref(xml_id, raise_if_not_found=False)
            if rec and rec._name == 'ir.access':
                rec.sudo().unlink()



