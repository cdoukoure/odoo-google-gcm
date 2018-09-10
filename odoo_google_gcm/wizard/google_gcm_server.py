# -*- coding: utf-8 -*-
from gcm import GCM
from odoo import models, fields, api
import odoo.tools as tools

class gcm_server(models.Model):
    _name = 'google_gcm.server'
    _description = 'GCM Settings'
    _rec_name ='sender_id'

    sender_id = fields.Char('Sender ID', required=True, help="Put here your project id")
    api_key = fields.Char('Api Key', required=True, help="Put here your api key")
    delay_while_idle = fields.Boolean('Delay while idle', default=False)
    time_to_live = fields.Integer('Time to live', default=2419200)
    dry_run = fields.Boolean('Dry run', default=False)
    active = fields.Boolean('Active', default=True)


class GcmServerWizard(models.TransientModel):
    _name = 'google_gcm.server_wizard'

    session_id = fields.Many2one('openacademy.session',string="Session", required=True)
    attendee_ids = fields.Many2many('res.partner', string="Attendees")


