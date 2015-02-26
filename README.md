# Postfix-tweaks
Scripts and config for use with the Postfix MTA.

## tweak_clamav-milter
This script assumes `clamav-milter` and spamassassin have been installed.

Then, in your Postfix main.cf, set:
    - `smtpd_milters = unix:/spamass/spamass.sock, unix:/clamav/clamav-milter.ctl`
