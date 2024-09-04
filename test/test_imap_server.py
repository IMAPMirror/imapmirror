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


import sys
import os
import argparse
import json
import re

# Might be started standalone
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from offlineimap import imaputil

"""Limited and partially conformant IMAP4rev1 server (RFC3501) aimed at testing IMAPMirror"""

_CRLF = b'\r\n'

class ConnectionClosedException(Exception):
    pass

def dump_stderr(subject):
    sys.stderr.buffer.raw.write(subject.encode('ascii'))

def encode_literal(subject):
    if not isinstance(subject, bytes):
        subject = subject.encode('utf-8')
    return ("{%d}" % len(subject)).encode('ascii') + _CRLF + subject

class TestImapServer(object):
    def __encode(self, item):
        if item is None:
            return b'NIL'
        elif isinstance(item, list):
            res = bytearray()
            res += b'('
            for cur_item in item:
                res += self.__encode(cur_item)
                res += b' '
            if len(item) > 0:
                res[-1] = ord(')')
            else:
                res += b')'
            return res
        elif isinstance(item, str):
            if self.__encode_str_as == 'literal':
                real_str = item.encode('utf8')
                return encode_literal(real_str)
            elif self.__encode_str_as == 'utf7m':
                if len(item) == 0:
                    return b'""'
                return imaputil.foldername_to_imapname(item.encode('imap4-utf-7').decode('ascii')).encode('ascii')
            elif self.__encode_str_as == 'utf8':
                if len(item) == 0:
                    return b'""'
                return imaputil.foldername_to_imapname(item).encode('utf8')
            else:
                raise ValueError("Don't know how to encode string as %s" % self.__encode_str_as)
        elif isinstance(item, bytes):
            return item
        elif isinstance(item, int):
            return ("%d" % item).encode('ascii')
        else:
            raise ValueError("Cannot encode: %s" % item)

    def __send_response(self, tag, oknobad, items, tail_bytes=None):
        data = bytearray()
        data += tag.encode('ascii')
        if len(oknobad) > 0:
            data += b' ' + oknobad 
        for cur_i in items:
            data += b' ' + self.__encode(cur_i)
        if tail_bytes:
            data += b' ' + tail_bytes
        data += _CRLF
        self.__iobuf.write_data(data)

    def __assertEqual(self, a, b):
        if a == b:
            return
        dump_stderr("Unexpected inequality: \"%s\" vs \"%s\", buffer=\"%s\"\n" % (a, b, self.__iobuf.get_buffer()))
        assert False

    def __handle_cmd_capability(self, tag, uid_cmd):
        assert not uid_cmd
        self.__iobuf.eat_chars(_CRLF)
        self.__send_response('*', b'', [], b'CAPABILITY IMAP4rev1 AUTH=LOGIN')
        self.__send_response(tag, b'OK', [], b'CAPABILITY completed')

    def __handle_cmd_noop(self, tag, uid_cmd):
        assert not uid_cmd
        self.__iobuf.eat_chars(_CRLF)
        self.__send_response(tag, b'OK', [], b'NOOP completed')

    def __handle_cmd_login(self, tag, uid_cmd):
        assert not self.__is_authenticated()
        assert not uid_cmd
        self.__iobuf.eat_chars(b' ')
        self.__assertEqual(self.__iobuf.read_string(False), 'test')
        self.__iobuf.eat_chars(b' ')
        self.__assertEqual(self.__iobuf.read_string(False), 'password')
        self.__iobuf.eat_chars(_CRLF)
        self.__send_response(tag, b'OK', [], b'LOGIN complete')
        self.__login  = 'test'

    def __handle_cmd_list(self, tag, uid_cmd):
        assert self.__is_authenticated()
        assert not uid_cmd
        self.__iobuf.eat_chars(b' ')
        arg_reference = self.__iobuf.read_string(False)
        self.__iobuf.eat_chars(b' ')
        arg_mbox = self.__iobuf.read_string(False)
        self.__iobuf.eat_chars(_CRLF)
        mpattern = re.escape(arg_reference)
        for c in arg_mbox:
            if c == '*':
                mpattern += '.*'
            elif c == '.':
                mpattern += '[^.]*'
            else:
                mpattern += re.escape(c)
        pattern_re = re.compile(mpattern)
        mboxes = []
        for mbox_candidate in self.__mailboxes.keys():
            if pattern_re.fullmatch(mbox_candidate) is not None:
                mboxes.append(mbox_candidate)
        if len(mboxes) == 0:
            self.__send_response('*', b'', [ 'LIST', [ '\\Noselect' ], ".", "" ], b'')
        else:
            for mbox in mboxes:
                self.__send_response('*', b'', [ 'LIST', [], ".", mbox], b'')
        self.__send_response(tag, b'OK', [], b'LIST completed')

    def __handle_cmd_select_examine(self, tag, uid_cmd, rw_mode):
        assert self.__is_authenticated()
        assert not uid_cmd
        self.__iobuf.eat_chars(b' ')
        mbox_name = self.__iobuf.read_string(False)
        self.__iobuf.eat_chars(_CRLF)
        mbox = self.__mailboxes[mbox_name]
        self.__selected_mailbox = mbox_name
        self.__send_response('*', b'', [ b'FLAGS', [b'\\Answered', b'\\Flagged', b'\\Deleted',
                                    b'\\Seen', b'\\Draft']], b'')
        self.__send_response('*', b'', [ ('%d EXISTS' % len(mbox['messages'])).encode('ascii') ], b'')
        self.__send_response('*', b'', [ b'0 RECENT' ], b'')
        unseen_count = 0
        for msg in mbox['messages']:
            if '\\Seen' not in msg['flags']:
                unseen_count += 1
        self.__send_response('*', b'OK', [ ('[UNSEEN %d]' % unseen_count).encode('ascii') ], b'')
        self.__send_response('*', b'OK', [ ('[UIDNEXT %d]' % mbox['uid_next']).encode('ascii') ], b'')
        self.__send_response('*', b'OK', [ ('[UIDVALIDITY %d]' % mbox['uid_validity']).encode('ascii') ], b'')
        self.__send_response(tag, b'OK', [ rw_mode ], b'command complete')

    def __handle_cmd_select(self, tag, uid_cmd):
        self.__handle_cmd_select_examine(tag, uid_cmd, b'[READ-WRITE]')
        self.__writable = True

    def __handle_cmd_examine(self, tag, uid_cmd):
        self.__handle_cmd_select_examine(tag, uid_cmd, b'[READ-ONLY]')
        self.__writable = False

    def __handle_cmd_logout(self, tag, uid_cmd):
        assert not uid_cmd
        self.__iobuf.eat_chars(_CRLF)
        self.__send_response('*', b'BYE', [], b'')
        self.__send_response(tag, b'OK', [], b'logout completed')
        return True

    __msg_set_part_re = re.compile(r'(?P<start>[0-9]+)(:(?P<end>([0-9]+)|\*))?(?P<coma>,?)')
    def __select_messages(self, msg_list, uid_cmd):
        def add_to_set(msg_idxs, mbox, imap_idx, uid_cmd):
            if uid_cmd:
                for idx in range(len(mbox['messages'])):
                    if mbox['messages'][idx]['uid'] == imap_idx:
                        msg_idxs.add(idx)
                        return
            else:
                if imap_idx <= len(mbox['messages']):
                    msg_idxs.add(imap_idx-1)

        msg_idxs = set()
        mbox = self.__mailboxes[self.__selected_mailbox]
        for match in self.__class__.__msg_set_part_re.finditer(msg_list):
            if match.group('end') is None:
                imap_idx = int(match.group('start'))
                add_to_set(msg_idxs, mbox, imap_idx, uid_cmd)
            else:
                imap_idx_begin = int(match.group('start'))
                if match.group('end') == '*':
                    imap_idx_end = len(mbox['messages'])
                else:
                    imap_idx_end = int(match.group('end'))
                for imap_idx in range(imap_idx_begin, imap_idx_end+1):
                    add_to_set(msg_idxs, mbox, imap_idx, uid_cmd)
        return msg_idxs
            

    def __handle_cmd_fetch(self, tag, uid_cmd):
        assert self.__is_selected()
        self.__iobuf.eat_chars(b' ')
        msg_list = self.__iobuf.read_string(False)
        self.__iobuf.eat_chars(b' ')
        dat_items = self.__iobuf.read_list_or_string()
        self.__iobuf.eat_chars(_CRLF)
        if not isinstance(dat_items, list):
            dat_items = [dat_items]
        msg_idxs = self.__select_messages(msg_list, uid_cmd)
        mbox = self.__mailboxes[self.__selected_mailbox]
        for msg_idx in msg_idxs:
            cur_item = list()
            msg = mbox['messages'][msg_idx]
            uid_set = False
            if uid_cmd:
                cur_item.append(b'UID')
                cur_item.append(msg['uid'])
                uid_set = True
            for data_item in dat_items:
                if data_item == 'FLAGS':
                    cur_item.append(b'FLAGS')
                    cur_item.append(msg['flags'])
                elif data_item == 'INTERNALDATE':
                    cur_item.append(b'INTERNALDATE')
                    cur_item.append(msg['date'])
                elif data_item == 'UID':
                    if not uid_set:
                        cur_item.append(b'UID')
                        cur_item.append(msg['uid'])
                        uid_set = True
                elif data_item == 'BODY.PEEK[]':
                    cur_item.append(b'BODY[]')
                    #cur_item.append(msg['content'])    # FIXME: client should work with any encoding
                    cur_item.append(encode_literal(msg['content']))
                else:
                    raise ValueError("Fetching data item %s is unsupported" % data_item)
            self.__send_response('*', ("%d FETCH" % (msg_idx+1)).encode('ascii'), [cur_item], b'')
        self.__send_response(tag, b'OK', [], b'FETCH complete')

    __command_handlers = {
        'capability': __handle_cmd_capability,
        'examine': __handle_cmd_examine,
        'fetch': __handle_cmd_fetch,
        'list': __handle_cmd_list,
        'login': __handle_cmd_login,
        'logout': __handle_cmd_logout,
        'noop': __handle_cmd_noop,
        'select': __handle_cmd_select,
    }

    def __try_process_command(self):
        tag = self.__iobuf.read_string(True)
        self.__iobuf.eat_chars(b' ')
        cmd = self.__iobuf.read_string(True)
        if cmd.lower() == 'uid':
            self.__iobuf.eat_chars(b' ')
            cmd = self.__iobuf.read_string(True)
            uid_cmd = True
        else:
            uid_cmd = False

        if cmd.lower() in self.__class__.__command_handlers.keys():
            return self.__class__.__command_handlers[cmd.lower()](self, tag, uid_cmd)
        self.__send_response(tag, b'BAD', [], b'Command not implemented')
        raise ValueError("Unsupported command: %s, uid=%s" % (cmd, uid_cmd))

    def __process_commands(self):
        should_quit = False
        while not should_quit:
            should_quit = self.__try_process_command()

    def __is_authenticated(self):
        return self.__login is not None

    def __is_selected(self):
        return self.__selected_mailbox is not None

    def run(self, args, in_stream, out_stream):
        self.__iobuf = IMAPIOBuffer(in_stream, out_stream, args.wire_tap_filename)
        self.__expected_min_size = 0
        self.__current_command = None
        self.__login = None
        self.__encode_str_as = args.encode_str_as
        with open(args.initial_mboxes_content, "r") as f:
            self.__mailboxes = json.load(f)
        self.__selected_mailbox = None
        self.__writable = None
        self.__send_response('*', b'OK', [], b'IMAP4rev1 Server Ready')
        try:
            self.__process_commands()
            self.__iobuf.close()
        except ConnectionClosedException:
            pass
        with open(args.dump_mbox_filename, "w") as f:
            json.dump(self.__mailboxes, f)

    def get_arg_parser(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('--initial_mboxes_content', required=True)
        parser.add_argument('--wire_tap_filename')
        parser.add_argument('--encode_str_as', choices=['utf7m', 'utf8', 'literal'], required=True)
        parser.add_argument('--dump_mbox_filename')
        return parser

class IMAPIOBuffer(object):
    def __init__(self, in_stream, out_stream, wire_tap_filename):
        self.__in_stream = in_stream
        self.__out_stream = out_stream
        self.__buffer = b''
        if wire_tap_filename is None:
            self.__wire_tap = None
        else:
            self.__wire_tap = open(wire_tap_filename, "wb")

    def get_buffer(self):
        return self.__buffer

    def eat_chars(self, chars):
        self.ensure_read(len(chars))
        assert self.__buffer[0:len(chars)] == chars
        self.eat_data(len(chars))

    def __read_data(self):
        new_dat = self.__in_stream.read(8192)
        if len(new_dat) == 0:
            self.close()
            raise ConnectionClosedException()
        self.__buffer += new_dat
        if self.__wire_tap is not None:
            self.__wire_tap.write( ('RECV(%d):' % len(new_dat)).encode('ascii') )
            self.__wire_tap.write(new_dat)

    def ensure_read(self, count):
        while len(self.__buffer) < count:
            self.__read_data()

    def eat_data(self, count):
        self.__buffer = self.__buffer[count:]

    def write_data(self, data):
        self.__out_stream.write(data)
        if self.__wire_tap is not None:
            self.__wire_tap.write( ('SND(%d):' % len(data)).encode('ascii') )
            self.__wire_tap.write(data)
        self.__out_stream.flush()

    def close(self):
        self.__in_stream.close()
        self.__out_stream.close()

    def __read_literal():
        assert self.__buffer[0] == b'{'
        while self.__buffer.find(b'}') == -1:
            self.__ensure_read(len(self.__buffer)+1)
        close_brace_idx = self.__buffer.find(b'}')
        byte_count = int(self.__buffer[1:close_brace_idx])
        self.eat_data(close_brace_idx)
        self.write_data(b'+ go ahead' + _CRLF)
        self.ensure_read(byte_count)
        literal  = self.__buffer[:byte_count]
        self.eat_data(byte_count)
        return literal

    def read_string(self, only_raw):
        data = b''
        end_found = False
        self.ensure_read(1)
        if self.__buffer[0:1] == b'{':
            if only_raw:
                assert False
            return self.__read_literal()
        quoted = self.__buffer[0:1] == b'"'
        if only_raw:
            assert not quoted
        escape = False
        while not end_found:
            if self.__buffer[0:len(_CRLF)] == _CRLF:
                end_found = True
                break
            ends_with_cr = False
            for idx in range(len(self.__buffer)):
                if escape:
                    escape = False
                    continue
                if (not quoted) and (self.__buffer[idx:idx+1] == b' '):
                    end_found = True
                    break
                elif quoted and (idx != 0) and (self.__buffer[idx:idx+1] == b'"'):
                    idx += 1
                    end_found = True
                    break
                elif quoted and (self.__buffer[idx:idx+1] == b'\\'):
                    escape = True
                elif self.__buffer[idx:idx+1] == _CRLF[0:1]:
                    ends_with_cr = True
                    break
                elif (not quoted) and (self.__buffer[idx:idx+1]) == b')':
                    end_found = True
                    break
            this_read = self.__buffer[:idx]
            data += this_read
            self.eat_data(len(this_read))
            if not end_found:
                self.ensure_read(2 if (ends_with_cr or escape) else 1)
        if (not quoted) and (data == b'NIL'):
            return None
        if only_raw:
            return data.decode('ascii')
        else:
            return imaputil.imapname_to_str(data)

    def read_list_or_string(self):
        self.ensure_read(1)
        if self.__buffer[0:1] != b'(':
            return self.read_string(False)
        self.eat_chars(b'(')
        res = []
        while True:
            if self.__buffer[0:1] == b'(':
                res.append(self.__read_list_or_string())
            else:
                res.append(self.read_string(False))
            self.ensure_read(1)
            if self.__buffer[0:1] not in b' )':
                raise ValueError("Could not parse list")
            else:
                if self.__buffer[0:1] == b' ':
                    self.eat_chars(b' ')
                else:
                    self.eat_chars(b')')
                    return res

if __name__ == "__main__":
    tis = TestImapServer()
    tis.run(tis.get_arg_parser().parse_args(), sys.stdin.buffer.raw, sys.stdout.buffer.raw)

