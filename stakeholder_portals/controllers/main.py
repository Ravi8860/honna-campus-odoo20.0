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

    def _send_signup_email(self, user, env):
        """
        Trigger Odoo-based signup email notification.
        Prepares signup token and sends set_password_email.
        Guarantees that a mail.mail record is generated and delivery is attempted.
        """
        try:
            # 1. Prepare partner signup token and validity
            user.partner_id.sudo().signup_prepare(signup_type='signup')

            # 2. Get Odoo auth_signup invitation email template
            tmpl = env.ref('auth_signup.set_password_email', raise_if_not_found=False) or \
                   env.ref('auth_signup.portal_set_password_email', raise_if_not_found=False)

            if tmpl:
                mail_id = tmpl.sudo().send_mail(
                    user.id,
                    force_send=True,
                    raise_exception=False,
                    email_values={
                        'email_to': user.email,
                        'auto_delete': False,
                    }
                )
                _logger.info("Odoo signup email created with id %s for user %s (%s)", mail_id, user.name, user.login)
                return mail_id
            else:
                # Fallback to standard action_reset_password if template ref not found
                user.sudo().with_context(create_user=1).action_reset_password()
                _logger.info("Odoo signup email sent via action_reset_password for user %s", user.login)
        except Exception as e:
            _logger.exception("Failed to send signup email for user %s: %s", user.login, e)

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
        success_message = kw.get('success_message')
        if kw.get('success') and kw.get('email'):
            success_message = _("Registration submitted successfully! A signup invitation email has been sent to %s. Please check your email to set your password and log in.") % kw.get('email')
        return request.render('stakeholder_portals.registration_page', {
            'errors': {},
            'values': kw,
            'success_message': success_message,
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

            # 3. Create res.users
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
            user = sudo_env['res.users'].sudo().create(user_vals)

            # 4. Create stakeholder record
            rec_id = False
            rec = None
            if portal_type == 'association':
                assoc_vals = {
                    'name': display_name,
                    'contact_name': display_name,
                    'primary_contact_first_name': first_name,
                    'primary_contact_last_name': last_name,
                    'email': email,
                    'phone': phone,
                    'state': 'approved',
                    'partner_id': partner.id,
                    'user_id': user.id,
                }
                rec = sudo_env['stakeholder.association'].sudo().create(assoc_vals)
                rec_id = rec.id
            else:
                cat_val = 'honna_staff' if portal_type == 'honna_staff' else ('school' if portal_type in ('school', 'school_college', 'organisation') else portal_type)
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
                    'user_id': user.id,
                }
                rec = sudo_env['stakeholder.organisation'].sudo().create(org_vals)
                rec_id = rec.id

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

            # 6. Trigger Odoo-based signup email notification
            self._send_signup_email(user, sudo_env)

            # 7. Redirect to login with confirmation message
            msg = _("Registration submitted successfully! A signup invitation email has been sent to %s. Please check your email to set your password and log in.") % email
            return request.redirect('/web/login?%s' % urlencode({'login': email, 'message': msg}))



        except Exception as e:
            _logger.exception("Error processing stakeholder registration submission")
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


    @http.route(['/stakeholder-portals/success', '/registration/success'], type='http', auth='public', website=True)
    def portals_success(self, **kw):
        """ Direct redirect to login page """
        return request.redirect('/web/login')
