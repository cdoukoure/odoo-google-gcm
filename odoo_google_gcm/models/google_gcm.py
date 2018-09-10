# -*- coding: utf-8 -*-
from gcmclient import *
import logging
import psycopg2
from odoo import models, fields, api
import odoo.tools as tools
from odoo.addons.base.ir.ir_mail_server import MailDeliveryException
from odoo.tools.translate import _
from odoo.exceptions import UserError


_logger = logging.getLogger(__name__)


class GcmServer(models.Model):
    _name = 'google_gcm.server'
    _description = 'GCM Settings'

    name = fields.Char('Name', required=True)
    sequence = fields.Integer('Sequence', select=True, help="Gives the sequence order when displaying a list of server.")
    sender_id = fields.Char('Sender ID', required=True, help="Put here your project id")
    api_key = fields.Char('Api Key', required=True, help="Put here your api key")
    collapse_key = fields.Char('Collapse key', help="Put your collapse key")
    delay_while_idle = fields.Boolean('Delay while idle', default=False)
    time_to_live = fields.Integer('Time to live', default=3600)
    #dry_run = fields.Boolean('Dry run', default=False)
    state = fields.Selection([
        ('draft', 'Not Connected'),
        ('done', 'Connected'),
    ], 'Status', readonly=True, copy=False, default='draft')
    active = fields.Boolean('Active', default=True)
    
    @api.multi
    def test_gcm_server_connection(self):
        for gcm_server in self:
            gcm = GCM(gcm_server.api_key)
            # Construct (key => scalar) payload. do not use nested structures.
            data = {'str': 'string', 'int': 10}

            # Unicast or multicast message, read GCM manual about extra options.
            # It is probably a good idea to always use JSONMessage, even if you send
            # a notification to just 1 registration ID.
            #unicast = PlainTextMessage("11111", data, dry_run=gcm_server.dry_run)
            multicast = JSONMessage(["registration_id_1", "registration_id_2"], data, collapse_key=gcm_server.collapse_key, dry_run=True)

            try:
                # attempt send
                #res_unicast = gcm.send(unicast)
                res_multicast = gcm.send(multicast)
                #gcm_server.state = 'done'
                gcm_server.write({'state': 'done'})
                return {'warning':
                    {
                        'title': _('Warning'),
                        'message': _('Connection Test Succeeded! Everything seems properly set up!')
                    }
                }
            except GCMAuthenticationError:
                # stop and fix your settings
                raise UserError(_("Connection Test Failed! Please check your ApiKey"))
            except ValueError, e:
                # probably your extra options, such as time_to_live,
                # are invalid. Read error message for more info.
                raise UserError(_("Invalid message/option or invalid GCM response:\n %s") % tools.ustr(e))
            except Exception:
                # your network is down or maybe proxy settings
                # are broken. when problem is resolved, you can
                # retry the whole message.
                raise UserError(_("There was an internal error in the GCM server while trying to process the request!"))
    
        #raise UserError(_("Connection Test Succeeded! Everything seems properly set up!"))

    #@api.one
    @api.onchange('api_key')
    def _onchange_api_key(self):
        self.state = 'draft'



class GcmDevice(models.Model):
    _name = 'google_gcm.device'
    _description = 'Users registered devices'
    _rec_name = 'gcm_reg_id'

    gcm_reg_id = fields.Char('Registration ID', required=True)
    #partner_id = fields.Many2one('res.partner', 'Partner', required=True, readonly=True, ondelete='restrict', index=True, copy=True)
    partner_id = fields.Many2one(
        'res.partner', 'Partner', select=1,
        ondelete='restrict',
        help="Partner ownering this device")
    active = fields.Boolean(default=True)

class GcmMessage(models.Model):
    _name = 'google_gcm.message'

    @api.model
    def _get_default_author(self):
        return self.env.user.partner_id
    
    @api.model
    def _get_default_gcm_server(self):
        server = self.env['google_gcm.server'].sudo().search([('active', '=', True),('state', '=', 'done')], limit=1, order='sequence asc')
        return server

    name = fields.Char('Title', required=True)
    content = fields.Text('Message')
    date = fields.Datetime('Date', default=fields.Datetime.now)
    recipient_ids = fields.Many2many('res.partner', string='To (Users)')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('exception', 'Delivery Failed'),
        ('cancel', 'Cancelled'),
    ], 'Status', readonly=True, copy=False, default='draft')
    author_id = fields.Many2one(
        'res.partner', 'Author', readonly=True, select=1,
        ondelete='set null', default=_get_default_author,
        help="Author of the notification.")
    gcm_server_id = fields.Many2one('google_gcm.server', 'Gcm server', readonly=1, default=_get_default_gcm_server)
    auto_delete = fields.Boolean(
        'Auto Delete',
        help="Permanently delete this Google Message after sending it, to save space")
    state_reason = fields.Text(
        'State Reason', readonly=1,
        help="State reason. This is usually the exception thrown by the gcm server, stored to ease the debugging of delivering issues.")

    @api.multi
    def compute_gcm_server(self):
        server = None
        server = self.env['google_gcm.server'].sudo().search([('active', '=', True),('state', '=', 'done')], limit=1, order='sequence asc')
        if not server:
            raise UserError(_("No valid server retreived !"))
        return self.write({'gcm_server_id': server.id})

    @api.multi
    def mark_draft(self):
        return self.write({'state': 'draft'})

    @api.multi
    def cancel(self):
        return self.write({'state': 'cancel'})
    
    @api.multi
    def send_get_gcm_body(self, partner=None):
        """Return a specific ir_email body. The main purpose of this method
        is to be inherited to add custom content depending on some module."""
        self.ensure_one()
        body = self.content or ''
        return tools.html2plaintext(body)
    
    @api.multi
    def send(self):

        # Get GCM Server Details
        gcm_server = None
        if self.gcm_server_id:
            gcm_server = self.gcm_server_id
        elif not gcm_server:
            gcm_server = self.env['google_gcm.server'].sudo().search([('active', '=', True),('state', '=', 'done')], limit=1, order='sequence')
        
        if not gcm_server:
            raise UserError(_("Missing GCM Server")+ "\n" + _("Please re-compute server, or provide the GCM parameters explicitly."))
        
        gcm_server.ensure_one()

        for gc_message in self:
            try:

                # specific behavior to customize the send gcm for notified partners
                gcm_device_list = []
                for partner in gc_message.recipient_ids:
                    for device in partner.gcm_device_ids:
                        gcm_device_list.append(device.gcm_reg_id)
            
                if len(gcm_device_list) == 0:
                    raise UserError(_("Missing Recipients")+ "\n" + _("Please define recipients that own at least one registered device."))

                # Writing on the gcm object may fail (e.g. lock on user) which
                # would trigger a rollback *after* actually sending the email.
                # To avoid sending twice the same email, provoke the failure earlier
                gc_message.write({
                    'state': 'exception',
                    'state_reason': _('Error without exception. Probably due do sending an google notification without computed recipients.'),
                })
                
                gcm = GCM(gcm_server.api_key)
                
                data = {'Title': gc_message.send_get_gcm_body(gc_message.name), 'Content': gc_message.send_get_gcm_body(gc_message.content)}
                
                """response = gcm.json_request(
                    registration_id = gcm_device_list,
                    data = data,
                    collapse_key = gcm_server.collapse_key,
                    delay_while_idle = gcm_server.delay_while_idle,
                    time_to_live = gcm_server.time_to_live
                )
                """
                
                message = JSONMessage(
                    gcm_device_list,
                    data,
                    collapse_key = gcm_server.collapse_key,
                    delay_while_idle = gcm_server.delay_while_idle,
                    time_to_live = gcm_server.time_to_live,
                    dry_run=True
                )
                response = gcm.send(message)
                
                state_reason = ''
        
                for reg_id, msg_id in response.success.items():
                    state_reason += '-Success for reg_id %s' % reg_id
                    _logger.info('GCM Notification with Title %r successfully sent to device reg_id %r', gc_message.name, reg_id)
                    if gc_message.auto_delete:
                        _logger.info("Deleting google_gcm.message %s :%s after success sending ('auto delete' option checked)",gc_message.id, gc_message.name)

                for reg_id in response.not_registered:
                    device = self.env['google_gcm.device'].search([('gcm_reg_id', '=', reg_id)])
                    _logger.info("Deleting invalid recipients for google_gcm.message %s: %s",device.partner_id.name, device.gcm_reg_id)
                    state_reason += "Deleting invalid recipients for google_gcm.message " + device.partner_id.name + ":"+device.gcm_reg_id
                    device.unlink()
                
                for reg_id, err_code in response.failed.items():
                    device = self.env['google_gcm.device'].search([('gcm_reg_id', '=', reg_id)])
                    _logger.info("Deleting  google_gcm.device %s: %s because %s",device.partner_id.name, device.gcm_reg_id, err_code)
                    state_reason += "Deleting  google_gcm.device " + device.partner_id.name + ":" + device.gcm_reg_id + " because " + err_code
                    device.unlink()

                for reg_id, new_reg_id in response.canonical.items():
                    # Repace reg_id with canonical_id in your database
                    device = self.env['google_gcm.device'].search([('gcm_reg_id', '=', reg_id)])
                    _logger.info("Updating recipients registration_id %s: %s to %s during google_gcm.message sent",device.partner_id.name, device.gcm_reg_id, new_reg_id)
                    state_reason += "Updating recipients registration_id of " + device.partner_id.name + ":" + device.gcm_reg_id + " to " + new_reg_id + " during google_gcm.message sent"
                    device.gcm_reg_id = new_reg_id
                    
                if response.needs_retry():
                    # construct new message with only failed regids
                    retry_msg = response.retry()
                    # you have to wait before attemting again. delay()
                    # will tell you how long to wait depending on your
                    # current retry counter, starting from 0.
                    _logger.info("Wait or schedule task after %s seconds",response.delay(retry))
                    state_reason += "Wait or schedule task after "+ response.delay(retry) +" seconds"
                    # retry += 1 and send retry_msg again

                gc_message.write({'state': 'sent', 'state_reason': state_reason})
            except MemoryError:
                # prevent catching transient MemoryErrors, bubble up to notify user or abort cron job
                # instead of marking the mail as failed
                _logger.exception(
                    'MemoryError while processing GCM Notification with ID %r and Title %r. Consider raising the --limit-memory-hard startup option',
                    gc_message.id, gc_message.name)
                raise
            except psycopg2.Error:
                # If an error with the database occurs, chances are that the cursor is unusable.
                # This will lead to an `psycopg2.InternalError` being raised when trying to write
                # `state`, shadowing the original exception and forbid a retry on concurrent
                # update. Let's bubble it.
                raise
            except Exception as e:
                failure_reason = tools.ustr(e)
                _logger.exception('failed sending google notification (id: %s) due to %s', gc_message.id, failure_reason)
                gc_message.write({'state': 'exception', 'state_reason': failure_reason})
                if isinstance(e, AssertionError):
                    # get the args of the original error, wrap into a value and throw a MailDeliveryException
                    # that is an except_orm, with name and value as arguments
                    value = '. '.join(e.args)
                    raise MailDeliveryException(_("Google Cloud Message Delivery Failed"), value)
                raise

        return True
