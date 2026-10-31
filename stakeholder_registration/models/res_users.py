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
        search='_search_is_association',
        help='When enabled, the user belongs to Organisation Users and can access '
             'Organisation and School only (Student and Parent menus are hidden).',
    )

    is_school = fields.Boolean(
        string='Is School User',
        compute='_compute_is_school',
        inverse='_inverse_is_school',
        search='_search_is_school',
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
            # Management Member mapping
            if not assoc and user.partner_id:
                mem = self.env['stakeholder.association.member'].sudo().search([
                    ('name', '=', user.partner_id.id),
                    ('association_id', '!=', False),
                ], limit=1)
                if mem:
                    assoc = mem.association_id
            if not assoc and user.email:
                mem = self.env['stakeholder.association.member'].sudo().search([
                    ('email', '=', user.email),
                    ('association_id', '!=', False),
                ], limit=1)
                if mem:
                    assoc = mem.association_id
            if not assoc and user.login and '@' in user.login:
                mem = self.env['stakeholder.association.member'].sudo().search([
                    ('email', '=', user.login),
                    ('association_id', '!=', False),
                ], limit=1)
                if mem:
                    assoc = mem.association_id
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

    def _search_is_association(self, operator, value):
        assoc_group = self.env.ref('stakeholder_registration.group_association_user', raise_if_not_found=False)
        if not assoc_group:
            return []
        if (operator in ('=', '!=') and value) or (operator == 'in' and True in value):
            pos_domain = [('all_group_ids', 'in', [assoc_group.id])]
            return pos_domain if operator in ('=', 'in') else ['!'] + pos_domain
        pos_domain = [('all_group_ids', 'not in', [assoc_group.id])]
        return pos_domain if operator in ('=', 'in') else ['!'] + pos_domain

    def _inverse_is_association(self):
        association_group = self.env.ref('stakeholder_registration.group_association_user')
        school_group = self.env.ref('stakeholder_registration.group_school_user', raise_if_not_found=False)
        stakeholder_group = self.env.ref('stakeholder_registration.group_stakeholder_user', raise_if_not_found=False)
        crm_salesman_group = self.env.ref('sales_team.group_sale_salesman', raise_if_not_found=False)
        crm_sales_all_group = self.env.ref('sales_team.group_sale_salesman_all_leads', raise_if_not_found=False)
        crm_lead_group = self.env.ref('crm.group_use_lead', raise_if_not_found=False)
        slides_group = self.env.ref('website_slides.group_website_slides_officer', raise_if_not_found=False)
        survey_group = self.env.ref('survey.group_survey_user', raise_if_not_found=False)
        default_feature_groups = [g for g in (crm_salesman_group, crm_sales_all_group, crm_lead_group, slides_group, survey_group) if g]
        crm_root = self.env.ref('crm.crm_menu_root', raise_if_not_found=False)
        survey_root = self.env.ref('survey.menu_surveys', raise_if_not_found=False)
        slides_root = self.env.ref('website_slides.website_slides_menu_root', raise_if_not_found=False)
        feature_menus = [m for m in (crm_root, survey_root, slides_root) if m]
        portal_group = self.env.ref('base.group_portal', raise_if_not_found=False)
        group_user = self.env.ref('base.group_user', raise_if_not_found=False)
        for user in self:
            commands = []
            vals = {}
            if user.is_association:
                if portal_group and portal_group in user.group_ids:
                    commands.append(Command.unlink(portal_group.id))
                    if group_user and group_user not in user.group_ids:
                        commands.append(Command.link(group_user.id))
                    vals['share'] = False
                commands.append(Command.link(association_group.id))
                for g in default_feature_groups:
                    if g not in user.group_ids:
                        commands.append(Command.link(g.id))
                if school_group:
                    commands.append(Command.unlink(school_group.id))
                if stakeholder_group:
                    commands.append(Command.unlink(stakeholder_group.id))
                if not user.user_category:
                    user.user_category = 'association'
                if hasattr(user, 'hide_menu_ids') and feature_menus:
                    unhide = [m for m in feature_menus if m in user.hide_menu_ids]
                    if unhide:
                        vals['hide_menu_ids'] = [Command.unlink(m.id) for m in unhide]
            else:
                commands.append(Command.unlink(association_group.id))
            if commands:
                vals['group_ids'] = commands
            if vals:
                user.sudo().write(vals)
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
            portal_group = self.env.ref('base.group_portal', raise_if_not_found=False)
            if portal_group and portal_group in user.group_ids:
                continue
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

            # Check Management Member mapping before creating new profile
            if not assoc and user.partner_id:
                mem = self.env['stakeholder.association.member'].sudo().search([
                    ('name', '=', user.partner_id.id),
                    ('association_id', '!=', False),
                ], limit=1)
                if mem:
                    assoc = mem.association_id
            if not assoc and user.email:
                mem = self.env['stakeholder.association.member'].sudo().search([
                    ('email', '=', user.email),
                    ('association_id', '!=', False),
                ], limit=1)
                if mem:
                    assoc = mem.association_id
            if not assoc and user.login and '@' in user.login:
                mem = self.env['stakeholder.association.member'].sudo().search([
                    ('email', '=', user.login),
                    ('association_id', '!=', False),
                ], limit=1)
                if mem:
                    assoc = mem.association_id

            if not assoc:
                assoc = self.env['stakeholder.association'].sudo().create({
                    'name': user.name or (user.partner_id.name if user.partner_id else 'Association Profile'),
                    'partner_id': user.partner_id.id if user.partner_id else False,
                    'user_id': user.id,
                    'email': user.email or (user.login if '@' in (user.login or '') else False),
                    'phone': user.partner_id.phone if user.partner_id else False,
                    'state': 'draft',
                })

            is_member = False
            if assoc:
                is_member = bool(
                    (user.partner_id and user.partner_id.id in assoc.member_ids.mapped('name.id'))
                    or (user.email and user.email in assoc.member_ids.mapped('email'))
                    or (user.login and user.login in assoc.member_ids.mapped('email'))
                )

            vals = {}
            if not is_member:
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

    def _search_is_school(self, operator, value):
        school_group = self.env.ref('stakeholder_registration.group_school_user', raise_if_not_found=False)
        if not school_group:
            return []
        if (operator in ('=', '!=') and value) or (operator == 'in' and True in value):
            pos_domain = [('all_group_ids', 'in', [school_group.id])]
            return pos_domain if operator in ('=', 'in') else ['!'] + pos_domain
        pos_domain = [('all_group_ids', 'not in', [school_group.id])]
        return pos_domain if operator in ('=', 'in') else ['!'] + pos_domain

    def _inverse_is_school(self):
        school_group = self.env.ref('stakeholder_registration.group_school_user')
        association_group = self.env.ref('stakeholder_registration.group_association_user', raise_if_not_found=False)
        stakeholder_group = self.env.ref('stakeholder_registration.group_stakeholder_user', raise_if_not_found=False)
        portal_group = self.env.ref('base.group_portal', raise_if_not_found=False)
        for user in self:
            if portal_group and portal_group in user.group_ids:
                continue
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
        crm_salesman_group = self.env.ref('sales_team.group_sale_salesman', raise_if_not_found=False)
        crm_sales_all_group = self.env.ref('sales_team.group_sale_salesman_all_leads', raise_if_not_found=False)
        crm_lead_group = self.env.ref('crm.group_use_lead', raise_if_not_found=False)
        slides_group = self.env.ref('website_slides.group_website_slides_officer', raise_if_not_found=False)
        survey_group = self.env.ref('survey.group_survey_user', raise_if_not_found=False)
        default_feature_groups = [g for g in (crm_salesman_group, crm_sales_all_group, crm_lead_group, slides_group, survey_group) if g]
        for vals in vals_list:
            if vals.get('user_category') == 'honna_staff' and honna_group:
                existing = vals.get('group_ids', [])
                vals['group_ids'] = existing + [Command.link(honna_group.id)]
            elif vals.get('user_category') in ('school_college', 'school', 'college', 'academy', 'partner', 'others', 'parent', 'student') and school_group:
                portal_group = self.env.ref('base.group_portal', raise_if_not_found=False)
                existing = vals.get('group_ids', [])
                has_portal = portal_group and any(
                    isinstance(cmd, (tuple, list)) and len(cmd) >= 2 and cmd[0] in (4, 6) and (
                        portal_group.id in (cmd[2] if cmd[0] == 6 else [cmd[1]])
                    ) for cmd in existing
                )
                if not has_portal:
                    if honna_group:
                        existing = [cmd for cmd in existing if not (isinstance(cmd, (tuple, list)) and len(cmd) >= 2 and cmd[1] == honna_group.id)]
                        existing.append(Command.unlink(honna_group.id))
                    add_cmds = [Command.link(school_group.id)]
                    if vals.get('user_category') == 'academy':
                        add_cmds += [Command.link(g.id) for g in default_feature_groups]
                    vals['group_ids'] = existing + add_cmds
            elif vals.get('user_category') == 'association' and assoc_group:
                group_user = self.env.ref('base.group_user', raise_if_not_found=False)
                portal_group = self.env.ref('base.group_portal', raise_if_not_found=False)
                existing = vals.get('group_ids', [])
                if portal_group:
                    existing = [cmd for cmd in existing if not (isinstance(cmd, (tuple, list)) and len(cmd) >= 2 and (portal_group.id in (cmd[2] if cmd[0] == 6 else [cmd[1]])))]
                add_cmds = [Command.link(assoc_group.id)] + [Command.link(g.id) for g in default_feature_groups]
                if group_user:
                    add_cmds.append(Command.link(group_user.id))
                vals['group_ids'] = existing + add_cmds
                vals['share'] = False
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
            crm_salesman_group = self.env.ref('sales_team.group_sale_salesman', raise_if_not_found=False)
            crm_sales_all_group = self.env.ref('sales_team.group_sale_salesman_all_leads', raise_if_not_found=False)
            crm_lead_group = self.env.ref('crm.group_use_lead', raise_if_not_found=False)
            slides_group = self.env.ref('website_slides.group_website_slides_officer', raise_if_not_found=False)
            survey_group = self.env.ref('survey.group_survey_user', raise_if_not_found=False)
            default_feature_groups = [g for g in (crm_salesman_group, crm_sales_all_group, crm_lead_group, slides_group, survey_group) if g]
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
                    portal_group = self.env.ref('base.group_portal', raise_if_not_found=False)
                    if portal_group and portal_group in user.group_ids:
                        continue
                    unlink_cmds = []
                    if honna_group and honna_group in user.group_ids:
                        unlink_cmds.append(Command.unlink(honna_group.id))
                    if assoc_group and assoc_group in user.group_ids:
                        unlink_cmds.append(Command.unlink(assoc_group.id))
                    link_cmds = [Command.link(school_group.id)] if school_group not in user.group_ids else []
                    if user.user_category == 'academy':
                        link_cmds += [Command.link(g.id) for g in default_feature_groups if g not in user.group_ids]
                    if link_cmds or unlink_cmds:
                        user.sudo().write({'group_ids': link_cmds + unlink_cmds})
                elif user.user_category == 'association' and assoc_group:
                    portal_group = self.env.ref('base.group_portal', raise_if_not_found=False)
                    group_user = self.env.ref('base.group_user', raise_if_not_found=False)
                    unlink_cmds = []
                    link_cmds = []
                    user_write_vals = {}
                    if portal_group and portal_group in user.group_ids:
                        unlink_cmds.append(Command.unlink(portal_group.id))
                        if group_user and group_user not in user.group_ids:
                            link_cmds.append(Command.link(group_user.id))
                        user_write_vals['share'] = False
                    if honna_group and honna_group in user.group_ids:
                        unlink_cmds.append(Command.unlink(honna_group.id))
                    if school_group and school_group in user.group_ids:
                        unlink_cmds.append(Command.unlink(school_group.id))
                    if assoc_group not in user.group_ids:
                        link_cmds.append(Command.link(assoc_group.id))
                    link_cmds += [Command.link(g.id) for g in default_feature_groups if g not in user.group_ids]
                    if link_cmds or unlink_cmds:
                        user_write_vals['group_ids'] = link_cmds + unlink_cmds
                    if user_write_vals:
                        user.sudo().write(user_write_vals)
        if any(f in vals for f in ('user_category', 'group_ids', 'name', 'email', 'login', 'partner_id', 'is_association')):
            self._sync_association_profile()
        return res


    def _check_and_sync_management_member(self):
        assoc_group = self.env.ref('stakeholder_registration.group_association_user', raise_if_not_found=False)
        default_feature_groups = [
            self.env.ref(xmlid, raise_if_not_found=False)
            for xmlid in (
                'sales_team.group_sale_salesman',
                'sales_team.group_sale_salesman_all_leads',
                'crm.group_use_lead',
                'website_slides.group_website_slides_officer',
                'survey.group_survey_user',
            )
        ]
        default_feature_groups = [g for g in default_feature_groups if g]

        for user in self:
            if user._is_system():
                continue
            assoc = user.association_id
            if not assoc:
                member = False
                if user.partner_id:
                    member = self.env['stakeholder.association.member'].sudo().search([
                        ('name', '=', user.partner_id.id),
                        ('association_id', '!=', False),
                    ], limit=1)
                if not member and user.email:
                    member = self.env['stakeholder.association.member'].sudo().search([
                        ('email', '=', user.email),
                        ('association_id', '!=', False),
                    ], limit=1)
                if not member and user.login and '@' in user.login:
                    member = self.env['stakeholder.association.member'].sudo().search([
                        ('email', '=', user.login),
                        ('association_id', '!=', False),
                    ], limit=1)
                if member:
                    assoc = member.association_id
            if assoc or user.user_category == 'association' or getattr(user, 'is_association', False):
                vals = {}
                if assoc and user.association_id != assoc:
                    vals['association_id'] = assoc.id
                portal_group = self.env.ref('base.group_portal', raise_if_not_found=False)
                group_user = self.env.ref('base.group_user', raise_if_not_found=False)
                is_portal = bool(portal_group and portal_group in user.group_ids)
                cmds = []
                if is_portal:
                    cmds.append(Command.unlink(portal_group.id))
                    if group_user and group_user not in user.group_ids:
                        cmds.append(Command.link(group_user.id))
                    vals['share'] = False
                if not user.user_category:
                    vals['user_category'] = 'association'
                if assoc_group and assoc_group not in user.group_ids:
                    cmds.append(Command.link(assoc_group.id))
                for g in default_feature_groups:
                    if g not in user.group_ids:
                        cmds.append(Command.link(g.id))
                if cmds:
                    vals['group_ids'] = cmds
                if vals:
                    user.sudo().with_context(skip_sync_assoc=True).write(vals)

    def _on_webclient_bootstrap(self):
        super()._on_webclient_bootstrap()
        self._check_and_sync_management_member()

    def _update_last_login(self):
        super()._update_last_login()
        self._check_and_sync_management_member()

    @api.model
    def _init_association_users(self):
        """Ensure all users marked as Association have a linked Association profile and correct groups."""
        assoc_group = self.env.ref('stakeholder_registration.group_association_user', raise_if_not_found=False)
        school_group = self.env.ref('stakeholder_registration.group_school_user', raise_if_not_found=False)
        honna_group = self.env.ref('stakeholder_registration.group_stakeholder_user', raise_if_not_found=False)

        portal_group = self.env.ref('base.group_portal', raise_if_not_found=False)
        group_user = self.env.ref('base.group_user', raise_if_not_found=False)

        users = self.sudo().search([
            '|',
            ('user_category', '=', 'association'),
            ('group_ids', 'in', [assoc_group.id] if assoc_group else [])
        ])
        for user in users:
            is_portal = bool(portal_group and portal_group in user.group_ids)
            vals = {}
            cmds = []
            if is_portal:
                cmds.append(Command.unlink(portal_group.id))
                if group_user and group_user not in user.group_ids:
                    cmds.append(Command.link(group_user.id))
                vals['share'] = False
            if user.user_category != 'association':
                vals['user_category'] = 'association'
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
                if portal_group and portal_group in non_staff.group_ids:
                    continue
                cmds = []
                if honna_group in non_staff.group_ids:
                    cmds.append(Command.unlink(honna_group.id))
                if school_group not in non_staff.group_ids:
                    cmds.append(Command.link(school_group.id))
                if cmds:
                    non_staff.sudo().write({'group_ids': cmds})

        # Ensure Academy and Association users have CRM, eLearning, and Survey access
        crm_salesman_group = self.env.ref('sales_team.group_sale_salesman', raise_if_not_found=False)
        crm_sales_all_group = self.env.ref('sales_team.group_sale_salesman_all_leads', raise_if_not_found=False)
        crm_lead_group = self.env.ref('crm.group_use_lead', raise_if_not_found=False)
        slides_group = self.env.ref('website_slides.group_website_slides_officer', raise_if_not_found=False)
        survey_group = self.env.ref('survey.group_survey_user', raise_if_not_found=False)
        default_feature_groups = [g for g in (crm_salesman_group, crm_sales_all_group, crm_lead_group, slides_group, survey_group) if g]
        crm_root = self.env.ref('crm.crm_menu_root', raise_if_not_found=False)
        survey_root = self.env.ref('survey.menu_surveys', raise_if_not_found=False)
        slides_root = self.env.ref('website_slides.website_slides_menu_root', raise_if_not_found=False)
        feature_menus = [m for m in (crm_root, survey_root, slides_root) if m]

        feature_users = self.sudo().search([
            '|', ('user_category', 'in', ('academy', 'association')),
            ('group_ids', 'in', [assoc_group.id] if assoc_group else [])
        ])
        for f_user in feature_users:
            if portal_group and portal_group in f_user.group_ids:
                continue
            cmds = [Command.link(g.id) for g in default_feature_groups if g not in f_user.group_ids]
            vals = {}
            if cmds:
                vals['group_ids'] = cmds
            if hasattr(f_user, 'hide_menu_ids') and feature_menus:
                unhide = [m for m in feature_menus if m in f_user.hide_menu_ids]
                if unhide:
                    vals['hide_menu_ids'] = [Command.unlink(m.id) for m in unhide]
            if vals:
                f_user.sudo().write(vals)

        internal_assoc_users = users.filtered(lambda u: not (portal_group and portal_group in u.group_ids))
        (internal_assoc_users | school_users)._ensure_main_company_access()
        internal_assoc_users._sync_association_profile()

        # Ensure all existing management members are synced
        members = self.env['stakeholder.association.member'].sudo().search([('association_id', '!=', False)])
        if members:
            members._sync_member_user_access()

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



