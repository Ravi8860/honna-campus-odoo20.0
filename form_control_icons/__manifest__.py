# Copyright 2026 TechUltra Solutions Private Limited
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
{
    "name": "Custom Form Save / Cancel Buttons",
    "summary": "Show labeled Save and Cancel buttons instead of icon-only controls on all form views.",
    "version": "20.0.1.0.0",
    "category": "Hidden",
    "author": "Ravi Parmar",
    "website": "",
    "license": "LGPL-3",
    "depends": ["web"],
    "assets": {
        "web.assets_backend": [
            "form_control_icons/static/src/scss/form_control_icons.scss",
            "form_control_icons/static/src/xml/form_status_indicator.xml",
            "form_control_icons/static/src/xml/form_buttons.xml",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
