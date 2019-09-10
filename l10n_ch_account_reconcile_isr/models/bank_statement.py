# -*- coding: utf-8 -*-
# Copyright 2019 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import api, models


class AccountBankStatement(models.Model):

    _inherit = "account.bank.statement"

    @api.multi
    def reconciliation_widget_preprocess(self):
        """ ISR reconciliation relies only on transaction_ref
        so matches of partner_id also should respect it

        Method is copy of parent the _prepare_query was only added
        """
        statements = self
        sql_query = """SELECT stl.id
                        FROM account_bank_statement_line stl
                        WHERE account_id IS NULL AND not exists (
                            select 1 from account_move m
                            where m.statement_line_id = stl.id
                            )
                            AND company_id = %s
                """
        params = (self.env.user.company_id.id,)
        if statements:
            sql_query += ' AND stl.statement_id IN %s'
            params += (tuple(statements.ids),)
        sql_query += ' ORDER BY stl.id'
        self.env.cr.execute(sql_query, params)
        st_lines_left = self.env[
            'account.bank.statement.line'
        ].browse([line.get('id') for line in self.env.cr.dictfetchall()])

        # try to assign partner to bank_statement_line
        stl_to_assign_partner = [
            stl.id for stl in st_lines_left if not stl.partner_id
        ]
        refs = list(set([
            st.name for st in st_lines_left if not st.partner_id
        ]))
        acc_cr = st_lines_left[0].journal_id.default_credit_account_id
        acc_dt = st_lines_left[0].journal_id.default_debit_account_id
        if st_lines_left and stl_to_assign_partner and refs\
           and acc_cr and acc_dt:

            sql_query = self._prepare_query()
            params = (
                self.env.user.company_id.id,
                (acc_cr.id, acc_dt.id),
                tuple(refs)
            )

            if statements:
                sql_query += 'AND stl.id IN %s'
                params += (tuple(stl_to_assign_partner),)
            self.env.cr.execute(sql_query, params)
            results = self.env.cr.dictfetchall()
            st_line = self.env['account.bank.statement.line']
            for line in results:
                st_line.browse(
                    line.get('id')
                ).write({'partner_id': line.get('partner_id')})

        return {
            'st_lines_ids': st_lines_left.ids,
            'notifications': [],
            'statement_name':
                len(statements) == 1 and statements[0].name or False,
            'num_already_reconciled_lines': 0,
        }

    def _prepare_query(self):
        """Replace ref on transaction_ref to match aml"""
        sql_query = """SELECT aml.partner_id, aml.transaction_ref, stl.id
                FROM account_move_line aml
                    JOIN account_account acc ON acc.id = aml.account_id
                    JOIN account_bank_statement_line stl
                    ON aml.transaction_ref = stl.name
                WHERE (aml.company_id = %s
                    AND aml.partner_id IS NOT NULL)
                    AND (
                        (aml.statement_id IS NULL AND aml.account_id IN %s)
                        OR
                        (acc.internal_type IN ('payable', 'receivable')
                         AND aml.reconciled = false)
                        )
                    AND aml.transaction_ref IN %s
                    """
        return sql_query