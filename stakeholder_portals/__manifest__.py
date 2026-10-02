# -*- coding: utf-8 -*-
{
    'name': 'Stakeholder Portals',
    'version': '20.0.1.0.0',
    'category': 'Website/Website',
    'summary': 'Unified Custom Portal System for Associations, Organisations, Students, and Parents',
    'description': """
Stakeholder Portals
====================
Provides custom registration portals for:
- Association Portal
- School Portal
- Student Portal
- Parent Portal

Features:
- Dynamic, responsive multi-step registration forms with frontend/backend validation
- Integration with res.partner and student.profile
- Automatic CRM lead creation on registration submit
- Association Portal fields on CRM lead form tab
- Relational mapping of contacts, management members, facilities, and skill programs
- Beautiful, Glassmorphic Dashboard for Students and Parents
    """,
    'author': 'leapai.ai',
    'website': 'https://leapai.ai',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'website', 'account', 'crm', 'stakeholder_registration', 'honna_campus_website'],
    'data': [
        'security/ir.access.csv',
        'data/website_menu.xml',
        'data/mock_data.xml',
        'views/portal_templates.xml',
        'views/stakeholder_crm_views.xml',
        'views/crm_lead_views.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            '/stakeholder_portals/static/src/css/portal.css',
            '/stakeholder_portals/static/src/js/portal.js',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
