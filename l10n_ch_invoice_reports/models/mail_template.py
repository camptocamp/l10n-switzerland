# Copyright 2021 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import base64

from odoo import _, models


class MailTemplate(models.Model):
    _inherit = "mail.template"

    def generate_email(self, res_ids, fields=None):
        """ Method overridden in order remove QR/ISR payslips and use
            Invoice report with payslip generated by this module
        """
        rslt = super(MailTemplate, self).generate_email(res_ids, fields)

        multi_mode = True
        if isinstance(res_ids, int):
            res_ids = [res_ids]
            multi_mode = False

        res_ids_to_templates = self.get_email_template(res_ids)
        for res_id in res_ids:
            related_model = self.env[self.model_id.model].browse(res_id)

            if related_model._name == "account.move":
                rslt[res_id]["attachments"] = False
                template = res_ids_to_templates[res_id]
                self._render_template(template.report_name, template.model, res_id)
                new_attachments = []
                # We add an optional attachment from mail template (if set)
                if self.report_template:
                    report_name = self.report_template.attachment
                    if (
                        self.report_template.report_name
                        == "l10n_ch_invoice_reports.account_move_payment_report"
                    ):
                        report_name = _(
                            "invoice_%s_with_payslip.pdf"
                        ) % related_model.name.replace("/", "_")
                    report_xml_id = self.report_template.xml_id
                    report_pdf = self.env.ref(report_xml_id).render_qweb_pdf([res_id])[
                        0
                    ]
                    report_pdf = base64.b64encode(report_pdf)
                    new_attachments.append((report_name, report_pdf))

                attachments_list = (
                    multi_mode
                    and rslt[res_id].get("attachments", False)
                    or rslt.get("attachments", False)
                )
                if attachments_list:
                    attachments_list.extend(new_attachments)
                else:
                    rslt[res_id]["attachments"] = new_attachments
        return rslt
