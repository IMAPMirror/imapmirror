.. -*- coding: utf-8 -*-
.. vim: spelllang=en ts=2 expandtab:

.. _IMAPMirror: https://github.com/imapmirror/imapmirror
.. _Repository: https://github.com/imapmirror/imapmirror
.. _Github: https://github.com/imapmirror/imapmirror
.. _How to fix a bug in open source software: https://opensource.com/life/16/8/how-get-bugs-fixed-open-source-software


=================
HOW TO CONTRIBUTE
=================

You'll find here the **basics** to contribute to IMAPMirror_, addressed to
users as well as learning or experienced developers to quickly provide
contributions.

**For more detailed documentation, see the** `Repository`_.

.. contents:: :depth: 3


Submit issues
=============

Issues are welcome to Github_, at your own
convenience. Provide the following information:
- system/distribution (with version)
- imapmirror version (`imapmirror -V`)
- Python version
- server name or domain
- CLI options
- Configuration file (imapmirrorrc)
- pythonfile (if any)
- Logs, error
- Steps to reproduce the error

Worth the read: `How to fix a bug in open source software`_.

You might help closing some issues, too. :-)


Community
=========

All contributors to IMAPMirror_ are benevolent volunteers. This makes hacking
to IMAPMirror_ **fun and open**.

Thanks to Python, almost every developer can quickly become productive. Students
and novices are welcome. Third-parties patches are essential and proved to be a
wonderful source of changes for both fixes and new features.

IMAPMirror_ is entirely written in Python, works on IMAP and source code is
tracked with Git.

*It is expected that most contributors don't have skills to all of these areas.*
That's why the best thing you could do for you, is to ask us about any
difficulty or question raising in your mind. We actually do our best to help new
comers. **We've all started like this.**


Getting started
===============

Occasional contributors
-----------------------

* Clone the official repository_.

Regular contributors
--------------------

* Create an account and login to Github.
* Fork the official repository_.
* Clone your own fork to your local workspace.
* Add a reference to your fork (once)::

  $ git remote add myfork https://github.com/<your_Github_account>/imapmirror.git

* Regularly fetch the changes applied by the maintainers::

  $ git fetch origin
  $ git checkout dev
  $ git merge imapmirror/dev
  $ git checkout next
  $ git merge offlineimap/next


Making changes (all contributors)
---------------------------------

1. Create your own topic branch off of ``next`` (recently updated) via::

   $ git checkout -b my_topic next

2. Check for unnecessary whitespaces with ``git diff --check`` before committing.
3. Commit your changes into logical/atomic commits.  **Sign-off your work** to
   confirm you agree with the `Developer's Certificate of Origin`_.
4. Write a good *commit message* about **WHY** this patch (take samples from
   the ``git log``).


Learn more
==========

There is already a lot of documentation. Here's where you might want to look
first:

- The directory ``imapmirror/docs`` has all kind of additional documentation
  (man pages, RFCs).

- The file ``imapmirror.conf`` allows to know all the supported features.

- The file ``TODO.rst`` express code changes we'd like and current *Work In
  Progress* (WIP).

