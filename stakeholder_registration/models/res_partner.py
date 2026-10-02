# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import AccessError
from .res_users import USER_CATEGORY_SELECTION


class ResPartner(models.Model):
    _inherit = 'res.partner'

    user_category = fields.Selection(
        selection=USER_CATEGORY_SELECTION,
        string='Category',
        index=True,
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
        if is_honna_staff:
            for vals in vals_list:
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
        return super().create(vals_list)

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

