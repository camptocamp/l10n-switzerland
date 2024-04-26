from odoo import api, models


class ReportSwissNoAmountQR(models.AbstractModel):
    _name = "report.l10n_ch_qr_no_amount.qr_no_amount_report_main"
    _inherit = "report.l10n_ch.qr_report_main"
    _description = "QR-No-Amount-bill"

    @api.model
    def _get_report_values(self, docids, data=None):
        return super()._get_report_values(docids, data)
