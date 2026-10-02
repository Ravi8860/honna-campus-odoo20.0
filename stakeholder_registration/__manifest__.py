# -*- coding: utf-8 -*-
{
    'name': 'Stakeholder Registration',
    'version': '20.0.1.0.0',
    'category': 'Administration',
    'summary': 'Dedicated tables for capturing Association, Organisation, Student, and Parent registrations',
    'description': """
Stakeholder Registration
========================
Provides custom tables for storing registration submissions:
- `stakeholder.association`
- `stakeholder.organisation`
- `stakeholder.student`
- `stakeholder.parent`

Security
--------
- Association User: Association and School menus only
- User: full Eco System Partners access including Student and Parent
    """,
    'author': 'leapai.ai',
    'website': 'https://leapai.ai',
    'license': 'LGPL-3',
    'depends': ['base', 'mail'],
    'data': [
        'security/stakeholder_security.xml',
        'security/ir.access.csv',
        'data/student_profile_sequence.xml',
        'data/facility_data.xml',
        'data/skill_program_data.xml',
        'views/stakeholder_views.xml',
        'views/res_users_views.xml',
        'views/res_partner_views.xml',
    ],

    'installable': True,
    'application': True,
    'auto_install': False,
}
