{
    'name': 'Sterio Backend (Community)',
    'version': '20.0.1.0.0',
    'summary': 'Modern professional backend UI theme for Odoo 20',
    'description': """
A fully customized backend theme with:
- Custom sidebar
- Enhanced navbar
- Stylish list & kanban views
- Professional color scheme

Free community theme by Steriotites.
    """,
    'author': 'Steriotites',
    'website': '',
    'license': 'LGPL-3',
    'category': 'Themes/Backend',
    'depends': [
        'base',
        'web',
        'mail',
    ],
    'data': [],
    'demo': [],
    'assets': {
        'web.assets_backend': [
            'steriotites_backend_theme/static/src/xml/webClient.xml',
            'steriotites_backend_theme/static/src/xml/navbar.xml',
            'steriotites_backend_theme/static/src/scss/web_client.scss',
            'steriotites_backend_theme/static/src/js/sidebar_menu.js',
            'steriotites_backend_theme/static/src/js/user_menu.js',
        ],
    },
    'images': [
        'static/description/main_screenshot.png',
        'static/description/main_screen.png',
        'static/description/main_1.png',
        'static/description/main_2.png',
        'static/description/main_3.png',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,

}


