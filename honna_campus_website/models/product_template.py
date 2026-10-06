# -*- coding: utf-8 -*-
from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    website_product_label = fields.Char(
        string='Website Product Label',
        help='Category or target label on website shop card (e.g., K-12 Kit, Advanced Lab, AI Assistant)',
        translate=True,
    )
    website_product_badge = fields.Char(
        string='Website Product Badge',
        help='Badge or edition tag on website shop card (e.g., School Edition, Turnkey Lab, SaaS Solution)',
        translate=True,
    )
    website_short_description = fields.Text(
        string='Website Short Description',
        help='Concise product summary displayed on website shop cards',
        translate=True,
    )
    website_cta_type = fields.Selection([
        ('request_quote', 'Request Quote'),
        ('request_demo', 'Request Demo'),
        ('add_to_cart', 'Add to Cart'),
        ('view_product', 'View Product'),
    ], string='Website CTA Type', default='request_quote', required=True,
       help='Action triggered when visitor clicks the card call-to-action button')
    website_featured = fields.Boolean(
        string='Featured on Website',
        default=False,
        index=True,
        help='Check to showcase this product in the featured Shop section.',
    )
    website_sequence = fields.Integer(
        string='Website Sequence',
        default=10,
        help='Display sequence order on the website shop page.',
    )
