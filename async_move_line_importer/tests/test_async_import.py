# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Nicolas Bessi
#    Copyright 2013 Camptocamp SA
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import base64
import tempfile

from . import odbc_test_common
from openerp import addons
from ..model import async_move_line_importer


class TestMoveLineImporter(odbc_test_common.ODBCBaseTestClass):

    def get_file(self, filename):
        """Retrive file from test data"""
        path = addons.get_module_resource('async_move_line_importer',
                                          'test', 'data', filename)
        with open(path) as test_data:
            with tempfile.TemporaryFile() as out:
                base64.encode(test_data, out)
                out.seek(0)
                return out.read()

    def setUp(self):
        super(TestMoveLineImporter, self).setUp()
        self.importer_model = self.registry('move.line.importer')
        self.move_model = self.registry('account.move')
        async_move_line_importer.USE_THREAD = False

    def tearDown(self):
        super(TestMoveLineImporter, self).tearDown()
        async_move_line_importer.USE_THREAD = True

    def test_01_one_line_direct_import_without_by_pass(self):
        """Test one line import without bypassing orm"""
        cr, uid = self.cr, self.uid
        importer_id = self.importer_model.create(cr, uid,
                                                 {'file': self.get_file('one_move.csv')})
        importer = self.importer_model.browse(cr, uid, importer_id)
        self.asertTrue(importer.company_id, 'Not default company set')
        self.assertFalse(importer.bypass_orm, 'By pass orm must not be active')
        self.assertEqual(importer.state, 'draft')
        importer.import_file()
        importer = self.importer_model.browse(cr, uid, importer_id)
        self.assertEquals(importer.state, 'done',
                          'Exception %s during import' % importer.report)
        created_move_ids = self.move_model.search(cr, uid, [('ref', '=', 'éöüàè_test_1')])
        self.assertTrue(created_move_ids, 'No move imported')
        created_move = self.move_model.browse(cr, uid, created_move_ids[0])
        self.assertTrue(len(created_move.line_id) == 3, 'Wrong number of move line imported')
        debit, credit = 0.0
        for line in created_move.line_id:
            debit += line.debit if line.debit else 0.0
            credit += line.credit if line.credit else 0.0
        self.assertEqual(debit, 1200.00)
        self.assertEqual(credit, 1200.00)
        self.assertEqual(created_move.state, 'draft', 'Wrong move state')
