# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.http import request
from odoo.addons.web.controllers.home import Home
from odoo.addons.web.controllers.session import Session, logout


class HonnaSession(Session):

    @http.route('/web/session/logout', type='http', auth='public', methods=['GET', 'POST'], sitemap=False, csrf=False)
    def logout(self, redirect='/'):
        logout(request.session, keep_db=True)
        return request.redirect(redirect, 303)


class HonnaWebsiteLogin(Home):

    @http.route(['/login', '/web/login'], type='http', auth="public", website=True, sitemap=False, readonly=False)
    def web_login(self, redirect=None, **kw):
        """Custom Honna login matching Figma split-screen layout with native Odoo auth."""
        # If user is already authenticated and visits login directly
        if request.session.uid and not kw.get('force'):
            return request.redirect(self._login_redirect(request.session.uid, redirect=redirect))

        # Use Home.web_login to process authentication and credentials
        response = super().web_login(redirect=redirect, **kw)

        # On successful login or external redirect, return the redirect response immediately
        if getattr(response, 'is_qweb', True) is False or response.status_code in (301, 302, 303):
            return response

        # Render custom Figma login page on GET or on authentication errors
        values = getattr(response, 'qcontext', None) or {}
        values.update({
            'page_name': 'login',
            'redirect': redirect,
            'login': kw.get('login', values.get('login', '')),
            'error': values.get('error', None),
            'message': kw.get('message', values.get('message', None)),
        })
        return request.render('honna_campus_website.login_page_template', values)


class HonnaCampusWebsiteController(http.Controller):

    @http.route(['/', '/honna'], type='http', auth='public', website=True, sitemap=True)
    def honna_home(self, **kw):
        """Main Honna Education Homepage matching Figma Homepage V6."""
        programs = request.env['honna.campus.program'].sudo().search([('active', '=', True)], order='sequence, id')
        partners = request.env['honna.campus.partner'].sudo().search([('active', '=', True)], order='sequence, id')
        impact_counters = request.env['honna.campus.impact'].sudo().search([('metric_type', '=', 'counter')], order='sequence, id')
        growth_points = request.env['honna.campus.impact'].sudo().search([('metric_type', '=', 'growth')], order='year asc')
        testimonials = request.env['honna.campus.testimonial'].sudo().search([('active', '=', True)], order='sequence, id')

        values = {
            'page_name': 'home',
            'programs': programs,
            'partners': partners,
            'impact_counters': impact_counters,
            'growth_points': growth_points,
            'testimonials': testimonials,
        }
        return request.render('honna_campus_website.homepage_template', values)

    @http.route(['/about-us', '/campus'], type='http', auth='public', website=True, sitemap=True)
    def honna_about(self, **kw):
        """Honna Campus Next-Gen ICT Curricula Page matching Figma dark layout."""
        programs = request.env['honna.campus.program'].sudo().search([('active', '=', True), ('category', '=', 'holistic')], order='sequence, id')
        values = {
            'page_name': 'about',
            'programs': programs,
        }
        return request.render('honna_campus_website.about_page_template', values)

    @http.route(['/curriculum', '/courses'], type='http', auth='public', website=True, sitemap=True)
    def honna_curriculum(self, **kw):
        """Curriculum & Courses Showcase."""
        programs = request.env['honna.campus.program'].sudo().search([('active', '=', True)], order='sequence, id')
        values = {
            'page_name': 'curriculum',
            'programs': programs,
        }
        return request.render('honna_campus_website.curriculum_page_template', values)

    @http.route(['/execution', '/lab', '/workshop', '/competition'], type='http', auth='public', website=True, sitemap=True)
    def honna_features(self, **kw):
        """Program Feature Details Page."""
        path = request.httprequest.path.strip('/')
        values = {
            'page_name': path,
            'feature_title': path.capitalize(),
        }
        return request.render('honna_campus_website.feature_page_template', values)

    @http.route(['/shop'], type='http', auth='public', website=True, sitemap=True)
    def honna_shop(self, **kw):
        """Honna STEM Kits & Lab Hardware Shop."""
        values = {
            'page_name': 'shop',
        }
        return request.render('honna_campus_website.shop_page_template', values)

    @http.route(['/jobs', '/careers'], type='http', auth='public', website=True, sitemap=True)
    def honna_careers(self, **kw):
        """Honna Careers & Opportunities."""
        values = {
            'page_name': 'careers',
        }
        return request.render('honna_campus_website.careers_page_template', values)

    @http.route(['/contactus', '/contact'], type='http', auth='public', website=True, sitemap=True)
    def honna_contact(self, **kw):
        """Contact Us Page."""
        values = {
            'page_name': 'contact',
            'success': kw.get('success', False),
        }
        return request.render('honna_campus_website.contact_page_template', values)

    @http.route(['/honna/contact-submit'], type='http', auth='public', website=True, methods=['POST'], csrf=True)
    def honna_contact_submit(self, **post):
        """Handle contact form submission and generate CRM Lead."""
        name = post.get('name', '').strip()
        email = post.get('email', '').strip()
        phone = post.get('phone', '').strip()
        message = post.get('message', '').strip()

        if name and (email or phone):
            description = f"Contact inquiry via Honna Campus Website:\nName: {name}\nEmail: {email}\nPhone: {phone}\n\nMessage:\n{message}"
            lead_vals = {
                'name': f"Website Inquiry: {name}",
                'contact_name': name,
                'email_from': email,
                'phone': phone,
                'description': description,
                'type': 'lead',
            }
            try:
                request.env['crm.lead'].sudo().create(lead_vals)
            except Exception:
                pass

        return request.redirect('/contactus?success=1')
