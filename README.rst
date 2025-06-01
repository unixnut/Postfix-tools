=============
Postfix tools
=============


.. image:: https://img.shields.io/pypi/v/postscan.svg
        :target: https://pypi.python.org/pypi/postscan



Tools, scripts and config for use with the Postfix MTA.


* Free software: GNU General Public License v3

postscan
--------

Accepts system mail logs on standard input and provides individual details of
all e-mail messages received.  Note that this can produce a *lot* of output on
a busy system.

Makes the following assumptions:

- Postfix is your MTA
- dovecot-lda is your delivery agent
- (optional) SpamAssassin is set up

Run ``postscan --help`` for command-line options.

TO-DO:

- Show local messages generated from redirects without having to use -l
- Options to show rejected and/or bounced messages

postresolve
-----------

Since ``sendmail -bv`` doesn't work as expected, this fakes it to show you what a
given user resolves to (e.g. by processing aliases)

tweak_clamav-milter
-------------------

This script assumes ``clamav-milter`` and SpamAssassin have been installed.

::

  tweak_clamav-milter

This will alter the configurations to suit SpamAssassin and ClamAV being
invoked at SMTP time by milters, e.g. mail filter plugins.

Then, in your Postfix ``main.cf``, set::

  smtpd_milters = unix:/spamass/spamass.sock, unix:/clamav/clamav-milter.ctl

=======
Credits
=======

Development Lead
----------------

* Alastair Irvine <alastair@plug.org.au>

Other Credits
-------------

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
