# -*- coding: utf-8 -*-
import base64
import json
import logging
import re
from urllib.parse import urlencode
from markupsafe import Markup, escape

from odoo import http, _
from odoo.http import request

_logger = logging.getLogger(__name__)

ROLE_TITLES = {
    'honna_staff': 'Honna Staff',
    'association': 'Association',
    'school': 'School',
    'college': 'College',
    'academy': 'Academy',
    'partner': 'Partner',
    'others': 'Others',
    'organisation': 'School',
    'school_college': 'School',
    'educator': 'Teacher',
    'ecosystem_partner': 'Partner',
    'student': 'Student',
    'parent': 'Parent',
}



class StakeholderPortalController(http.Controller):

    def _format_lead_description(self, title, rows):
        """Build an HTML notes block for the CRM lead from label/value pairs."""
        lines = [f"<p><strong>{escape(title)}</strong></p><ul>"]
        for label, value in rows:
            if value not in (None, False, ''):
                lines.append(
                    f"<li><strong>{escape(str(label))}:</strong> {escape(str(value))}</li>"
                )
        lines.append("</ul>")
        return Markup("".join(lines))

    def _create_crm_lead(self, env, lead_vals):
        """Create a CRM lead for a portal registration. Failures are logged only."""
        try:
            vals = {
                'type': 'lead',
                'user_id': False,
                **lead_vals,
            }
            if not vals.get('company_id') and request.website:
                vals['company_id'] = request.website.company_id.id
            medium = env.ref('utm.utm_medium_website', raise_if_not_found=False)
            if medium and not vals.get('medium_id'):
                vals['medium_id'] = medium.id
            return env['crm.lead'].sudo().create(vals)
        except Exception:
            _logger.exception("Failed to create CRM lead for portal registration")
            return env['crm.lead']

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
            honna_group = sudo_env.ref('stakeholder_registration.group_stakeholder_user', raise_if_not_found=False)
            group_ids = [g.id for g in [group_user, honna_group] if g]

            if portal_type == 'association':
                assoc_group = sudo_env.ref('stakeholder_registration.group_association_user', raise_if_not_found=False)
                if assoc_group:
                    group_ids.append(assoc_group.id)
            elif portal_type in ('school', 'college', 'academy', 'organisation', 'school_college'):
                school_group = sudo_env.ref('stakeholder_registration.group_school_user', raise_if_not_found=False)
                if school_group:
                    group_ids.append(school_group.id)

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
            else:
                cat_val = 'honna_staff' if portal_type == 'honna_staff' else ('school' if portal_type in ('school', 'school_college', 'organisation') else portal_type)
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

            # 5. Create CRM Lead for tracking & visibility
            lead = self._create_crm_lead(sudo_env, {
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
                'org_registration_id': rec_id if portal_type != 'association' else False,
                'assoc_registration_id': rec_id if portal_type == 'association' else False,
                'description': self._format_lead_description(
                    _('%s Registration') % role_title,
                    [
                        (_('Role'), role_title),
                        (_('Salutation'), salutation),
                        (_('First Name'), first_name),
                        (_('Last Name'), last_name),
                        (_('Full Name'), display_name),
                        (_('Email'), email),
                        (_('Phone'), phone),
                        (_('Registration ID'), rec_id),
                    ]
                ),
            })
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
        lead = self._create_crm_lead(env, {
            'name': _('Student Registration: %s') % name,
            'contact_name': name,
            'email_from': email,
            'phone': phone,
            'portal_type': 'student',
            'user_category': 'student',
            'first_name': post.get('first_name') or name,
            'last_name': post.get('last_name') or '',
            'registration_id_ref': str(student_rec.id),
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
        lead = self._create_crm_lead(env, {
            'name': _('Parent Registration: %s') % name,
            'contact_name': name,
            'email_from': email,
            'phone': phone,
            'portal_type': 'parent',
            'user_category': 'parent',
            'first_name': post.get('first_name') or name,
            'last_name': post.get('last_name') or '',
            'registration_id_ref': str(parent_rec.id),
        })
        if lead:
            parent_rec.sudo().write({'lead_id': lead.id})
        return request.redirect('/web/login')


    @http.route(['/association/profile', '/my/association', '/stakeholder-portals/profile'], type='http', auth='public', website=True)
    def association_profile(self, **kw):
        """ Renders the Association / Organisation Profile page matching Figma Screenshots 2 & 3 """
        sudo_env = request.env(su=True)
        assoc = None
        assoc_id = kw.get('id')
        if assoc_id:
            try:
                assoc = sudo_env['stakeholder.association'].browse(int(assoc_id))
                if not assoc.exists():
                    assoc = None
            except Exception:
                assoc = None

        user = request.env.user
        if not assoc and user and user.id != request.env.ref('base.public_user').id:
            if hasattr(user, 'association_id') and user.association_id:
                assoc = user.association_id
            elif user.partner_id:
                assoc = sudo_env['stakeholder.association'].search([('partner_id', '=', user.partner_id.id)], limit=1)
            if not assoc and user.email:
                assoc = sudo_env['stakeholder.association'].search([('email', '=', user.email)], limit=1)

        # Fallback for preview / demo
        if not assoc:
            assoc = sudo_env['stakeholder.association'].search([], order='id desc', limit=1)

        countries = sudo_env['res.country'].search([('code', '=', 'IN')]) or sudo_env['res.country'].search([], limit=10)
        states = sudo_env['res.country.state'].search([('country_id.code', '=', 'IN')])

        return request.render('stakeholder_portals.association_profile_page', {
            'association': assoc,
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
        mem_desig = (post.get('new_member_designation') or mem_role).strip()

        if mem_first or mem_last or mem_email:
            sudo_env['stakeholder.association.member'].create({
                'association_id': assoc.id,
                'first_name': mem_first,
                'last_name': mem_last,
                'name': f"{mem_first} {mem_last}".strip() or mem_email,
                'role': mem_role or 'Member',
                'designation': mem_desig or mem_role or 'Member',
                'email': mem_email,
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

    @http.route(['/school/profile', '/my/school', '/stakeholder-portals/school'], type='http', auth='public', website=True)
    def school_profile(self, **kw):
        """ Renders the School Profile multi-step wizard matching Screenshots 1, 2, 3 """
        sudo_env = request.env(su=True)
        school = None
        school_id = kw.get('id')
        if school_id:
            try:
                school = sudo_env['stakeholder.organisation'].browse(int(school_id))
                if not school.exists() or (school.category and school.category != 'school'):
                    school = None
            except Exception:
                school = None

        user = request.env.user
        if not school and user and user.id != request.env.ref('base.public_user').id:
            if user.partner_id:
                school = sudo_env['stakeholder.organisation'].search([
                    ('partner_id', '=', user.partner_id.id),
                    ('category', '=', 'school')
                ], limit=1)
            if not school and user.email:
                school = sudo_env['stakeholder.organisation'].search([
                    ('email', '=', user.email),
                    ('category', '=', 'school')
                ], limit=1)

        # Fallback for preview / demo
        if not school:
            school = sudo_env['stakeholder.organisation'].search([('category', '=', 'school')], order='id desc', limit=1)

        countries = sudo_env['res.country'].search([('code', '=', 'IN')]) or sudo_env['res.country'].search([], limit=10)
        states = sudo_env['res.country.state'].search([('country_id.code', '=', 'IN')])
        associations = sudo_env['stakeholder.association'].search([], order='name asc')
        parent_schools = sudo_env['stakeholder.organisation'].search([
            ('category', '=', 'school'),
            ('id', '!=', school.id if school else 0)
        ], order='name asc')

        step = 1
        try:
            step = int(kw.get('step', 1))
        except (ValueError, TypeError):
            step = 1

        return request.render('stakeholder_portals.school_profile_page', {
            'school': school,
            'countries': countries,
            'states': states,
            'associations': associations,
            'parent_schools': parent_schools,
            'saved': kw.get('saved') == '1',
            'action_type': kw.get('action_type', 'save'),
            'current_step': step,
        })

    @http.route(['/school/profile/save'], type='http', auth='public', website=True, methods=['POST'], csrf=True)
    def school_profile_save(self, **post):
        """ Handles school profile updates and multi-step submissions matching Screenshots """
        sudo_env = request.env(su=True)
        school_id = post.get('school_id')
        school = None
        if school_id:
            try:
                school = sudo_env['stakeholder.organisation'].browse(int(school_id))
            except Exception:
                pass

        if not school or not school.exists():
            user = request.env.user
            if user and user.id != request.env.ref('base.public_user').id and user.partner_id:
                school = sudo_env['stakeholder.organisation'].search([
                    ('partner_id', '=', user.partner_id.id),
                    ('category', '=', 'school')
                ], limit=1)
            if not school:
                school = sudo_env['stakeholder.organisation'].search([('category', '=', 'school')], order='id desc', limit=1)

        if not school:
            return request.redirect('/school/profile')

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

        # Parent Organisation
        if post.get('parent_organisation_id'):
            try:
                vals['parent_organisation_id'] = int(post.get('parent_organisation_id'))
            except (ValueError, TypeError):
                pass
        elif post.get('parent_org_name'):
            p_name = post.get('parent_org_name').strip()
            p_org = sudo_env['stakeholder.association'].search([('name', 'ilike', p_name)], limit=1)
            if not p_org and p_name:
                p_org = sudo_env['stakeholder.association'].create({'name': p_name})
            if p_org:
                vals['parent_organisation_id'] = p_org.id

        # Parent School / Head Office
        if post.get('parent_school_id'):
            try:
                vals['parent_school_id'] = int(post.get('parent_school_id'))
            except (ValueError, TypeError):
                pass
        elif post.get('parent_school_name'):
            ps_name = post.get('parent_school_name').strip()
            p_sch = sudo_env['stakeholder.organisation'].search([('name', 'ilike', ps_name), ('category', '=', 'school')], limit=1)
            if not p_sch and ps_name:
                p_sch = sudo_env['stakeholder.organisation'].create({'name': ps_name, 'category': 'school'})
            if p_sch:
                vals['parent_school_id'] = p_sch.id

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

        # School Contacts
        if post.get('phone'):
            vals['phone'] = post.get('phone').strip()
        if post.get('email'):
            vals['email'] = post.get('email').strip()

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

        # Action: Draft vs Save
        action_type = post.get('action') or 'save'
        if action_type == 'draft':
            vals['state'] = 'draft'
        elif action_type == 'save' and school.state == 'draft':
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

        if vals:
            school.sudo().write(vals)

        # Handle Member Add or Edit
        mem_cat = (post.get('member_category') or 'executive').strip().lower()
        mem_model_name = 'stakeholder.organisation.board.member'
        if mem_cat == 'academic':
            mem_model_name = 'stakeholder.organisation.dept.head'
        elif mem_cat == 'operations':
            mem_model_name = 'stakeholder.organisation.operation.member'

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
                'role': mem_role or 'Member',
                'designation': mem_role or 'Member',
                'email': mem_email,
                'phone': mem_phone,
                'is_primary': mem_primary,
            }
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
            try:
                del_rec = sudo_env[del_model].browse(int(delete_member_id))
                if del_rec.exists() and del_rec.organisation_id.id == school.id:
                    del_rec.unlink()
            except Exception:
                pass

        step = post.get('current_step') or '1'

        if request.httprequest.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in request.httprequest.headers.get('Accept', ''):
            return request.make_json_response({
                'status': 'success',
                'message': _("School profile updated successfully!"),
                'action_type': action_type,
                'step': step,
            })

        return request.redirect(f'/school/profile?id={school.id}&saved=1&step={step}&action_type={action_type}')

    @http.route(['/stakeholder-portals/success', '/registration/success'], type='http', auth='public', website=True)
    def portals_success(self, **kw):
        """ Direct redirect to login page """
        return request.redirect('/web/login')
