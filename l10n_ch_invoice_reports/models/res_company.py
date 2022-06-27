from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    print_qr_invoice = fields.Boolean(
        string="Print invoice with QR bill", readonly=False,
    )
    print_isr_invoice = fields.Boolean(
        string="Print invoice with ISR payslip", readonly=False,
    )
