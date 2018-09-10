# -*- coding: utf-8 -*-

from odoo import _, api, fields, models

class Partner(models.Model):
    """ Update of res.users class
        - add a user list of devices registered on Google Cloud Message
    """
    _name = 'res.partner'
    _inherit = ['res.partner']

    gcm_device_ids = fields.One2many('google_gcm.device', 'partner_id', string='GCM devices')

