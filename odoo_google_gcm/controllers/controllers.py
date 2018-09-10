# -*- coding: utf-8 -*-
import openerp

from openerp import http
from openerp.http import request
from openerp.addons.web.controllers.main import ensure_db

class GoogleGcm(http.Controller):
 
#    _cp_path = "/web/binary"
# 
#    @http.route('/google_gcm/google_gcm/', auth='public')
#    def index(self, **kw):
#         return "Hello, world"
#
#    @http.route('/google_gcm/google_gcm/objects/', auth='public')
#    def list(self, **kw):
#        return http.request.render('google_gcm.listing', {
#            'root': '/google_gcm/google_gcm',
#            'objects': http.request.env['google_gcm.google_gcm'].search([]),
#        })
#
#    @http.route('/google_gcm/google_gcm/objects/<model("google_gcm.google_gcm"):obj>/', auth='public')
#    def object(self, obj, **kw):
#        return http.request.render('google_gcm.object', {
#            'object': obj
#        })

    @http.route('/google_gcm', auth='none')
    def index(self, **kw):
         return "Hello, world"

    @http.route('/google_gcm/device/register', type='http', auth='none')
    def register(self, **kw):
        ensure_db()
        if not request.uid:
            request.uid = openerp.SUPERUSER_ID
    
        if request.httprequest.method == 'POST':
            uid = request.session.authenticate(request.params['db'], request.params['login'], request.params['password'])
            if uid is not False:
                user = request.env['res.users'].sudo().browse([uid])
                devices = request.env['google_gcm.device']
                device = devices.sudo().create({
                    'gcm_reg_id': request.params['regId'],
                    'partner_id': user.partner_id
                })
                #values['success'] = "Your device has been registered successfully !!!"
                #return True
            #values = "Wrong login/password for the specified database !!!"
        #return request.render('google_gcm.device_register', values)
        return 'Register page for phone <a href="/google_gcm">Return to index Google Cloud Message</a>'

    @http.route('/google_gcm/device/login', type='http', auth="none")
    def web_login(self, redirect=None, **kw):
        ensure_db()
        request.params['login_success'] = False
        if request.httprequest.method == 'GET' and redirect and request.session.uid:
            return http.redirect_with_hash(redirect)

        if not request.uid:
            request.uid = openerp.SUPERUSER_ID

        values = request.params.copy()
        try:
            values['databases'] = http.db_list()
        except openerp.exceptions.AccessDenied:
            values['databases'] = None

        if request.httprequest.method == 'POST':
            old_uid = request.uid
            uid = request.session.authenticate(request.session.db, request.params['login'], request.params['password'])
            if uid is not False:
                request.params['login_success'] = True
                if not redirect:
                    redirect = '/web'
                return http.redirect_with_hash(redirect)
            request.uid = old_uid
            values['error'] = "Wrong login/password"
        return request.render('web.login', values)

