# -*- coding: utf-8 -*-
{
    'name': 'Honna Campus Website',
    'version': '20.0.1.0.0',
    'category': 'Website/Website',
    'summary': 'Next-Generation ICT & STEM Learning Platform matching Figma prototype',
    'description': """
Honna Campus & Honna Education Website
=======================================
Complete, pixel-perfect frontend website and portal integration for Honna Campus matching the Figma prototype:
- Honna Education Homepage V6: Arched hero carousel, What We Do wave, Why Choose Honna, Our Impact with growth curve, Partner Schools carousel, Contact Us form, and Mascot Login Modal.
- Honna Campus Platform: Dark luxury theme, Next-Generation ICT & Computer Curricula, Where It All Began story & 2022/50k+ stats, 9-card Holistic Tech Education glowing grid, and CTA banner.
- Curriculum, Courses, Hardware Shop, Careers, and Contact pages.
- Backend dynamic management for partner schools, impact metrics, programs, and testimonials.
- Seamless integration with Stakeholder Portals.
    """,
    'author': 'leapai.ai',
    'website': 'https://honna.in',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'website',
        'crm',
    ],
    'data': [
        'security/ir.access.csv',
        'data/default_data.xml',
        'data/website_menu.xml',
        'views/layout_templates.xml',
        'views/home_templates.xml',
        'views/about_templates.xml',
        'views/courses_templates.xml',
        'views/shop_templates.xml',
        'views/jobs_templates.xml',
        'views/contact_templates.xml',
        'views/login_templates.xml',
        'views/admin_views.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'honna_campus_website/static/src/css/honna_style.css',
            'honna_campus_website/static/src/js/honna_website.js',
        ],
    },
    'images': [
        'static/src/img/hero_boy_rover.png',
        'static/src/img/hero_arch_1.png',
        'static/src/img/robot_mascot.png',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
