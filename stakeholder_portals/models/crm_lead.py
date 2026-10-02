# -*- coding: utf-8 -*-
from odoo import models, fields


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    user_category = fields.Selection([
        ('honna_staff', 'Honna Staff'),
        ('association', 'Association'),
        ('school', 'School'),
        ('college', 'College'),
        ('academy', 'Academy'),
        ('partner', 'Partner'),
        ('others', 'Others'),
        ('school_college', 'School/College'),
        ('educator', 'Teacher'),
        ('ecosystem_partner', 'Ecosystem Partner'),
        ('student', 'Student'),
        ('parent', 'Parent'),
    ], string='User Category', index=True, copy=False)

    salutation = fields.Char(string='Salutation', copy=False)
    first_name = fields.Char(string='First Name', copy=False)
    last_name = fields.Char(string='Last Name', copy=False)
    registration_id_ref = fields.Char(string='Registration ID', copy=False)

    portal_type = fields.Selection([
        ('honna_staff', 'Honna Staff'),
        ('association', 'Association'),
        ('school', 'School'),
        ('college', 'College'),
        ('academy', 'Academy'),
        ('partner', 'Partner'),
        ('others', 'Others'),
        ('organisation', 'School/College'),
        ('school_college', 'School/College'),
        ('educator', 'Teacher'),
        ('ecosystem_partner', 'Ecosystem Partner'),
        ('student', 'Student'),
        ('parent', 'Parent'),
    ], string='Portal Type', copy=False, index=True)

    org_registration_id = fields.Many2one(
        'stakeholder.organisation',
        string='Institution Registration',
        readonly=True,
        copy=False,
    )


    # Association Portal Registration
    assoc_organisation_name = fields.Char(string='Organisation Name')
    assoc_organisation_code = fields.Char(string='Organisation Code')
    assoc_tax_gst = fields.Char(string='Tax / GST')
    assoc_trust_details = fields.Text(string='Trust Details')
    assoc_address = fields.Text(string='Address')
    assoc_geolocation = fields.Char(string='Geo-location')
    assoc_branch_code = fields.Char(string='Branch Code')
    assoc_contact_name = fields.Char(string='Contact Name')
    assoc_contact_role = fields.Char(string='Role')
    assoc_contact_time = fields.Char(string='Preferred Contact Time')
    assoc_secondary_phone = fields.Char(string='Secondary Phone')
    assoc_secondary_email = fields.Char(string='Secondary Email')
    assoc_registration_id = fields.Many2one(
        'stakeholder.association',
        string='Registration',
        readonly=True,
        copy=False,
    )
