# -*- coding: utf-8 -*-
from odoo import models


class PortalEntry(models.Model):
    _inherit = "portal.entry"

    def _filter_visible_portal_cards(self):
        visible = super()._filter_visible_portal_cards()
        unwanted_urls = {
            '/my/invoices?filterby=invoices',
            '/my/invoices?filterby=bills',
            '/my/addresses',
            '/my/security',
        }
        unwanted_names = {
            'Your Invoices',
            'Our Invoices',
            'Addresses',
            'Connection & Security',
        }
        return visible.filtered(
            lambda c: c.url not in unwanted_urls and c.name not in unwanted_names
        )
