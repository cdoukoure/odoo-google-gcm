# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests import common


class TestGCMBase(common.SavepointCase):
    @classmethod
    def setUpClass(cls):
        super(TestContractBase, cls).setUpClass()
        cls.partner = cls.env.ref('base.res_partner_2')
        cls.product = cls.env.ref('product.product_product_2')
        cls.product.taxes_id += cls.env['account.tax'].search(
            [('type_tax_use', '=', 'sale')], limit=1)
        cls.product.description_sale = 'Test description sale'
        cls.template_vals = {
            'recurring_rule_type': 'yearly',
            'recurring_interval': 12345,
            'name': 'Test Contract Template',
        }
        cls.template = cls.env['account.analytic.contract'].create(
            cls.template_vals,
        )
        cls.contract = cls.env['account.analytic.account'].create({
            'name': 'Test Contract',
            'partner_id': cls.partner.id,
            'pricelist_id': cls.partner.property_product_pricelist.id,
            'recurring_invoices': True,
            'date_start': '2016-02-15',
            'recurring_next_date': '2016-02-29',
        })
        cls.contract2 = cls.env['account.analytic.account'].create({
            'name': 'Test Contract 2',
            'partner_id': cls.partner.id,
            'pricelist_id': cls.partner.property_product_pricelist.id,
            'recurring_invoices': True,
            'date_start': '2016-02-15',
            'recurring_next_date': '2016-02-29',
            'contract_type': 'purchase',
        })
        cls.line_vals = {
            'analytic_account_id': cls.contract.id,
            'product_id': cls.product.id,
            'name': 'Services from #START# to #END#',
            'quantity': 1,
            'uom_id': cls.product.uom_id.id,
            'price_unit': 100,
            'discount': 50,
        }
        cls.acct_line = cls.env['account.analytic.invoice.line'].create(
            cls.line_vals,
        )


class TestGCM(TestGCMBase):
    def _add_template_line(self, overrides=None):
        if overrides is None:
            overrides = {}
        vals = self.line_vals.copy()
        vals['analytic_account_id'] = self.template.id
        vals.update(overrides)
        return self.env['account.analytic.contract.line'].create(vals)

    def test_check_discount(self):
        with self.assertRaises(ValidationError):
            self.acct_line.write({'discount': 120})

    def test_automatic_price(self):
        self.acct_line.automatic_price = True
        self.product.list_price = 1100
        self.assertEqual(self.acct_line.price_unit, 1100)
        # Try to write other price
        self.acct_line.price_unit = 10
        self.acct_line.refresh()
        self.assertEqual(self.acct_line.price_unit, 1100)
        # Now disable automatic price
        self.acct_line.automatic_price = False
        self.acct_line.price_unit = 10
        self.acct_line.refresh()
        self.assertEqual(self.acct_line.price_unit, 10)

    def test_contract(self):
        self.assertAlmostEqual(self.acct_line.price_subtotal, 50.0)
        res = self.acct_line._onchange_product_id()
        self.assertIn('uom_id', res['domain'])
        self.acct_line.price_unit = 100.0
        with self.assertRaises(ValidationError):
            self.contract.partner_id = False
        self.contract.partner_id = self.partner.id
        self.contract.recurring_create_invoice()
        self.invoice_monthly = self.env['account.invoice'].search(
            [('contract_id', '=', self.contract.id)])
        self.assertTrue(self.invoice_monthly)
        self.assertEqual(self.contract.recurring_next_date, '2016-03-29')
        self.inv_line = self.invoice_monthly.invoice_line_ids[0]
        self.assertTrue(self.inv_line.invoice_line_tax_ids)
        self.assertAlmostEqual(self.inv_line.price_subtotal, 50.0)
        self.assertEqual(self.contract.partner_id.user_id,
                         self.invoice_monthly.user_id)

)