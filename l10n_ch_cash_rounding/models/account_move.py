# Copyright 2023 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    invoice_cash_rounding_id = fields.Many2one(
        readonly=False, compute="_compute_invoice_cash_rounding"
    )

    @api.depends("state", "type", "currency_id")
    def _compute_invoice_cash_rounding(self):
        for move in self:
            if move.state != "posted" and move.type in ["out_invoice", "out_refund"]:
                move.invoice_cash_rounding_id = False
                if move.currency_id == self.env.ef("base.CHF").id:
                    move.invoice_cash_rounding_id = self.env.ref(
                        "l10n_ch_cash_rounding.swiss_cash_rounding"
                    ).id
