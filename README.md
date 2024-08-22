[imapmirror]: https://github.com/imapmirror/imapmirror

Links:
* Official github code repository for Python3: [imapmirror]

# IMAPMirror

***"Get the emails where you need them."***


## Description

IMAPMirror is software that downloads your email mailbox(es) as **local
Maildirs**. IMAPMirror will synchronize both sides via *IMAP*. It is a
fork of OfflineIMAP3


## Why should I use IMAPMirror?

With IMAPMirror, you can download your Mailboxes and make your own backups of
your [Maildir](https://en.wikipedia.org/wiki/Maildir).

This allows reading your email offline without the need for your mail
reader (MUA) to support IMAP operations. Need an attachment from a
message without internet connection? No problem, the message is still there.


## Project status and future

IMAPMirror, using Python 3, is based on OfflineIMAP for Python 3.



## License

GNU General Public License v2.


## Downloads

You should first check if your distribution already packages OfflineIMAP for you.
Downloads releases as [tarball or zipball](https://github.com/imapmirror/imapmirror/tags).

## Feedbacks and contributions

Bugs, issues and contributions can be tracked on
[official Github project][imapmirror].  Provide the following information:
- system/distribution (with version)
- imapmirror version (`imapmirror -V`)
- Python version
- server name or domain
- CLI options
- Configuration file (imapmirrorrc)
- pythonfile (if any)
- Logs, error
- Steps to reproduce the error


## The community

* IMAPMirror's main site is the [project page at Github][imapmirror].


## Requirements & dependencies

* Python v3.8+
* rfc6555 (required)
* imaplib2 >= 3.5
* gssapi (optional), for Kerberos authentication
* portalocker (optional), if you need to run imapmirror in Cygwin for Windows

### Documentation

Documentation is available in the doc/ directory of [IMAPMirror repository][imapmirror]
