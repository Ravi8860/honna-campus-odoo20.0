# -*- coding: utf-8 -*-
from odoo import api, fields, models, Command, _
from odoo.fields import Domain
from .res_users import USER_CATEGORY_SELECTION


class ResPartner(models.Model):
    _inherit = 'res.partner'

    user_category = fields.Selection(
        selection=USER_CATEGORY_SELECTION,
        string='Category',
        index=True,
    )
    designation = fields.Char(string='Designation')
    association_member_ids = fields.One2many(
        'stakeholder.association.member',
        'name',
        string='Association Memberships',
    )
    association_id = fields.Many2one(
        'stakeholder.association',
        string='Association',
        compute='_compute_association_id',
        inverse='_inverse_association_id',
        store=False,
    )

    def _compute_association_id(self):
        for partner in self:
            assoc = False
            if partner.id and not isinstance(partner.id, models.NewId):
                assoc = self.env['stakeholder.association'].sudo().search([('partner_id', '=', partner.id)], limit=1)
                if not assoc and partner.association_member_ids:
                    assoc = partner.association_member_ids[0].association_id
            partner.association_id = assoc

    def _inverse_association_id(self):
        for partner in self:
            if partner.id and not isinstance(partner.id, models.NewId):
                if partner.association_id and partner.association_id.partner_id != partner:
                    partner.association_id.sudo().write({'partner_id': partner.id})

    def _is_association_or_school_user(self):
        user = self.env.user
        if (
            user.has_group('stakeholder_registration.group_stakeholder_user')
            or user.has_group('base.group_system')
        ):
            return False
        return (
            user.has_group('stakeholder_registration.group_association_user')
            or user.has_group('stakeholder_registration.group_school_user')
        )

    @api.model
    def _access_domain(self, operation):
        """Scope Association/School Contacts without leaking all internal partners.

        List shows: login partner, management members, schools, and own created/assigned.
        Chatter authors: archived system partners + Administrator (hidden from list via _search).
        """
        if self.env.su or not self._is_association_or_school_user():
            return super()._access_domain(operation)

        user = self.env.user
        company = (
            Domain('company_id', '=', False)
            | Domain('company_id', 'parent_of', self.env.companies.ids)
        )
        parts = [
            Domain('id', '=', user.partner_id.id),
            Domain('create_uid', '=', user.id),
            Domain('user_id', '=', user.id),
            # Archived system partners (Public, OdooBot) — not listed (active_test)
            Domain('active', '=', False),
        ]
        admin = self.env.ref('base.partner_admin', raise_if_not_found=False)
        if admin:
            parts.append(Domain('id', '=', admin.id))

        if user.has_group('stakeholder_registration.group_association_user'):
            assoc = user.association_id
            if assoc:
                if assoc.partner_id:
                    parts.append(Domain('id', '=', assoc.partner_id.id))
                member_ids = assoc.member_ids.name.ids
                school_ids = assoc.school_ids.partner_id.ids
                if member_ids:
                    parts.append(Domain('id', 'in', member_ids))
                if school_ids:
                    parts.append(Domain('id', 'in', school_ids))
        else:
            org = user.organisation_id
            if org and org.partner_id:
                parts.append(Domain('id', '=', org.partner_id.id))

        return Domain.OR(parts) & company

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None, *, active_test=True, bypass_access=False):
        # Keep Administrator readable for chatter, but out of Contacts list.
        if not self.env.su and not bypass_access and self._is_association_or_school_user():
            admin = self.env.ref('base.partner_admin', raise_if_not_found=False)
            if admin:
                domain = Domain(domain) & Domain('id', '!=', admin.id)
        return super()._search(
            domain, offset=offset, limit=limit, order=order,
            active_test=active_test, bypass_access=bypass_access,
        )

    @api.onchange('parent_id')
    def _onchange_parent_id_user_category(self):
        if self.parent_id and self.parent_id.user_category and not self.user_category:
            self.user_category = self.parent_id.user_category

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        user = self.env.user
        is_admin = user.has_group('base.group_system') or self.env.is_superuser()

        is_honna_staff = not is_admin and (
            getattr(user, 'is_honna_staff', False) or
            user.user_category == 'honna_staff' or
            user.has_group('stakeholder_registration.group_stakeholder_user')
        )
        if is_honna_staff:
            if 'user_id' in fields_list and not defaults.get('user_id'):
                defaults['user_id'] = user.id
            if 'user_category' in fields_list and not defaults.get('user_category'):
                defaults['user_category'] = 'honna_staff'

        is_restricted = not is_admin and (getattr(user, 'is_school', False) or getattr(user, 'is_association', False)) and not (
            user.has_group('stakeholder_registration.group_stakeholder_user')
        )
        if is_restricted:
            if 'user_id' in fields_list and not defaults.get('user_id'):
                defaults['user_id'] = user.id
            if 'company_id' in fields_list:
                defaults['company_id'] = False
        return defaults

    @api.model_create_multi
    def create(self, vals_list):
        user = self.env.user
        is_admin = user.has_group('base.group_system') or self.env.is_superuser()

        is_honna_staff = not is_admin and (
            getattr(user, 'is_honna_staff', False) or
            user.user_category == 'honna_staff' or
            user.has_group('stakeholder_registration.group_stakeholder_user')
        )
        for vals in vals_list:
            if is_honna_staff:
                if not vals.get('user_id'):
                    vals['user_id'] = user.id
                if not vals.get('user_category'):
                    vals['user_category'] = 'honna_staff'

        is_restricted = not is_admin and (getattr(user, 'is_school', False) or getattr(user, 'is_association', False)) and not (
            user.has_group('stakeholder_registration.group_stakeholder_user')
        )
        if is_restricted:
            for vals in vals_list:
                if not vals.get('user_id'):
                    vals['user_id'] = user.id
                vals['company_id'] = False
        partners = super().create(vals_list)
        if is_restricted or self._is_association_or_school_user():
            partners._create_users_from_contacts()
        return partners

    def _create_users_from_contacts(self):
        """Create a login user from contact name + email (Association/School create).

        Link the user to the creator's association/school so Contacts scope works
        after login (own contact + that association's members/schools).
        """
        User = self.env['res.users'].sudo()
        group_user = self.env.ref('base.group_user', raise_if_not_found=False)
        group_assoc = self.env.ref('stakeholder_registration.group_association_user', raise_if_not_found=False)
        group_school = self.env.ref('stakeholder_registration.group_school_user', raise_if_not_found=False)
        if not group_user:
            return
        creator = self.env.user
        is_school_creator = bool(
            group_school and creator.has_group('stakeholder_registration.group_school_user')
        )
        for partner in self:
            email = (partner.email or '').strip()
            if not email or partner.user_ids:
                continue
            if User.search([
                '|',
                ('login', '=', email),
                ('partner_id', '=', partner.id),
            ], limit=1):
                continue

            if is_school_creator:
                group_ids = [group_user.id, group_school.id]
                category = 'school'
            else:
                group_ids = [group_user.id] + ([group_assoc.id] if group_assoc else [])
                category = 'association'

            user = User.with_context(no_reset_password=True, skip_sync_assoc=True).create({
                'name': partner.name,
                'login': email,
                'email': email,
                'partner_id': partner.id,
                'user_category': category,
                'group_ids': [Command.set(group_ids)],
            })
            # Set after create so stored compute does not wipe the creator's link
            link_vals = {}
            if is_school_creator and creator.organisation_id:
                link_vals['organisation_id'] = creator.organisation_id.id
            elif creator.association_id:
                link_vals['association_id'] = creator.association_id.id
            if link_vals:
                user.with_context(skip_sync_assoc=True).write(link_vals)

            # Keep contact in Association Management Members (creator + new user scope)
            if not is_school_creator and creator.association_id:
                Member = self.env['stakeholder.association.member'].sudo()
                exists = Member.search([
                    ('association_id', '=', creator.association_id.id),
                    ('name', '=', partner.id),
                ], limit=1)
                if not exists:
                    Member.create({
                        'association_id': creator.association_id.id,
                        'name': partner.id,
                        'email': email,
                        'phone': partner.phone or False,
                        'designation': partner.designation or partner.function or False,
                    })
                    self.env['ir.access']._clear_caches()
                    self.env.transaction.invalidate_ormcache()
            try:
                user.action_reset_password()
            except Exception:
                pass

    @api.model
    def _init_partner_user_category(self):
        """Initialize user_category for existing contacts on module upgrade."""
        # 1. Honna Staff users and organisations
        honna_group = self.env.ref('stakeholder_registration.group_stakeholder_user', raise_if_not_found=False)
        honna_users = self.env['res.users'].sudo().search([
            '|', ('user_category', '=', 'honna_staff'),
            ('group_ids', 'in', [honna_group.id] if honna_group else [])
        ])
        for u in honna_users:
            if u.partner_id and u.partner_id.user_category != 'honna_staff':
                u.partner_id.sudo().write({'user_category': 'honna_staff'})

        honna_orgs = self.env['stakeholder.organisation'].sudo().search([('category', '=', 'honna_staff')])
        for org in honna_orgs:
            if org.partner_id and org.partner_id.user_category != 'honna_staff':
                org.partner_id.sudo().write({'user_category': 'honna_staff'})

        # 2. Associations
        associations = self.env['stakeholder.association'].sudo().search([])
        for assoc in associations:
            if assoc.partner_id and assoc.partner_id.user_category != 'association':
                assoc.partner_id.sudo().write({'user_category': 'association'})

        # 3. Organisations of other categories (school, college, academy, etc.)
        other_orgs = self.env['stakeholder.organisation'].sudo().search([('category', '!=', 'honna_staff')])
        for org in other_orgs:
            if org.partner_id and org.category and org.partner_id.user_category != org.category:
                org.partner_id.sudo().write({'user_category': org.category})

        # 4. Students
        students = self.env['stakeholder.student'].sudo().search([])
        for st in students:
            if st.partner_id and st.partner_id.user_category != 'student':
                st.partner_id.sudo().write({'user_category': 'student'})

        # 5. Parents
        parents = self.env['stakeholder.parent'].sudo().search([])
        for p in parents:
            if p.partner_id and p.partner_id.user_category != 'parent':
                p.partner_id.sudo().write({'user_category': 'parent'})

        # 6. Any other users with user_category
        all_users = self.env['res.users'].sudo().search([('user_category', '!=', False)])
        for u in all_users:
            if u.partner_id and u.partner_id.user_category != u.user_category:
                u.partner_id.sudo().write({'user_category': u.user_category})

        # 7. Child contacts inherit user_category from parent_id if unset
        children = self.sudo().search([('parent_id.user_category', '!=', False), ('user_category', '=', False)])
        for child in children:
            child.write({'user_category': child.parent_id.user_category})

        # 8. Association/School created contacts: clear company to avoid multi-company AccessError
        assoc_group = self.env.ref('stakeholder_registration.group_association_user', raise_if_not_found=False)
        school_group = self.env.ref('stakeholder_registration.group_school_user', raise_if_not_found=False)
        group_ids = [g.id for g in (assoc_group, school_group) if g]
        if group_ids:
            restricted_users = self.env['res.users'].sudo().search([('group_ids', 'in', group_ids)])
            if restricted_users:
                stuck = self.sudo().search([
                    ('create_uid', 'in', restricted_users.ids),
                    ('company_id', '!=', False),
                    ('user_ids', '=', False),
                ])
                if stuck:
                    stuck.write({'company_id': False})
