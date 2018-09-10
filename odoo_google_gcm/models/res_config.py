# -*- coding: utf-8 -*-

from odoo import api, fields, models


class GoogleGcmConfigSettings(models.TransientModel):
    _name = 'google_gcm.config.settings'
    """ Inherit the base settings to add a counter of failed email + configure
    the alias domain. """
    _inherit = 'base.config.settings'
    
    
    module_google_gcm = fields.boolean('Allow notification by Google Cloud Message',
                                              help="""This install the module google_gcm.""")

#    @api.multi
#    def open_google_gcm(self):
#        server = self.env['google_gcm.server'].browse()
#        return {
#            'type': 'ir.actions.act_window',
#            'name': 'Google Cloud Message',
#            'view_type': 'form',
#            'view_mode': 'form',
#            'res_model': 'google_gcm.server',
#            'res_id': server.id,
#            'target': 'current',
#        }