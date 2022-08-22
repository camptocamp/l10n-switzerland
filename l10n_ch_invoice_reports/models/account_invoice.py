# Copyright 2022 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)


from odoo import api, models


class AccountMove(models.Model):
    _inherit = "account.move"

    # override to add context key dependency and handle it properly inside method
    @api.depends(
        "type",
        "name",
        "currency_id.name",
        "invoice_partner_bank_id.l10n_ch_isr_subscription_eur",
        "invoice_partner_bank_id.l10n_ch_isr_subscription_chf",
    )
    @api.depends_context("_mail_template_no_attachments")
    def _compute_l10n_ch_isr_valid(self):
        """Returns True if all the data required to generate the ISR are present"""
        for record in self:
            if self.env.context.get("_mail_template_no_attachments", False):
                record.l10n_ch_isr_valid = False
                continue
            record.l10n_ch_isr_valid = (
                record.type == "out_invoice"
                and record.name
                and record.l10n_ch_isr_subscription
                and record.l10n_ch_currency_name in ["EUR", "CHF"]
            )

    def can_generate_qr_bill(self):
        """ Returns True iff the invoice can be used to generate a QR-bill.
        """
        self.ensure_one()
        if self.env.context.get("_mail_template_no_attachments", False):
            return False
        return not self.env.ref(
            "l10n_ch.l10n_ch_swissqr_template"
        ).inherit_id and self.invoice_partner_bank_id.validate_swiss_code_arguments(
            self.invoice_partner_bank_id.currency_id,
            self.partner_id,
            self.invoice_payment_ref,
        )

    def action_invoice_sent(self):
        # override to update context with new key
        action = super().action_invoice_sent()
        ctx = action["context"].copy()
        ctx.update({"_mail_template_no_attachments": True})
        action["context"] = ctx
        return action
