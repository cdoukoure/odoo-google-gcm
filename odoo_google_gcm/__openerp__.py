# -*- coding: utf-8 -*-
{
    'name': "Google Cloud Message",

    'summary': """
        Push notification on phone, tablet devices""",

    'description': """
        Send data from your server to your users' phone devices, and receive messages from devices on the same connection.
    """,

    'author': "Jean-Charles Doukouré",
    'website': "",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'Tools',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/res_partner_views.xml',
        'views/gcm_server_views.xml',
        'views/gcm_message_views.xml',
        'views/gcm_device_views.xml',
        #'templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo.xml',
    ],
}