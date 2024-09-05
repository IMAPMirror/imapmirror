# Copyright (C) 2024 Etienne Buira
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301 USA


import unittest
from test import helper

class OfflineImapCompat(unittest.TestCase):
    def test_basic_imap_to_maildir_sync(self):
        imth = helper.IMTestHelper()
        imth.load_default_conf()
        imth.set_initial_imap_mailbox(helper.get_sample_imap_data())
        imth.run_offlineimap('utf7m')
        self.assertEqual(helper.imap_data_to_maildir(helper.get_sample_imap_data()), imth.get_maildir())
        self.assertEqual(helper.get_sample_maildir_metadata(), imth.get_metadata())
        imth.run_offlineimap('utf7m')
        self.assertEqual(helper.imap_data_to_maildir(helper.get_sample_imap_data()), imth.get_maildir())
        self.assertEqual(helper.get_sample_maildir_metadata(), imth.get_metadata())
        imth.cleanup()

