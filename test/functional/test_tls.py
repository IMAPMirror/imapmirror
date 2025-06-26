# Copyright (C) 2025 Etienne Buira
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

class TLSTests(unittest.TestCase):
    def __get_usual_helper(self):
        imth = helper.IMTestHelper()
        imth.load_default_conf()
        imth.set_initial_imap_mailbox(helper.get_sample_imap_data())
        return imth

    def __postrun_check(self, imth):
        self.assertEqual(helper.imap_data_to_maildir(helper.get_sample_imap_data()), imth.get_maildir())

    def test_plain(self):
        imth = self.__get_usual_helper()
        imth.update_conf({'Repository TestRemote': {'ssl': 'no', 'starttls': 'no'}})
        (server_process, client_process) = imth.run_tcp_offlineimap('utf7m')
        client_process.wait()
        self.assertEqual(client_process.returncode, 0)
        server_process.stdout.close()
        server_process.wait()
        self.__postrun_check(imth)


