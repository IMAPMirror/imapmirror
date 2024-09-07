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
import re
import json
import subprocess
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

    def __apply_mbnames_confbase(self, imth):
        imth.update_conf({'mbnames': {
            'enabled': 'yes',
            'filename': imth.get_tmp_filename('mboxes_names'),
            'header': '"mailboxes "',
            'peritem': r'"+%(accountname)s/%(foldername)s"',
            'sep': '" "',
            'footer': r'"\n"',
            'incremental': 'no',
        }})


    def test_mailboxes_names(self):
        imth = helper.IMTestHelper()
        imth.load_default_conf()
        self.__apply_mbnames_confbase(imth)
        imth.set_initial_imap_mailbox(helper.get_sample_imap_data())
        imth.run_offlineimap('utf7m')
        with open(imth.get_tmp_filename('mboxes_names'), "r") as f:
            mboxes_file = f.read()
        m = re.fullmatch(r'mailboxes (?P<mailboxes>("\+[^"]+" ?)+)\n', mboxes_file, re.MULTILINE)
        self.assertIsNotNone(m)
        expected = { '"+Test/INBOX"', '"+Test/Internationalised &- specials &AOkA4ADo-"' }
        for m in re.findall(r'("\+[^"]+") ?', m.group('mailboxes')):
            self.assertIn(m, expected)
            expected.discard(m)
        self.assertEqual(len(expected), 0)
        with open(imth.get_tmp_filename('metadata', 'mbnames', 'Test.json'), "r") as f:
            test_mbnames = json.load(f)
        maildir = imth.get_tmp_filename('maildir')
        expected = [
            { 'accountname': 'Test', 'foldername': 'INBOX', 'localfolders': maildir },
            { 'accountname': 'Test', 'foldername': 'Internationalised &- specials &AOkA4ADo-', 'localfolders': maildir },
        ]
        for mbname in test_mbnames:
            self.assertIn(mbname, expected)
            expected.remove(mbname)
        self.assertEqual(len(expected), 0)
        imth.cleanup()

    def test_mbnames_folderfilter(self):
        imth = helper.IMTestHelper()
        imth.load_default_conf()
        self.__apply_mbnames_confbase(imth)
        imth.update_conf({'mbnames': {
            'folderfilter': 'lambda: False',
        }})
        imth.set_initial_imap_mailbox(helper.get_sample_imap_data())
        with self.assertRaises(subprocess.CalledProcessError):
            imth.run_offlineimap('utf7m')
        imth.cleanup()

