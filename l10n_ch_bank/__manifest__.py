# Copyright 2011 Camptocamp SA
# Copyright 2014 Olivier Jossen brain-tec AG
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Switzerland - Bank list",
    "version": "12.0.1.0.0",
    "author": "Camptocamp, brain-tec AG, Odoo Community Association (OCA)",
    "category": "Localisation",
    "website": "https://github.com/OCA/l10n-switzerland",
    "license": "AGPL-3",
    "summary": "Banks names, addresses and BIC codes",
    "depends": ["l10n_ch_base_bank"],
    # We use csv file as xml is too slow
    # unfortunately it doesn't work with noupdate thus we use a post_init hook
    # 'init': ['data/res.bank.csv'],
    "post_init_hook": "post_init",
    "data": [],
}
