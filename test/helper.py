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


import os
import tempfile
import json
import copy
import subprocess
import shutil
import re
import base64
from hashlib import md5
import socket

import sqlite3

from offlineimap.CustomConfig import CustomConfigParser
from offlineimap import imaputil

_base_conf = r'''
[general]
accounts = Test

[Account Test]
localrepository = TestLocal
remoterepository = TestRemote

[Repository TestLocal]
type = Maildir
# localfolders should be set for each case using this conf

[Repository TestRemote]
type = IMAP
remoteuser = test
remotepass = password
'''

_sample_imap_content = {
    'INBOX': { 'uid_validity': 0, 'uid_next': 100, 'messages': [
            { 'uid': 5, 'flags': ['\\Seen'], 'date': '21-Mar-2024', 'headers': ['From: <source@origin.com>',
                    'To: <recipient@destination.com>',
                    'Subject: Just a simple mail', 'Message-Id: a@origin.com'],
                'body': ["Just a simple test mail."]
            },
            { 'uid': 3, 'flags': [], 'date': ' 1-Feb-2024', 'headers': ['From: <source@origin.com>',
                    'To: <recipient@destination.com>',
                    'Subject: With attachement', 'Message-Id: b@origin.com', 'MIME-Version: 1.0',
                    'Content-Type: multipart/mixed; boundary="_-=_separator"'],
                'body': [ "This is MIME multipart message.",
                        "--_-=_separator", 'Content-Type: text/plain; charset="UTF-8"',
                        'Content-Transfer-Encoding: 8bit',
                        '',
                        'Please find attachment.',
                        '--_-=_separator', 'Content-Type: application/data',
                        'Content-Transfer-Encoding: base64', '',
                        20 * 'SnVzdCByYW5kb20ganVuay4gSnVzdCByYW5kb20ganVuay4gSnVzdCByYW5kb20ganVuay4gSnVz\n',
                        '',
                        '--_-=_separator--', '']
            },
            { 'uid': 4, 'flags': [], 'date': '22-Jun-2025', 'headers': ['To: <test@example.com>', 'Subject: us-ascii announced ill-formed email',
                        'From: user@example.com', 'Content-Type: text/plain; charset=us-ascii',
                        'Content-Transfer-Encoding: 8bit', 'Message-Id: <20160614102505.9OFQ19L1C>' ],
                'body_base64': 'VGhpcyBzGRwAAADAdHJpbmcgY29udGFpbnMgbgAAANBvbi1hc2NpaSDvv70K'
            },
        ]
    },
    
    'Internationalised & specials éàè': {'uid_validity': 0, 'uid_next': 50, 'messages': [
        { 'uid': 25, 'flags': [], 'date': '28-Oct-2024', 'headers': ['From: <source@origin.com>',
                'To: <recipient@destination.com>',
                'Subject: Nothing', 'Message-Id: c@origin.com'],
            'body': ['Just a sample mail',]
        }]
    }
}

_sample_maildir_metadata = {
    'Account-Test': { 'type': 'sqldump', 'content': {
            'INBOX': set( [ (5, 'S', 0, ''), (3, '', 0, ''), (4, '', 0, '') ] ),
            'Internationalised &- specials &AOkA4ADo-': set( [ (25, '', 0, '') ] ) } },
    'Repository-TestLocal': { 'type': 'uidvalidity', 'content': { 'INBOX': 42,
                'Internationalised &- specials &AOkA4ADo-': 42 } },
    'Repository-TestRemote': { 'type': 'uidvalidity', 'content': {'INBOX': 0,
                'Internationalised &- specials &AOkA4ADo-': 0} },
}

_CRLF = "\r\n"

#<%d_%d.%d.%s>,U=<%d>,FMD5=<%s>:2,<FLAGS>
_email_filename_re = re.compile(r'^[0-9]+_[0-9]+\.[0-9]+\.[^,]+,U=(?P<uid>[0-9]+),FMD5=(?P<fmd5>[0-9a-fA-F]+):2,(?P<flags>.*)$')

def get_sample_imap_data(data=_sample_imap_content):
    res = dict()
    for mbox_name, mbox in data.items():
        res[mbox_name] = { 'uid_validity': mbox['uid_validity'],
                        'uid_next': mbox['uid_next'] }
        res[mbox_name]['messages'] = list()
        for msg in mbox['messages']:
            new_msg = {
                'uid': msg['uid'], 'flags': msg['flags'], 'date': msg['date'],
            }
            if 'body' in msg:
                new_msg['content'] = _CRLF.join(msg['headers']) + 2*_CRLF + _CRLF.join(msg['body'])
            elif 'body_base64' in msg:
                crlf_bytes = _CRLF.encode('ascii')
                as_bytes = crlf_bytes.join([x.encode('utf8') for x in msg['headers']])
                as_bytes += 2*crlf_bytes
                as_bytes += base64.b64decode(msg['body_base64'])
                new_msg['content_base64'] = base64.b64encode(as_bytes).decode('ascii')
            else:
                raise ValueErrror("Message with no body")
            res[mbox_name]['messages'].append(new_msg)
    return res

def get_sample_maildir_metadata():
    return copy.deepcopy(_sample_maildir_metadata)

def imap_data_to_maildir(imap_data):
    res = dict()
    for mbox_name, imap_box in imap_data.items():
        md_mbox_name = mbox_name.encode('imap4-utf-7').decode('ascii')
        res[md_mbox_name] = dict()
        for msg in imap_box['messages']:
            new_msg = { 'flags': imaputil.flagsimap2maildir("(%s)" % " ".join(msg['flags'])) }
            if 'content' in msg:
                new_msg['content'] = msg['content'].replace('\r\n', os.linesep)
            elif 'content_base64' in msg:
                as_bytes = base64.b64decode(msg['content_base64']).replace(b'\r\n', os.linesep.encode('ascii'))
                new_msg['content_base64'] = base64.b64encode(as_bytes).decode('ascii')
            else:
                raise ValueError("Message with no content")
            res[md_mbox_name][msg['uid']] = new_msg
    return res

def _find_first_address_family():
    for entry in socket.getaddrinfo('localhost', None, 0):
        if entry[0] in (socket.AF_INET, socket.AF_INET6):
            return entry[0]

class IMTestHelper(object):
    def __init__(self):
        self.__config = None
        self.__tmpdir = None
        self.__initial_imap_mailbox = None
    
    def load_default_conf(self):
        self.__config = CustomConfigParser()
        self.__config.read_string(_base_conf)

    def update_conf(self, update_elts):
        for section in update_elts.keys():
            if section not in self.__config.sections():
                self.__config.add_section(section)
            for name, val in update_elts[section].items():
                self.__config.set(section, name, val)

    def get_tmp_filename(self, *rel_name):
        self.__ensure_tmp_dirtree()
        return os.path.join(self.__tmpdir, *rel_name)

    def set_initial_imap_mailbox(self, initial_mbox):
        self.__initial_imap_mailbox = copy.deepcopy(initial_mbox)

    def __ensure_tmp_dirtree(self):
        if self.__tmpdir is None:
           self.__tmpdir = tempfile.mkdtemp(prefix='imapmirror_test_')
        maildir = os.path.join(self.__tmpdir, 'maildir')
        if not os.path.exists(maildir):
            os.mkdir(maildir)
        self.update_conf({'Repository TestLocal': { 'localfolders': maildir }})
        metadata_dir = os.path.join(self.__tmpdir, 'metadata')
        if not os.path.exists(metadata_dir):
            os.mkdir(metadata_dir)
        self.update_conf({'general': { 'metadata': metadata_dir }})
        imapside_dir = os.path.join(self.__tmpdir, 'imap_side')
        if not os.path.exists(imapside_dir):
            os.mkdir(imapside_dir)

    def __prepare_to_run(self):
        src_dir = os.path.join(os.path.dirname(__file__), '../')
        self.__ensure_tmp_dirtree()
        imap_initial_mboxes_fn = os.path.join(self.__tmpdir, 'imap_side', 'initial_mboxes.json')
        with open(imap_initial_mboxes_fn, "w") as f:
            json.dump(self.__initial_imap_mailbox, f)
        return {
            'src_dir': src_dir,
            'script_name': os.path.join(src_dir, 'offlineimap.py'),
            'server_script_name': os.path.join(src_dir, 'test', 'test_imap_server.py'),
            'imap_initial_mboxes_fn': imap_initial_mboxes_fn,
            'imap_final_mbox_fn': os.path.join(self.__tmpdir, 'imap_side', 'final_mbox.json'),
            'imap_wire_tap_fn': os.path.join(self.__tmpdir, 'imap_side', 'wire_tap.dump'),
            'conf_fn': os.path.join(self.__tmpdir, 'imapmirror.conf'),
        }

    def run_offlineimap(self, str_encoding):
        run_info = self.__prepare_to_run()
        if "'" in run_info['src_dir']:
            raise ValueError("Checkout directory name must not contain \"'\"")
        self.update_conf({'Repository TestRemote': { 'transporttunnel':
            "python3 '{server_script_name}' --initial_mboxes_content '{initial_mailbox_content_fn}' "
            "--wire_tap_filename '{wire_tap_fn}' --encode_str_as {str_encoding} "
            "--dump_mbox_filename '{dump_mbox}'".format(
                server_script_name = run_info['server_script_name'],
                initial_mailbox_content_fn = run_info['imap_initial_mboxes_fn'],
                wire_tap_fn = run_info['imap_wire_tap_fn'],
                str_encoding = str_encoding,
                dump_mbox = run_info['imap_final_mbox_fn']) } })
        with open(run_info['conf_fn'], "w") as f:
            self.__config.write(f)
        subprocess.run([run_info['script_name'], '-1', '-c', run_info['conf_fn']]).check_returncode()

    def run_tcp_offlineimap(self, str_encoding):
        run_info = self.__prepare_to_run()
        sock_family = _find_first_address_family()
        bhost = { socket.AF_INET: '127.0.0.1', socket.AF_INET6: '::1' }[sock_family]
        bport = os.environ.get('IMAPMIRROR_TCP_PORT', '0')
        server_process = subprocess.Popen(['python3', run_info['server_script_name'],
                '--initial_mboxes_content', run_info['imap_initial_mboxes_fn'],
                '--wire_tap_filename', run_info['imap_wire_tap_fn'],
                '--encode_str_as', str_encoding,
                '--dump_mbox_filename', run_info['imap_final_mbox_fn'],
                '--bind_host', bhost, '--bind_port', bport ],
                stdout=subprocess.PIPE, encoding='utf8')
        bport = server_process.stdout.readline().strip()
        self.update_conf({'Repository TestRemote': { 'remotehost': bhost, 'remoteport': bport } })
        with open(run_info['conf_fn'], "w") as f:
            self.__config.write(f)
        client_process = subprocess.Popen([run_info['script_name'], '-1', '-c', run_info['conf_fn']])
        return (server_process, client_process)

    def get_maildir(self, dirname='maildir'):
        res = dict()
        maildir_path = os.path.join(self.__tmpdir, dirname)
        for box in os.listdir(maildir_path):
            box_path = os.path.join(maildir_path, box)
            computed_md5 = md5(box.encode('utf-8')).hexdigest().lower()
            res[box] = dict()
            for subp in ("cur", "new"):
                subpath = os.path.join(box_path, subp)
                for email_fname in os.listdir(subpath):
                    email_path = os.path.join(subpath, email_fname)
                    m =_email_filename_re.match(email_fname)
                    assert m is not None
                    got_md5 = m.group('fmd5').lower()
                    if computed_md5 != got_md5:
                        raise ValueError("Unexpected md5 for box %s (%s)" % (box, got_md5))
                    new_msg = { 'flags':set(m.group('flags')) }
                    try:
                        with open(email_path, "r") as f:
                            new_msg['content'] = f.read()
                    except UnicodeDecodeError:
                        with open(email_path, "rb") as f:
                            new_msg['content_base64'] = base64.b64encode(f.read()).decode('ascii')
                    res[box][int(m.group('uid'))] = new_msg
        return res

    def get_metadata(self):
        def dump_sql_data(in_dir):
            res = dict()
            for db in os.listdir(in_dir):
                db_path = os.path.join(in_dir, db)
                res[db] = set()
                c = sqlite3.connect(db_path)
                for row in c.execute("select id, flags, mtime, labels from status"):
                    res[db].add( (row[0], row[1], row[2], row[3]) )
            return res

        res = dict()
        md_path = os.path.join(self.__tmpdir, 'metadata')
        for mdata_dir in os.listdir(md_path):
            mdata_dir_path = os.path.join(md_path, mdata_dir)
            for subdir in os.listdir(mdata_dir_path):
                subdir_path = os.path.join(mdata_dir_path, subdir)
                if subdir == 'LocalStatus-sqlite':
                    res[mdata_dir] = { 'type': 'sqldump', 'content': dump_sql_data(subdir_path)}
                elif subdir == 'FolderValidity':
                    res[mdata_dir] = { 'type': 'uidvalidity', 'content': dict() }
                    for folder in os.listdir(subdir_path):
                        folder_path = os.path.join(subdir_path, folder)
                        with open(folder_path, "r") as f:
                            res[mdata_dir]['content'][folder] = int(f.read().strip())
        return res

    def cleanup(self):
        if self.__tmpdir is not None:
            shutil.rmtree(self.__tmpdir)
            self.__tmpdir = None

