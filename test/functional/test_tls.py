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
import ssl
from dataclasses import dataclass
import tempfile
import subprocess
import os
import shutil
from test import helper

@dataclass
class TLSData:
    key: str
    certificate: str

class TLSTests(unittest.TestCase):
    def __get_usual_helper(self):
        imth = helper.IMTestHelper()
        imth.load_default_conf()
        imth.set_initial_imap_mailbox(helper.get_sample_imap_data())
        return imth

    def __postrun_check(self, imth):
        self.assertEqual(helper.imap_data_to_maildir(helper.get_sample_imap_data()), imth.get_maildir())

    def __build_selfsigned_certificate(self):
        kdir = tempfile.mkdtemp()
        cert_fn = os.path.join(kdir, 'cert.pem')
        key_fn = os.path.join(kdir, 'priv.key')
        subprocess.run(['openssl', 'req', '-new', '-x509', '-days', '10', '-noenc',
                        '-out', cert_fn, '-keyout', key_fn,
                        '-subj', '/C=NO/ST=nowhere/O=imapmirror/CN=localhost',
                        '-addext', 'subjectAltName=IP:127.0.0.1,IP:::1']).check_returncode()
        with open(cert_fn, "r") as cert, open(key_fn, "r") as key:
            r = TLSData(key=key.read(), certificate=cert.read())
        shutil.rmtree(kdir)
        return r

    def test_plain(self):
        imth = self.__get_usual_helper()
        imth.update_conf({'Repository TestRemote': {'ssl': 'no', 'starttls': 'no'}})
        (server_process, client_process) = imth.run_tcp_offlineimap('utf7m')
        client_process.wait()
        self.assertEqual(client_process.returncode, 0)
        server_process.stdout.close()
        server_process.wait()
        self.__postrun_check(imth)

    def test_ssl_normal(self):
        imth = self.__get_usual_helper()
        tlsdata = self.__build_selfsigned_certificate()
        imth.set_server_tls(tlsdata)
        client_cafile = imth.get_tmp_filename('client_ca')
        with open(client_cafile, "w") as f:
            f.write(tlsdata.certificate)
        imth.update_conf({'Repository TestRemote': { 'sslcacertfile': client_cafile } })
        (server_process, client_process) = imth.run_tcp_offlineimap('utf7m')
        client_process.wait()
        self.assertEqual(client_process.returncode, 0)
        server_process.stdout.close()
        server_process.wait()
        self.assertEqual(server_process.returncode, 0)
        self.__postrun_check(imth)

