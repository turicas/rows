# coding: utf-8

# Copyright 2014-2016 Álvaro Justen <https://github.com/turicas/rows/>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

from decimal import Decimal

from ofxtools import OFXTree

from rows.plugins.utils import create_table, get_filename_and_fobj


# TODO: force field types:
#       OrderedDict([
#               ('id', rows.fields.TextField),
#               ('checknum', rows.fields.TextField),
#               ('datetime', rows.fields.DatetimeField),
#               ('name', rows.fields.TextField),
#               ('description', rows.fields.TextField),
#               ('type', rows.fields.TextField),
#               ('amount', rows.fields.DecimalField),
#               ('payee_id', rows.fields.IntegerField),
#       ])
#    trntype = OneOf('CREDIT', 'DEBIT', 'INT', 'DIV', 'FEE', 'SRVCHG',
#                    'DEP', 'ATM', 'POS', 'XFER', 'CHECK', 'PAYMENT',
#                    'CASH', 'DIRECTDEP', 'DIRECTDEBIT', 'REPEATPMT',
#                    'OTHER', required=True)
#    dtposted = DateTime(required=True)
#    trnamt = Decimal(required=True)
#
#    dtuser = DateTime()
#    dtavail = DateTime()
#    correctfitid = Decimal()
#    correctaction = OneOf('REPLACE', 'DELETE')
#    checknum = String(12)
#    refnum = String(32)
#    sic = Integer()
#    payeeid = String(12)
#    name = String(32)
#    memo = String(255)
#    inv401ksource = OneOf(*INV401KSOURCES)
#
#    payee = None
#    bankacctto = None
#    ccacctto = None

def import_from_ofx(filename_or_fobj, index=0, *args, **kwargs):
    '''Import data from OFX file

    `index` is the index of desired statement
    '''

    filename, _ = get_filename_and_fobj(filename_or_fobj, dont_open=True)
    tree = OFXTree()
    tree.parse(filename)
    response = tree.convert()
    statement = response.statements[index]

    meta = {'imported_from': 'ofx',
            'filename': filename,
            'ofx': {'account': {'id': statement.account.acctid,
                                'type': statement.account.accttype, },
                    'currency': statement.currency,
                    'balance': {'value': Decimal(statement.ledgerbal.balamt),
                                'datetime': statement.ledgerbal.dtasof, },
            },
    }

    header = ['id', 'checknum', 'datetime', 'name', 'description', 'type',
              'amount', 'payee_id']
    header_mapping = ['fitid', 'checknum', 'dtposted', 'name', 'memo',
                      'trntype', 'trnamt', 'payeeid']
    table_rows = [[getattr(row, field) for field in header_mapping]
                  for row in statement.transactions]

    # TODO: what if we have more than one statment? add index
    # TODO: what to do with other metadata?
    # TODO: what if the account type is not 'checking'?

    return create_table([header] + table_rows, meta=meta, *args, **kwargs)
