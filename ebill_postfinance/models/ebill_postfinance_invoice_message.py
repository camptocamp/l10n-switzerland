# Copyright 2019 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import os
from datetime import datetime

import pytz
from jinja2 import Environment, FileSystemLoader

from odoo import _, fields, models
from odoo.modules.module import get_module_root

from odoo.addons.base.models.res_bank import sanitize_account_number

MODULE_PATH = get_module_root(os.path.dirname(__file__))
# INVOICE_TEMPLATE_2013 = "invoice-2013A.xml"
INVOICE_TEMPLATE_2003 = "invoice-2003A.jinja"
TEMPLATE_DIR = [MODULE_PATH + "/messages"]

DOCUMENT_TYPE = {"out_invoice": "EFD", "out_refund": "EGS"}


class EbillPostfinanceInvoiceMessage(models.Model):
    _name = "ebill.postfinance.invoice.message"
    _description = "Postfinance message send to service"

    service_id = fields.Many2one(
        comodel_name="ebill.postfinance.service",
        string="Service used",
        required=True,
        ondelete="restrict",
        readonly=True,
    )
    ebill_payment_contract_id = fields.Many2one(comodel_name="ebill.payment.contract")
    invoice_id = fields.Many2one(comodel_name="account.move", ondelete="restrict")
    transaction_id = fields.Char(string="Transaction Id")
    file_type_used = fields.Char()
    submitted_on = fields.Datetime(string="Submitted on")
    attachment_id = fields.Many2one("ir.attachment", "PDF")
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("sent", "Sent"),
            ("error", "Error"),
            ("processing", "Processing"),
            ("reject", "Reject"),
            ("done", "Done"),
        ],
        default="draft",
    )
    server_state = fields.Selection(
        selection=[
            ("invalid", "Invalid"),
            ("processing", "Processing"),
            ("unsigned", "Unsigned"),
            ("open", "Open"),
            ("paid", "Paid"),
            # Not encountered states
            ("rejected", "Rejected"),
            ("incomplete", "Incomplete"),
            ("deleted", "Deleted"),
        ],
    )
    server_reason_code = fields.Integer(string="Error code")
    server_reason_text = fields.Char(string="Error text")

    # Set with invoice_id.number but also with returned data from server ?
    ref = fields.Char("Reference No.", size=35)
    ebill_account_number = fields.Char("Paynet Id", size=20)
    payload = fields.Text("Payload sent")
    response = fields.Text("Response")
    # shipment_id = fields.Char(size=24, help="Shipment Id on Paynet service")
    payment_type = fields.Selection(
        selection=[("qr", "QR"), ("isr", "ISR"), ("esp", "ESP"), ("npy", "NPY")],
        default="qr",
        readonly=True,
    )

    def set_transaction_id(self):
        for record in self:
            record.transaction_id = "_".join(
                [
                    record.invoice_id.name.replace("/", "_"),
                    fields.Datetime.now().strftime("%Y_%m_%d_%H_%_M"),
                    (record.file_type_used or "").lower().replace(".", ""),
                ]
            )

    def update_message_from_server_data(self, data):
        """Update the invoice message with data received from the server.

        Keyword arguments:
        data -- Structure from the api
                Example:
                {
                    'BillerId': '41101000001021209',
                    'TransactionId': 'INV_2022_03_0001_2022_03_26_08_31_xml',
                    'eBillAccountId': '123412341234',
                    'Amount': Decimal('0'),
                    'State': 'Invalid',
                    'PaymentType': None,
                    'ESRReferenceNbr': None,
                    'DeliveryDate': datetime.datetime(2022, 3, 26, 0, 0),
                    'PaymentDueDate': None,
                    'ReasonCode': '16',
                    'ReasonText': 'some good reason'
                }
        """
        self.ensure_one()
        # TODO check transaction id are the same
        self.server_state = data.State.lower()
        self.server_reason_code = data.ReasonCode
        self.server_reason_text = data.ReasonText
        if self.server_state in ["invalid"]:
            self.state = "error"
        elif self.server_state == "processing":
            self.state = "processing"
        elif self.server_state == "paid":
            self.set_as_paid(data)

    def set_as_paid(self, data):
        for record in self:
            if record.state != "done":
                record.state = "done"
                record.invoice_id.message_post(body=_("Invoice paid through eBilling"))

    def send_to_postfinance(self):
        # TODO: Could sent multiple with one call
        for message in self:
            message.file_type_used = message.service_id.file_type_to_use
            message.set_transaction_id()
            message.payload = message._generate_payload()
            try:
                # TODO: Handle file type from service configuation
                data = message.payload.encode("utf-8")
                res = message.service_id.upload_file(
                    message.transaction_id, message.file_type_used, data
                )
                response = res[0]
                if response.ProcessingState == "OK":
                    message.state = "sent"
                    submit_date_utc = response.SubmitDate.astimezone(pytz.utc)
                    message.submitted_on = submit_date_utc.replace(tzinfo=None)
                    message.response = response  # Probably not needed anymore
                else:
                    message.state = "error"
                    message.server_reason_code = "NOK"
                    message.server_reason_text = "Could not be sent to sftp"
            # except zeep.exceptions.Fault as e:
            except Exception:
                # message.response = PayNetDWS.handle_fault(e)
                message.response = "TODO get error message from response if any."
                message.state = "error"

    @staticmethod
    def format_date(date_string=None):
        """Format a date in the Jinja template."""
        if not date_string:
            date_string = datetime.now()
        return date_string.strftime("%Y%m%d")

    def _get_payload_params(self):
        bank_account = ""
        if self.payment_type == "qr":
            bank_account = sanitize_account_number(
                self.invoice_id.partner_bank_id.l10n_ch_qr_iban
                or self.invoice_id.partner_bank_id.acc_number
            )
        else:
            bank_account = self.invoice_id.partner_bank_id.l10n_ch_isr_subscription_chf
            if bank_account:
                account_parts = bank_account.split("-")
                bank_account = (
                    account_parts[0] + account_parts[1].rjust(6, "0") + account_parts[2]
                )
            else:
                bank_account = ""

        params = {
            "client_pid": self.service_id.biller_id,
            "invoice": self.invoice_id,
            "invoice_lines": self.invoice_id.postfinance_invoice_line_ids(),
            "biller": self.invoice_id.company_id,
            "customer": self.invoice_id.partner_id,
            "delivery": self.invoice_id.partner_shipping_id,
            "pdf_data": self.attachment_id.datas.decode("ascii"),
            "bank": self.invoice_id.partner_bank_id,
            "bank_account": bank_account,
            "transaction_id": self.transaction_id,
            "payment_type": self.payment_type,
            "document_type": DOCUMENT_TYPE[self.invoice_id.move_type],
            "format_date": self.format_date,
            "ebill_account_number": self.ebill_account_number,
            "discount_template": "",
            "discount": {},
        }
        amount_by_group = []
        # Get the percentage of the tax from the name of the group
        # Could be improve by searching in the account_tax linked to the group
        for taxgroup in self.invoice_id.amount_by_group:
            rate = taxgroup[0].split()[-1:][0][:-1]
            amount_by_group.append(
                (
                    rate or "0",
                    taxgroup[1],
                    taxgroup[2],
                )
            )
        params["amount_by_group"] = amount_by_group
        # Get the invoice due date
        date_due = None
        if self.invoice_id.invoice_payment_term_id:
            terms = self.invoice_id.invoice_payment_term_id.compute(
                self.invoice_id.amount_total
            )
            if terms:
                # Returns all payment and their date like [('2020-12-07', 430.37), ...]
                # Get the last payment date in the format "202021207"
                date_due = terms[-1][0].replace("-", "")
        if not date_due:
            date_due = self.format_date(
                self.invoice_id.invoice_date_due or self.invoice_id.invoice_date
            )
        params["date_due"] = date_due
        return params

    def _get_jinja_env(self, template_dir):
        jinja_env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=True,
        )
        # Force the truncate filter to be exact
        jinja_env.policies["truncate.leeway"] = 0
        return jinja_env

    def _get_template(self, jinja_env):
        return jinja_env.get_template(INVOICE_TEMPLATE_2003)

    def _generate_payload(self):
        self.ensure_one()
        assert self.state in ("draft", "error")
        params = self._get_payload_params()
        jinja_env = self._get_jinja_env(TEMPLATE_DIR)
        jinja_template = self._get_template(jinja_env)
        return jinja_template.render(params)

    def update_invoice_status(self):
        """Update the export status in the chatter."""
        for message in self:
            if message.state == "done":
                message.invoice_id.log_invoice_accepted_by_system()
            elif message.state in ["reject", "error"]:
                message.invoice_id.log_invoice_refused_by_system()
