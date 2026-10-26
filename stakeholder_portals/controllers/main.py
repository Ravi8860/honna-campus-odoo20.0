# -*- coding: utf-8 -*-
import base64
import json
import logging
import re
from urllib.parse import urlencode

from odoo import http, fields, _
from odoo.http import request
from odoo.addons.web.controllers.home import Home
from odoo.addons.web.controllers.utils import ensure_db, is_user_internal
from odoo.http.session import check, touch
from odoo.tools import hmac
from odoo.exceptions import AccessError

_logger = logging.getLogger(__name__)

ROLE_TITLES = {
    'association': 'Organisation',
    'school': 'School',
    'parent': 'Parent',
    'academy': 'Academy',
    'student': 'Student',
    'partner': 'Vendor',
    'ecosystem_partner': 'Vendor',
    'honna_staff': 'Honna Staff',
    'college': 'College',
    'others': 'Others',
    'organisation': 'School',
    'school_college': 'School',
    'educator': 'Teacher',
}



class StakeholderPortalController(http.Controller):

    @http.route(['/stakeholder-portals', '/registration'], type='http', auth='public', website=True)
    def portals_index(self, **kw):
        """ Renders the stakeholder account creation page matching Figma """
        return request.render('stakeholder_portals.registration_page', {
            'errors': {},
            'values': kw,
            'success_message': kw.get('success_message'),
            'submitted': kw.get('submitted') == '1',
        })

    @http.route(['/stakeholder-portals/submit', '/registration/submit'], type='http', auth='public', website=True, methods=['POST'], csrf=True)
    def portals_submit(self, **post):
        """ Handles the unified form submission for all stakeholder categories """
        portal_type = (post.get('portal_type') or 'honna_staff').strip()
        salutation = (post.get('salutation') or '').strip()
        first_name = (post.get('first_name') or post.get('name') or '').strip()
        last_name = (post.get('last_name') or '').strip()
        email = (post.get('email') or '').strip()
        raw_phone = (post.get('phone') or '').strip()
        country_code = (post.get('country_code') or '+91').strip()
        terms_agree = post.get('terms_agree')

        errors = {}
        values = post

        # 1. Validation
        if not portal_type:
            errors['portal_type'] = _('Please select your role.')
        if not salutation:
            errors['salutation'] = _('Salutation is required.')
        if not first_name:
            errors['first_name'] = _('Full Name is required.')
        if not email:
            errors['email'] = _('Email Address is required.')
        elif not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            errors['email'] = _('Please enter a valid email address.')
        if not raw_phone:
            errors['phone'] = _('Phone Number is required.')
        if not terms_agree:
            errors['terms_agree'] = _('You must agree to the Terms & Conditions and Privacy Policy.')

        # Check existing user
        if email and not errors.get('email'):
            existing_user = request.env['res.users'].sudo().search(['|', ('login', '=', email), ('email', '=', email)], limit=1)
            if existing_user:
                errors['email'] = _('An account with this email address already exists. Please sign in.')

        if errors:
            if request.httprequest.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in request.httprequest.headers.get('Accept', ''):
                return request.make_json_response({
                    'status': 'error',
                    'errors': errors
                })
            return self._render_form_with_errors(errors, values)

        # Phone formatting
        phone = raw_phone if raw_phone.startswith('+') else f"{country_code} {raw_phone}".strip()

        # Full display name
        full_name = f"{first_name} {last_name}".strip() if last_name else first_name
        display_name = f"{salutation} {full_name}".strip() if salutation else full_name

        role_title = ROLE_TITLES.get(portal_type, portal_type.replace('_', ' ').title())
        sudo_env = request.env(su=True)

        try:
            # 1. Partner setup
            category_mapping = {
                'organisation': 'school',
                'school_college': 'school',
                'ecosystem_partner': 'partner',
            }
            user_cat = category_mapping.get(portal_type, portal_type)

            partner_obj = sudo_env['res.partner'].sudo()
            partner = partner_obj.search([('email', '=', email)], limit=1)
            if not partner and phone:
                partner = partner_obj.search([('phone', '=', phone)], limit=1)

            if not partner:
                partner = partner_obj.create({
                    'name': full_name or display_name,
                    'email': email,
                    'phone': phone,
                })
            else:
                partner_vals = {}
                if not partner.phone and phone:
                    partner_vals['phone'] = phone
                if partner_vals:
                    partner.write(partner_vals)

            # Check legacy student/parent form submissions
            if portal_type == 'student' and post.get('stud_roll'):
                return self._handle_student_submit(post, sudo_env)
            if portal_type == 'parent' and post.get('par_students'):
                return self._handle_parent_submit(post, sudo_env)

            # 2. Determine groups for res.users
            group_user = sudo_env.ref('base.group_user', raise_if_not_found=False)
            group_ids = [g.id for g in [group_user] if g]

            if portal_type == 'honna_staff':
                honna_group = sudo_env.ref('stakeholder_registration.group_stakeholder_user', raise_if_not_found=False)
                if honna_group:
                    group_ids.append(honna_group.id)
            elif portal_type == 'association':
                assoc_group = sudo_env.ref('stakeholder_registration.group_association_user', raise_if_not_found=False)
                if assoc_group:
                    group_ids.append(assoc_group.id)
            elif portal_type in ('school', 'college', 'academy', 'organisation', 'school_college', 'partner', 'vendor', 'parent', 'student'):
                school_group = sudo_env.ref('stakeholder_registration.group_school_user', raise_if_not_found=False)
                if school_group:
                    group_ids.append(school_group.id)
            if portal_type in ('association', 'academy'):
                crm_salesman_group = sudo_env.ref('sales_team.group_sale_salesman', raise_if_not_found=False)
                crm_sales_all_group = sudo_env.ref('sales_team.group_sale_salesman_all_leads', raise_if_not_found=False)
                crm_lead_group = sudo_env.ref('crm.group_use_lead', raise_if_not_found=False)
                slides_group = sudo_env.ref('website_slides.group_website_slides_officer', raise_if_not_found=False)
                survey_group = sudo_env.ref('survey.group_survey_user', raise_if_not_found=False)
                for g in (crm_salesman_group, crm_sales_all_group, crm_lead_group, slides_group, survey_group):
                    if g:
                        group_ids.append(g.id)

            # 3. Find or Create stakeholder record FIRST (prevent duplicate records)
            rec_id = False
            rec = None
            if portal_type == 'association':
                assoc_obj = sudo_env['stakeholder.association'].sudo()
                rec = partner and assoc_obj.search([('partner_id', '=', partner.id)], limit=1)
                if not rec and email:
                    rec = assoc_obj.search([('email', '=', email)], limit=1)

                assoc_vals = {
                    'name': display_name,
                    'contact_name': display_name,
                    'primary_contact_first_name': first_name,
                    'primary_contact_last_name': last_name,
                    'email': email,
                    'phone': phone,
                    'state': 'draft',
                    'partner_id': partner.id,
                }
                if rec:
                    rec.write(assoc_vals)
                else:
                    rec = assoc_obj.create(assoc_vals)
                rec_id = rec.id
            elif portal_type == 'student':
                stud_obj = sudo_env['stakeholder.student'].sudo()
                rec = stud_obj.search([('email', '=', email)], limit=1) if email else None
                if not rec and phone:
                    rec = stud_obj.search([('phone', '=', phone)], limit=1)
                stud_vals = {
                    'name': display_name or full_name,
                    'email': email,
                    'phone': phone,
                }
                if rec:
                    rec.write(stud_vals)
                else:
                    stud_vals['roll'] = f"ADM-{sudo_env['ir.sequence'].sudo().next_by_code('stakeholder.student') or '001'}"
                    rec = stud_obj.create(stud_vals)
                rec_id = rec.id
            elif portal_type == 'parent':
                par_obj = sudo_env['stakeholder.parent'].sudo()
                rec = par_obj.search([('email', '=', email)], limit=1) if email else None
                if not rec and phone:
                    rec = par_obj.search([('phone', '=', phone)], limit=1)
                par_vals = {
                    'name': display_name or full_name,
                    'email': email,
                    'phone': phone,
                }
                if rec:
                    rec.write(par_vals)
                else:
                    rec = par_obj.create(par_vals)
                rec_id = rec.id
            else:
                cat_val = 'school' if portal_type in ('school', 'school_college', 'organisation') else portal_type
                org_obj = sudo_env['stakeholder.organisation'].sudo()
                rec = partner and org_obj.search([('partner_id', '=', partner.id), ('category', '=', cat_val)], limit=1)
                if not rec and email:
                    rec = org_obj.search([('email', '=', email), ('category', '=', cat_val)], limit=1)

                org_vals = {
                    'name': display_name,
                    'contact_name': display_name,
                    'primary_contact_first_name': first_name,
                    'primary_contact_last_name': last_name,
                    'email': email,
                    'phone': phone,
                    'category': cat_val,
                    'state': 'approved' if portal_type == 'honna_staff' else 'draft',
                    'partner_id': partner.id,
                }
                if rec:
                    rec.write(org_vals)
                else:
                    rec = org_obj.create(org_vals)
                rec_id = rec.id

            # 4. Find or Create res.users with skip_sync_assoc=True (prevent duplicate users & duplicate profiles)
            user_obj = sudo_env['res.users'].sudo()
            user = user_obj.search([('login', '=', email)], limit=1)
            if not user and partner:
                user = user_obj.search([('partner_id', '=', partner.id)], limit=1)

            if not user:
                user_vals = {
                    'name': display_name or full_name,
                    'login': email,
                    'email': email,
                    'phone': phone,
                    'partner_id': partner.id,
                    'group_ids': [(6, 0, list(set(group_ids)))],
                    'share': False,
                    'user_category': user_cat,
                }
                if portal_type == 'association' and rec:
                    user_vals['association_id'] = rec.id
                user = user_obj.with_context(skip_sync_assoc=True).create(user_vals)
            else:
                user_write_vals = {'user_category': user_cat}
                current_gids = user.group_ids.ids
                new_gids = [gid for gid in group_ids if gid not in current_gids]
                if new_gids:
                    user_write_vals['group_ids'] = [(4, gid) for gid in new_gids]
                if not user.phone and phone:
                    user_write_vals['phone'] = phone
                if portal_type == 'association' and rec and user.association_id != rec:
                    user_write_vals['association_id'] = rec.id
                user.with_context(skip_sync_assoc=True).write(user_write_vals)

            if rec and hasattr(rec, 'user_id') and not rec.user_id:
                rec.sudo().write({'user_id': user.id})

            # 5. Create CRM Lead based on selected category
            lead_vals = {
                'name': _('%s Registration: %s') % (role_title, display_name),
                'partner_name': display_name,
                'contact_name': display_name,
                'partner_id': partner.id if partner else False,
                'email_from': email,
                'phone': phone,
                'portal_type': portal_type,
                'user_category': user_cat,
                'salutation': salutation,
                'first_name': first_name,
                'last_name': last_name,
                'registration_id_ref': str(rec_id) if rec_id else '',
                'org_registration_id': rec_id if portal_type not in ('association', 'student', 'parent') else False,
                'assoc_registration_id': rec_id if portal_type == 'association' else False,
                'type': 'lead',
                'user_id': user.id if user else False,
                'company_id': request.env.company.id if hasattr(request, 'env') and request.env.company else False,
            }
            lead = sudo_env['crm.lead'].create(lead_vals)
            if lead and rec and hasattr(rec, 'lead_id'):
                rec.sudo().write({'lead_id': lead.id})

            # 6. Response for popup notification and redirect to login page
            if request.httprequest.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in request.httprequest.headers.get('Accept', ''):
                return request.make_json_response({
                    'status': 'success',
                    'message': _("Registration submitted successfully!"),
                    'redirect_url': '/web/login?registered=1',
                })

            return request.redirect('/web/login?registered=1')

        except Exception as e:
            _logger.exception("Error processing stakeholder registration submission")
            if request.httprequest.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in request.httprequest.headers.get('Accept', ''):
                return request.make_json_response({
                    'status': 'error',
                    'errors': {'global': str(e)}
                })
            errors['global'] = str(e)
            return self._render_form_with_errors(errors, values)

    def _render_form_with_errors(self, errors, values):
        return request.render('stakeholder_portals.registration_page', {
            'errors': errors,
            'values': values
        })

    def _handle_student_submit(self, post, env):
        name = post.get('stud_name') or post.get('first_name')
        email = post.get('stud_email') or post.get('email')
        phone = post.get('stud_phone') or post.get('phone')
        roll = post.get('stud_roll') or f"ADM-{env['ir.sequence'].sudo().next_by_code('stakeholder.student') or '001'}"

        student_rec = env['stakeholder.student'].sudo().create({
            'name': name,
            'email': email,
            'phone': phone,
            'roll': roll,
        })
        lead = env['crm.lead'].sudo().create({
            'name': _('Student Registration: %s') % name,
            'contact_name': name,
            'email_from': email,
            'phone': phone,
            'portal_type': 'student',
            'user_category': 'student',
            'first_name': post.get('first_name') or name,
            'last_name': post.get('last_name') or '',
            'registration_id_ref': str(student_rec.id),
            'type': 'lead',
        })
        if lead:
            student_rec.sudo().write({'lead_id': lead.id})
        return request.redirect('/web/login')

    def _handle_parent_submit(self, post, env):
        name = post.get('par_name') or post.get('first_name')
        email = post.get('par_email') or post.get('email')
        phone = post.get('par_phone') or post.get('phone')

        parent_rec = env['stakeholder.parent'].sudo().create({
            'name': name,
            'email': email,
            'phone': phone,
        })
        lead = env['crm.lead'].sudo().create({
            'name': _('Parent Registration: %s') % name,
            'contact_name': name,
            'email_from': email,
            'phone': phone,
            'portal_type': 'parent',
            'user_category': 'parent',
            'first_name': post.get('first_name') or name,
            'last_name': post.get('last_name') or '',
            'registration_id_ref': str(parent_rec.id),
            'type': 'lead',
        })
        if lead:
            parent_rec.sudo().write({'lead_id': lead.id})
        return request.redirect('/web/login')


    @http.route(['/association/profile', '/my/association', '/stakeholder-portals/profile'], type='http', auth='public', website=True)
    def association_profile(self, **kw):
        """ Renders the Association / Organisation Profile page matching Figma Screenshots 2 & 3 """
        sudo_env = request.env(su=True)
        assoc = None
        user = request.env.user
        is_internal_or_staff = user and (user.has_group('base.group_system') or user.has_group('stakeholder_registration.group_stakeholder_user'))

        if not is_internal_or_staff and user and user.id != request.env.ref('base.public_user').id:
            if hasattr(user, 'association_id') and user.association_id:
                assoc = user.association_id.sudo()
            elif user.partner_id:
                assoc = sudo_env['stakeholder.association'].search([('partner_id', '=', user.partner_id.id)], limit=1)
                if not assoc:
                    mem = sudo_env['stakeholder.association.member'].search([
                        ('name', '=', user.partner_id.id),
                        ('association_id', '!=', False)
                    ], limit=1)
                    if mem:
                        assoc = mem.association_id
            if not assoc and user.email:
                assoc = sudo_env['stakeholder.association'].search([('email', '=', user.email)], limit=1)
                if not assoc:
                    mem = sudo_env['stakeholder.association.member'].search([
                        ('email', '=', user.email),
                        ('association_id', '!=', False)
                    ], limit=1)
                    if mem:
                        assoc = mem.association_id
            if not assoc and user.login and '@' in user.login:
                mem = sudo_env['stakeholder.association.member'].search([
                    ('email', '=', user.login),
                    ('association_id', '!=', False)
                ], limit=1)
                if mem:
                    assoc = mem.association_id
        else:
            assoc_id = kw.get('id')
            if assoc_id:
                try:
                    assoc = sudo_env['stakeholder.association'].browse(int(assoc_id))
                    if not assoc.exists():
                        assoc = None
                except Exception:
                    assoc = None

            if not assoc and user and user.id != request.env.ref('base.public_user').id:
                if hasattr(user, 'association_id') and user.association_id:
                    assoc = user.association_id.sudo()
                elif user.partner_id:
                    assoc = sudo_env['stakeholder.association'].search([('partner_id', '=', user.partner_id.id)], limit=1)
                if not assoc and user.email:
                    assoc = sudo_env['stakeholder.association'].search([('email', '=', user.email)], limit=1)

        # Fallback for preview / demo
        if not assoc:
            assoc = sudo_env['stakeholder.association'].search([], order='id desc', limit=1)

        assoc_sudo = assoc.sudo() if assoc else None
        members = assoc_sudo.member_ids.sudo() if assoc_sudo else sudo_env['stakeholder.association.member'].browse([])
        countries = sudo_env['res.country'].search([('code', '=', 'IN')]) or sudo_env['res.country'].search([], limit=10)
        states = sudo_env['res.country.state'].search([('country_id.code', '=', 'IN')])

        return request.render('stakeholder_portals.association_profile_page', {
            'page_name': 'profile',
            'active_menu': 'profile',
            'association': assoc_sudo,
            'members': members,
            'countries': countries,
            'states': states,
            'saved': kw.get('saved') == '1',
            'action_type': kw.get('action_type', 'save'),
        })

    @http.route(['/association/profile/save'], type='http', auth='public', website=True, methods=['POST'], csrf=True)
    def association_profile_save(self, **post):
        """ Handles profile update from web portal matching Figma design """
        sudo_env = request.env(su=True)
        assoc_id = post.get('association_id')
        assoc = None
        if assoc_id:
            try:
                assoc = sudo_env['stakeholder.association'].browse(int(assoc_id))
            except Exception:
                pass

        if not assoc or not assoc.exists():
            user = request.env.user
            if user and hasattr(user, 'association_id') and user.association_id:
                assoc = user.association_id
            else:
                assoc = sudo_env['stakeholder.association'].search([], order='id desc', limit=1)

        if not assoc:
            return request.redirect('/association/profile')

        vals = {}
        if post.get('name'):
            vals['name'] = post.get('name').strip()
        if post.get('organisation_type'):
            vals['organisation_type'] = post.get('organisation_type')
        if post.get('street'):
            vals['street'] = post.get('street').strip()
        if post.get('street2'):
            vals['street2'] = post.get('street2').strip()
        if post.get('city'):
            vals['city'] = post.get('city').strip()
        if post.get('country_id'):
            try:
                vals['country_id'] = int(post.get('country_id'))
            except (ValueError, TypeError):
                pass
        if post.get('state_id'):
            try:
                vals['state_id'] = int(post.get('state_id'))
            except (ValueError, TypeError):
                pass
        if post.get('zip'):
            vals['zip'] = post.get('zip').strip()

        if post.get('email'):
            vals['email'] = post.get('email').strip()
        if post.get('phone'):
            vals['phone'] = post.get('phone').strip()
        if post.get('website'):
            vals['website'] = post.get('website').strip()
        if post.get('parent_org'):
            vals['parent_org'] = post.get('parent_org').strip()
        if post.get('parent_head_office'):
            vals['parent_head_office'] = post.get('parent_head_office').strip()
        if post.get('board_affiliation'):
            vals['board_affiliation'] = post.get('board_affiliation')
        if post.get('medium'):
            vals['medium'] = post.get('medium').strip()
        if post.get('year_established'):
            vals['year_established'] = post.get('year_established').strip()
        if post.get('vat'):
            vals['vat'] = post.get('vat').strip()
        if post.get('trust_details'):
            vals['trust_details'] = post.get('trust_details').strip()
        if 'geolocation' in post:
            vals['geolocation'] = (post.get('geolocation') or '').strip()

        # Primary contact
        if post.get('primary_contact_first_name'):
            vals['primary_contact_first_name'] = post.get('primary_contact_first_name').strip()
        if post.get('primary_contact_last_name'):
            vals['primary_contact_last_name'] = post.get('primary_contact_last_name').strip()
        if post.get('contact_role'):
            vals['contact_role'] = post.get('contact_role').strip()
        if post.get('contact_email'):
            vals['contact_email'] = post.get('contact_email').strip()
        if post.get('contact_phone'):
            vals['contact_phone'] = post.get('contact_phone').strip()
        if post.get('contact_method'):
            vals['contact_method'] = post.get('contact_method')

        # Action: Draft vs Save
        action_type = post.get('action') or 'save'
        if action_type == 'draft':
            vals['state'] = 'draft'
        elif action_type == 'save' and assoc.state == 'draft':
            vals['state'] = 'approved'

        # Photo upload
        logo_file = request.httprequest.files.get('logo')
        if logo_file and logo_file.filename:
            try:
                vals['logo'] = base64.b64encode(logo_file.read())
            except Exception:
                pass

        if vals:
            assoc.sudo().write(vals)

        # Handle New Member addition from form
        mem_first = (post.get('new_member_first_name') or '').strip()
        mem_last = (post.get('new_member_last_name') or '').strip()
        mem_role = (post.get('new_member_role') or '').strip()
        mem_email = (post.get('new_member_email') or '').strip()
        mem_phone = (post.get('new_member_phone') or '').strip()
        mem_desig = (post.get('new_member_designation') or mem_role).strip()

        if mem_first or mem_last or mem_email or mem_phone:
            full_name = f"{mem_first} {mem_last}".strip() or mem_email or mem_phone
            partner = sudo_env['res.partner'].create({
                'name': full_name,
                'designation': mem_desig or mem_role or 'Member',
                'email': mem_email,
                'phone': mem_phone,
            })
            sudo_env['stakeholder.association.member'].create({
                'association_id': assoc.id,
                'name': partner.id,
                'designation': mem_desig or mem_role or 'Member',
                'email': mem_email,
                'phone': mem_phone,
            })

        # Member deletion if requested
        delete_member_id = post.get('delete_member_id')
        if delete_member_id:
            try:
                del_mem = sudo_env['stakeholder.association.member'].browse(int(delete_member_id))
                if del_mem.exists() and del_mem.association_id.id == assoc.id:
                    del_mem.unlink()
            except Exception:
                pass

        if request.httprequest.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in request.httprequest.headers.get('Accept', ''):
            return request.make_json_response({
                'status': 'success',
                'message': _("Profile updated successfully!"),
                'action_type': action_type,
            })

        return request.redirect(f'/association/profile?id={assoc.id}&saved=1&action_type={action_type}')

    @http.route(['/schools', '/school', '/school/list', '/my/schools'], type='http', auth='public', website=True)
    def schools_list(self, **kw):
        """ Renders the School List View for Portal Users """
        sudo_env = request.env(su=True)
        user = request.env.user
        is_admin_or_staff = user and (user.has_group('base.group_system') or user.has_group('stakeholder_registration.group_stakeholder_user'))

        domain = [('category', '=', 'school')]
        if not is_admin_or_staff and user and not user._is_public():
            user_domains = []
            if user.partner_id:
                user_domains.append(('partner_id', '=', user.partner_id.id))
            user_domains.append(('user_id', '=', user.id))
            user_domains.append(('create_uid', '=', user.id))
            if hasattr(user, 'association_id') and user.association_id:
                user_domains.append(('parent_organisation_id', '=', user.association_id.id))
                user_domains.append(('association_ids', 'in', [user.association_id.id]))
                if user.association_id.school_ids:
                    user_domains.append(('id', 'in', user.association_id.school_ids.ids))
            if hasattr(user, 'organisation_id') and user.organisation_id:
                user_domains.append(('id', '=', user.organisation_id.id))
                user_domains.append(('parent_school_id', '=', user.organisation_id.id))

            if user_domains:
                domain = domain + (['|'] * (len(user_domains) - 1)) + user_domains

        schools = sudo_env['stakeholder.organisation'].search(domain, order='create_date desc, id desc')
        if not schools and (user._is_public() or is_admin_or_staff):
            schools = sudo_env['stakeholder.organisation'].search([('category', '=', 'school')], order='id desc', limit=10)

        return request.render('stakeholder_portals.school_list_page', {
            'page_name': 'school',
            'active_menu': 'school',
            'schools': schools,
            'saved': kw.get('saved') == '1',
        })

    def _render_school_form(self, school=None, step=1, **kw):
        sudo_env = request.env(su=True)
        user = request.env.user
        countries = sudo_env['res.country'].search([('code', '=', 'IN')]) or sudo_env['res.country'].search([], limit=10)
        states = sudo_env['res.country.state'].search([('country_id.code', '=', 'IN')])
        associations = sudo_env['stakeholder.association'].search([], order='name asc')
        parent_schools = sudo_env['stakeholder.organisation'].search([
            ('category', '=', 'school'),
            ('id', '!=', school.id if school else 0)
        ], order='name asc')

        user_assoc = getattr(user, 'association_id', None) if user and not user._is_public() else None

        try:
            step = int(step)
        except (ValueError, TypeError):
            step = 1

        return request.render('stakeholder_portals.school_profile_page', {
            'page_name': 'school',
            'active_menu': 'school',
            'school': school,
            'user_association': user_assoc,
            'countries': countries,
            'states': states,
            'associations': associations,
            'parent_schools': parent_schools,
            'saved': kw.get('saved') == '1',
            'action_type': kw.get('action_type', 'save'),
            'current_step': step,
        })

    @http.route(['/school/profile', '/my/school', '/stakeholder-portals/school'], type='http', auth='public', website=True)
    def school_profile(self, **kw):
        """ Renders the School Profile multi-step wizard matching Screenshots 1, 2, 3 """
        sudo_env = request.env(su=True)
        school = None
        school_id = kw.get('id')
        is_new = kw.get('new') == '1' or school_id == 'new'

        if is_new:
            return self._render_school_form(school=None, step=kw.get('step', 1), is_new=True, **kw)

        if school_id and str(school_id).isdigit():
            try:
                school = sudo_env['stakeholder.organisation'].browse(int(school_id))
                if not school.exists() or (school.category and school.category != 'school'):
                    school = None
            except Exception:
                school = None

        user = request.env.user
        if not school and user and not user._is_public():
            if hasattr(user, 'organisation_id') and user.organisation_id:
                school = user.organisation_id.sudo()
            elif user.partner_id:
                school = sudo_env['stakeholder.organisation'].search([
                    ('partner_id', '=', user.partner_id.id),
                    ('category', '=', 'school')
                ], limit=1)
            if not school and user.email:
                school = sudo_env['stakeholder.organisation'].search([
                    ('email', '=', user.email),
                    ('category', '=', 'school')
                ], limit=1)

        if not school:
            return request.redirect('/schools')

        return self._render_school_form(school=school, step=kw.get('step', 1), is_new=False, **kw)

    @http.route(['/school/profile/save'], type='http', auth='public', website=True, methods=['POST'], csrf=True)
    def school_profile_save(self, **post):
        """ Handles school profile creation, updates and multi-step submissions """
        sudo_env = request.env(su=True)
        user = request.env.user
        school_id = post.get('school_id')
        school = None
        if school_id and str(school_id).isdigit() and int(school_id) > 0:
            try:
                school = sudo_env['stakeholder.organisation'].browse(int(school_id))
                if not school.exists() or (school.category and school.category != 'school'):
                    school = None
            except Exception:
                school = None

        vals = {}
        if post.get('name'):
            vals['name'] = post.get('name').strip()
        if post.get('website'):
            vals['website'] = post.get('website').strip()
        if post.get('board_affiliation'):
            vals['board_affiliation'] = post.get('board_affiliation')
        if post.get('medium'):
            vals['medium'] = post.get('medium').strip()
        if post.get('year_established'):
            vals['year_established'] = post.get('year_established').strip()
        if post.get('residential'):
            vals['residential'] = post.get('residential')

        # Parent Organisation (Many2one to stakeholder.association)
        if post.get('parent_organisation_id'):
            try:
                vals['parent_organisation_id'] = int(post.get('parent_organisation_id'))
            except (ValueError, TypeError):
                vals['parent_organisation_id'] = False
        elif 'parent_organisation_id' in post:
            vals['parent_organisation_id'] = False

        # Parent School / Head Office (Many2one to stakeholder.organisation)
        if post.get('parent_school_id'):
            try:
                vals['parent_school_id'] = int(post.get('parent_school_id'))
            except (ValueError, TypeError):
                vals['parent_school_id'] = False
        elif 'parent_school_id' in post:
            vals['parent_school_id'] = False

        # Primary Address
        if post.get('street'):
            vals['street'] = post.get('street').strip()
        if post.get('street2'):
            vals['street2'] = post.get('street2').strip()
        if post.get('city'):
            vals['city'] = post.get('city').strip()
        if post.get('country_id'):
            try:
                vals['country_id'] = int(post.get('country_id'))
            except (ValueError, TypeError):
                pass
        if post.get('state_id'):
            try:
                vals['state_id'] = int(post.get('state_id'))
            except (ValueError, TypeError):
                pass
        if post.get('zip'):
            vals['zip'] = post.get('zip').strip()

        # Primary Address geolocation
        if 'geolocation' in post:
            vals['geolocation'] = (post.get('geolocation') or '').strip()

        # School Contacts & Registration Details
        if post.get('phone'):
            vals['phone'] = post.get('phone').strip()
        if post.get('email'):
            vals['email'] = post.get('email').strip()
        if post.get('vat'):
            vals['vat'] = post.get('vat').strip()
        if post.get('trust_details'):
            vals['trust_details'] = post.get('trust_details').strip()

        # Step 3: Primary Contacts
        if post.get('principal_name'):
            vals['principal_name'] = post.get('principal_name').strip()
        if post.get('principal_email'):
            vals['principal_email'] = post.get('principal_email').strip()
        if post.get('principal_phone'):
            vals['principal_phone'] = post.get('principal_phone').strip()
        if post.get('principal_contact_method'):
            vals['principal_contact_method'] = post.get('principal_contact_method')

        if post.get('primary_contact_first_name'):
            vals['primary_contact_first_name'] = post.get('primary_contact_first_name').strip()
        if post.get('primary_contact_last_name'):
            vals['primary_contact_last_name'] = post.get('primary_contact_last_name').strip()
        if post.get('contact_name'):
            vals['contact_name'] = post.get('contact_name').strip()
            parts = vals['contact_name'].split(' ')
            if not vals.get('primary_contact_first_name'):
                vals['primary_contact_first_name'] = parts[0]
            if not vals.get('primary_contact_last_name') and len(parts) > 1:
                vals['primary_contact_last_name'] = ' '.join(parts[1:])
        if post.get('contact_role'):
            vals['contact_role'] = post.get('contact_role').strip()
        if post.get('contact_email'):
            vals['contact_email'] = post.get('contact_email').strip()
        if post.get('contact_phone'):
            vals['contact_phone'] = post.get('contact_phone').strip()
        if post.get('contact_method'):
            vals['contact_method'] = post.get('contact_method')

        # Step 4: Other Details
        if post.get('affiliation_number'):
            vals['affiliation_number'] = post.get('affiliation_number').strip()
        if post.get('accreditation'):
            vals['accreditation'] = post.get('accreditation').strip()
        if post.get('capacity'):
            try:
                vals['capacity'] = int(post.get('capacity'))
            except (ValueError, TypeError):
                pass
        if post.get('branch_code'):
            vals['branch_code'] = post.get('branch_code').strip()
        if post.get('area'):
            vals['area'] = post.get('area').strip()

        # Billing Address
        vals['billing_same_as_primary'] = bool(post.get('billing_same_as_primary'))
        if post.get('billing_street'):
            vals['billing_street'] = post.get('billing_street').strip()
        if post.get('billing_street2'):
            vals['billing_street2'] = post.get('billing_street2').strip()
        if post.get('billing_city'):
            vals['billing_city'] = post.get('billing_city').strip()
        if post.get('billing_district'):
            vals['billing_district'] = post.get('billing_district').strip()
        if post.get('billing_zip'):
            vals['billing_zip'] = post.get('billing_zip').strip()
        if post.get('billing_country_id'):
            try:
                vals['billing_country_id'] = int(post.get('billing_country_id'))
            except (ValueError, TypeError):
                pass
        if post.get('billing_state_id'):
            try:
                vals['billing_state_id'] = int(post.get('billing_state_id'))
            except (ValueError, TypeError):
                pass

        # Shipping Address
        vals['shipping_same_as_primary'] = bool(post.get('shipping_same_as_primary'))
        if post.get('shipping_street'):
            vals['shipping_street'] = post.get('shipping_street').strip()
        if post.get('shipping_street2'):
            vals['shipping_street2'] = post.get('shipping_street2').strip()
        if post.get('shipping_city'):
            vals['shipping_city'] = post.get('shipping_city').strip()
        if post.get('shipping_district'):
            vals['shipping_district'] = post.get('shipping_district').strip()
        if post.get('shipping_zip'):
            vals['shipping_zip'] = post.get('shipping_zip').strip()
        if post.get('shipping_country_id'):
            try:
                vals['shipping_country_id'] = int(post.get('shipping_country_id'))
            except (ValueError, TypeError):
                pass
        if post.get('shipping_state_id'):
            try:
                vals['shipping_state_id'] = int(post.get('shipping_state_id'))
            except (ValueError, TypeError):
                pass

        # Action: Draft vs Save
        action_type = post.get('action') or 'save'
        if action_type == 'draft':
            vals['state'] = 'draft'
        elif action_type == 'save':
            vals['state'] = 'approved'

        # File uploads
        logo_file = request.httprequest.files.get('logo')
        if logo_file and logo_file.filename:
            try:
                vals['logo'] = base64.b64encode(logo_file.read())
            except Exception:
                pass

        p_img = request.httprequest.files.get('principal_image')
        if p_img and p_img.filename:
            try:
                vals['principal_image'] = base64.b64encode(p_img.read())
            except Exception:
                pass

        c_img = request.httprequest.files.get('primary_contact_image')
        if c_img and c_img.filename:
            try:
                vals['primary_contact_image'] = base64.b64encode(c_img.read())
            except Exception:
                pass

        # CREATE OR UPDATE RECORD IN BACKEND
        if not school:
            vals['category'] = 'school'
            if not vals.get('name'):
                vals['name'] = post.get('name') or _('New School')
            if user and not user._is_public():
                if user.partner_id:
                    vals['partner_id'] = user.partner_id.id
                vals['user_id'] = user.id
                if hasattr(user, 'association_id') and user.association_id:
                    if not vals.get('parent_organisation_id'):
                        vals['parent_organisation_id'] = user.association_id.id
                    vals['association_ids'] = [(4, user.association_id.id)]
            school = sudo_env['stakeholder.organisation'].create(vals)
            if user and not user._is_public() and hasattr(user, 'association_id') and user.association_id:
                user.association_id.sudo().write({'school_ids': [(4, school.id)]})
        else:
            if vals:
                school.sudo().write(vals)

        # Handle Member Add or Edit
        mem_cat = (post.get('member_category') or 'executive').strip().lower()
        mem_model_name = 'stakeholder.organisation.board.member'
        if mem_cat == 'academic':
            mem_model_name = 'stakeholder.organisation.dept.head'
        elif mem_cat == 'operations':
            mem_model_name = 'stakeholder.organisation.operation.member'

        # Handle Association Partner addition
        new_assoc_id = post.get('new_assoc_id')
        if new_assoc_id and str(new_assoc_id).isdigit():
            sudo_env['stakeholder.organisation.association.membership'].create({
                'organisation_id': school.id,
                'association_id': int(new_assoc_id),
                'membership_number': (post.get('new_assoc_membership_number') or '').strip(),
                'expiry_date': post.get('new_assoc_expiry_date') or False,
            })

        edit_member_id = post.get('edit_member_id')
        mem_first = (post.get('new_member_first_name') or '').strip()
        mem_last = (post.get('new_member_last_name') or '').strip()
        mem_role = (post.get('new_member_role') or '').strip()
        mem_email = (post.get('new_member_email') or '').strip()
        mem_phone = (post.get('new_member_phone') or '').strip()
        mem_primary = bool(post.get('new_member_is_primary'))

        mem_img = request.httprequest.files.get('new_member_image')
        mem_img_bytes = False
        if mem_img and mem_img.filename:
            try:
                mem_img_bytes = base64.b64encode(mem_img.read())
            except Exception:
                pass

        if mem_first or mem_last or mem_email or mem_role:
            mem_vals = {
                'organisation_id': school.id,
                'first_name': mem_first,
                'last_name': mem_last,
                'name': f"{mem_first} {mem_last}".strip() or mem_email,
                'designation': mem_role or '',
                'email': mem_email,
                'phone': mem_phone,
                'is_primary': mem_primary,
            }

            # Safely validate role against the model's Selection field
            role_key = False
            if mem_role and mem_model_name in sudo_env:
                clean_r = mem_role.strip().lower().replace(' ', '_').replace('-', '_')
                field_role = sudo_env[mem_model_name]._fields.get('role')
                if field_role and hasattr(field_role, 'selection'):
                    sel = field_role.selection or []
                    for k, label in sel:
                        if clean_r == k or clean_r == label.lower():
                            role_key = k
                            break
                        elif clean_r in k or k in clean_r or clean_r in label.lower():
                            role_key = k
            mem_vals['role'] = role_key

            if mem_img_bytes:
                mem_vals['image'] = mem_img_bytes

            if edit_member_id:
                try:
                    target_rec = sudo_env[mem_model_name].browse(int(edit_member_id))
                    if target_rec.exists() and target_rec.organisation_id.id == school.id:
                        target_rec.write(mem_vals)
                except Exception:
                    pass
            else:
                sudo_env[mem_model_name].create(mem_vals)

        # Member deletion
        delete_member_id = post.get('delete_member_id')
        delete_member_type = post.get('delete_member_type') or 'executive'
        if delete_member_id:
            del_model = 'stakeholder.organisation.board.member'
            if delete_member_type == 'academic':
                del_model = 'stakeholder.organisation.dept.head'
            elif delete_member_type == 'operations':
                del_model = 'stakeholder.organisation.operation.member'
            elif delete_member_type == 'association_partners':
                del_model = 'stakeholder.organisation.association.membership'
            try:
                del_rec = sudo_env[del_model].browse(int(delete_member_id))
                if del_rec.exists() and del_rec.organisation_id.id == school.id:
                    del_rec.unlink()
            except Exception:
                pass

        step = str(post.get('current_step') or '1')

        if request.httprequest.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in request.httprequest.headers.get('Accept', ''):
            return request.make_json_response({
                'status': 'success',
                'message': _("School record saved successfully!"),
                'school_id': school.id,
                'action_type': action_type,
                'step': step,
            })

        if post.get('delete_member_id') or (step == '2' and (post.get('new_member_first_name') or post.get('new_member_email')) and not post.get('finalize')):
            return request.redirect(f'/school/profile?id={school.id}&saved=1&step=2&action_type={action_type}')

        return request.redirect('/schools?saved=1')

    @http.route(['/stakeholder-portals/success', '/registration/success'], type='http', auth='public', website=True)
    def portals_success(self, **kw):
        """ Direct redirect to login page """
        return request.redirect('/web/login')

    @http.route(['/portal/profile', '/my/profile'], type='http', auth='user', website=True)
    def portal_profile_route(self, **kw):
        """ Redirect to the appropriate profile based on user role """
        user = request.env.user
        if user.has_group('stakeholder_registration.group_school_user') or getattr(user, 'user_category', '') in ('school', 'school_college', 'college', 'academy') or getattr(user, 'organisation_id', None):
            return request.redirect('/school/profile')
        elif getattr(user, 'association_id', None) or user.has_group('stakeholder_registration.group_association_user'):
            return request.redirect('/association/profile')

        assoc = request.env['stakeholder.association'].sudo().search([
            '|', ('partner_id', '=', user.partner_id.id), ('email', '=', user.email)
        ], limit=1)
        if not assoc:
            mem = request.env['stakeholder.association.member'].sudo().search([
                ('association_id', '!=', False),
                '|', ('name', '=', user.partner_id.id), ('email', '=', user.email)
            ], limit=1)
            if mem:
                assoc = mem.association_id
        if assoc:
            return request.redirect(f'/association/profile?id={assoc.id}')

        school = request.env['stakeholder.organisation'].sudo().search([
            '|', ('partner_id', '=', user.partner_id.id), ('email', '=', user.email)
        ], limit=1)
        if school:
            return request.redirect(f'/school/profile?id={school.id}')

        return request.redirect('/association/profile')

    @http.route(['/portal/contacts', '/my/contacts'], type='http', auth='user', website=True)
    def portal_contacts_route(self, **kw):
        """ Navigates to the portal contact dashboard """
        return request.redirect('/my')

    @http.route(['/portal/calendar', '/my/calendar'], type='http', auth='user', website=True)
    def portal_calendar_route(self, **kw):
        """ Redirects directly to the Odoo backend calendar view """
        return request.redirect('/odoo/calendar')


class StakeholderWebHome(Home):

    @http.route(['/web', '/odoo', '/odoo/<path:subpath>', '/scoped_app/<path:subpath>'], type='http', auth="none", readonly=Home._web_client_readonly)
    def web_client(self, s_action=None, **kw):
        """ Allows users accessing /odoo/calendar to load backend calendar view directly """
        ensure_db()
        if not request.session.uid:
            return request.redirect_query('/web/login', query={'redirect': request.httprequest.full_path}, code=303)
        if kw.get('redirect'):
            return request.redirect(kw.get('redirect'), 303)
        check(request.session, request)

        subpath = kw.get('subpath') or ''
        is_calendar = (subpath == 'calendar') or request.httprequest.path.startswith('/odoo/calendar') or (s_action and 'calendar' in str(s_action))

        if not is_user_internal(request.session.uid) and not is_calendar:
            return request.redirect('/web/login_successful', 303)

        touch(request.session)
        request.update_env(user=request.session.uid)
        try:
            if request.env.user:
                request.env.user._on_webclient_bootstrap()
            context = request.env['ir.http'].webclient_rendering_context()

            hmac_payload = request.env.user._session_token_get_values()
            session_info = context.get("session_info")
            session_info['browser_cache_secret'] = hmac(request.env(su=True), "browser_cache_key", hmac_payload)

            response = request.render('web.webclient_bootstrap', qcontext=context)
            response.headers['X-Frame-Options'] = 'SAMEORIGIN'
            response.headers['Cache-Control'] = 'no-store'
            return response
        except AccessError:
            return request.redirect('/web/login?error=access')


