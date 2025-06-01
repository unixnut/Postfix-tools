"""
Matches relevant log entries.
"""

from __future__ import absolute_import

import re
import socket


class Scanner(object):
    def __init__(self, include_local, logger):
        self.log = logger

        hostname = socket.gethostname()

        uuid_regex = r'[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}'

        # These identify relevant log lines
        # Date & host, e.g. "Aug 10 16:14:36 cagney "
        dh_regex =    '(\w{3} +\d+ \d{2}:\d{2}:\d{2}) %s ' % hostname
        # E.g. "... postfix/smtpd[22878]: 1864B667736: client=unknown[192.187.99.250]"
        smtpd_regex = dh_regex + 'postfix/(?:submission|smtpd)[^[]*\[(\d+)\]: '
        smtpd_re =    re.compile(smtpd_regex)
        host_ip_regex = '([\w\d\.-]+[\w\d\.-])\[(\d{1,3}\.\d{1,3}\.\d{1,3}.\d{1,3})\]'
        # https://stackoverflow.com/a/17644686/2067682
        # Modified to make the @... part optional; THANKS, APPLE.
        msg_id_regex = r'(?:(?:[a-zA-Z0-9!#$%&\'*+/=?^_`{|}~-]+(?:\.[a-zA-Z0-9!#$%&\'*+/=?^_`{|}~-]+)*)|(?:"(?:(?:[\x01-\x08\x0B\x0C\x0E-\x1F\x7F]|[\x21\x23-\x5B\x5D-\x7E])|(?:\\[\x01-\x09\x0B\x0C\x0E-\x7F]))*"))(?:@(?:(?:[a-zA-Z0-9!#$%&\'*+/=?^_`{|}~-]+(?:\.[a-zA-Z0-9!#$%&\'*+/=?^_`{|}~-]+)*)|(?:\[(?:(?:[\x01-\x08\x0B\x0C\x0E-\x1F\x7F]|[\x21-\x5A\x5E-\x7E])|(?:\\[\x01-\x09\x0B\x0C\x0E-\x7F]))*\])))?'
        ## msg_id_re  = re.compile(msg_id_regex)
        # E.g. "... connect from o417.notify.sendle.com[167.89.105.135]"
        connect_re =  re.compile(smtpd_regex + 'connect from ' + host_ip_regex)
        # E.g. "... disconnect from o417.notify.sendle.com[167.89.105.135]"
        disconnect_re =  re.compile(smtpd_regex + 'disconnect from ' + host_ip_regex)
        # E.g. "... client=unknown[192.187.99.250]"
        client_re =   re.compile(smtpd_regex + '(\w+): client=' + host_ip_regex)
        # E.g. "... postfix/pickup[46180]: 16982667739: uid=0 from=<root>"
        pickup_re =   re.compile(dh_regex + 'postfix/pickup\[(\d+)\]: (\w+): uid=(\d+) from=<([^>]+)>')
        # E.g. "... postfix/cleanup[44462]: EBA07667720: message-id=<1533884753792.b2c522e5-18f2-4b30-bd0d-1a622ab63539@notify.sendle.com>"
        #   or "Sep  3 12:16:47 cagney postfix/cleanup[30143]: 43877660443: message-id=<5B34496C16872430@smtp.telstra.com> (added by postmaster@smtp.telstra.com)
        # (The closing ">" at the end is optional, because it's missing when
        # there's a weird char at start of message-id, which isn't present in
        # this log line but is for spam result)
        cleanup_re =  re.compile('{0}postfix/cleanup\[(\d+)\]: (\w+): message-id=<?({1})?>?'
                                   .format(dh_regex, msg_id_regex))
        # E.g. "... postfix/qmgr[37259]: EBA07667720: "
        qmgr_regex =  dh_regex + 'postfix/qmgr\[(\d+)\]: (\w+): '
        qmgr_re =     re.compile(qmgr_regex)
        # E.g. "... from=<melissa@pagetraffic.tech>, size=3900, nrcpt=1 (queue active)"
        envfrom_regex = qmgr_regex + 'from=<([-\w!#$%&\'*+/=?^_`{|}~.]+@[-\w.]+)>.* nrcpt=(\d+)'
        envfrom_re  = re.compile(envfrom_regex)
        spamd_regex = dh_regex + 'spamd\[(\d+)\]: spamd: '
        spamd_re =    re.compile(spamd_regex)
        # E.g. "... result: . 4 - BAYES_60,HTML_IMAGE_ONLY_24,HTML_MESSAGE,HTML_SHORT_LINK_IMG_3,MIME_HTML_ONLY,MIME_HTML_ONLY_MULTI,MPART_ALT_DIFF,UNPARSEABLE_RELAY scantime=1.7,size=3752,user=spamass-milter,uid=124,required_score=5.0,rhost=localhost,raddr=127.0.0.1,rport=35658,mid=<PBLLr6b5xX05qVzhu_RZ8Wi_0ry5k4PWu2@wCac.adeptus.com>,bayes=0.715496,autolearn=no"
        # or "......,mid=(unknown)..."
        result_re =   re.compile('{0}result: . ([-\d]+) - (\S+) .*user=([^,]+).*mid=(?:<\??({1})\??>)?'
                                  .format(spamd_regex, msg_id_regex))
        # E.g. "... dovecot: lda(xyz): sieve: msgid=<f2f99cbdae05cab1de81cb0b3d519a98@RobertBanas.download>: stored mail into mailbox 'INBOX'"
        #   or "... dovecot: lda(xyz): sieve: msgid=<5B34496C16872430@smtp.telstra.com> (added by postmaster@smtp.telstra.com): stored mail into mailbox 'INBOX'
        #   or "... dovecot: lda(xyz): sieve: msgid=7a91f8d9-7f2d-4217-9498-a3fe503a68a8: stored mail into mailbox ' Spam'"
        #   or "... dovecot: lda(xyz): sieve: msgid=unspecified: stored mail into mailbox ' Spam'"
        #   or "... dovecot: lda(xyz): sieve: msgid=<5df9507c519f93780b2a8b8d4.19d1d6f996.20200628233841.0c38b20919.fc08a18c@mail20.sea91.rsgsv.net>: marked message to be discarded if not explicitly delivered (discard action)"
        #   or "... dovecot: lda(xyz): sieve: msgid=unspecified: forwarded to <bob@example.com>"
        #   or "... dovecot: lda(xyz)<20453><gtTeEEIBGWTlTwAAPWRvRg>: sieve: msgid=<40DA6E9C-B3DC-476E-A279-7D843CB64848@xyz.com.au>: stored mail into mailbox 'INBOX'"

        lda_re =      re.compile(r'{0}dovecot: lda\(([^)]+)\)(?:<[0-9]+><[/+a-zA-Z0-9]+>)?: sieve: '
                                 r'msgid=(?:[? ]*(?:<({1})>|({2}))(?: \([^)]*\))?|unspecified)'
                                 r"(?:: fileinto action)?"
                                 r"(?:: stored mail into mailbox '([^']+)')?"
                                   .format(dh_regex, msg_id_regex, uuid_regex))
        # E.g. "... postfix/local[8270]: 2FECF667738: to=<user@xyz.com.au>, orig_to=<info@xyz.com.au>, relay=local, delay=3.3, delays=3.2/0/0/0.04, dsn=2.0.0, status=sent (delivered to command: /usr/lib/dovecot/dovecot-lda -f "$SENDER" -a "$ORIGINAL_RECIPIENT" -d "$USER")"
        local_re =    re.compile(dh_regex + 'postfix/local\[(\d+)\]: (\w+): to=<([-\w\.]+@[-\w\.]+)>, (?:orig_to=<([-\w\.]+@[-\w\.]+)>)?')
        # E.g. "... 2FECF667738: removed"
        removed_re  = re.compile(qmgr_regex + 'removed')

        # E.g. "... postfix/cleanup[4499]: CADB76676A3: milter-reject: END-OF-MESSAGE from zgz2.honeyanda.com[185.237.96.123]: 5.7.1 Blocked by SpamAssassin; from=<winona@honeyanda.com> to=<user@xyz.com.au> proto=ESMTP helo=<zgz2.honeyanda.com>"
        rejected_re = re.compile(dh_regex + 'postfix/cleanup\[(\d+)\]: (\w+): milter-reject')

        # E.g. "... postfix/bounce[2153401]: 7A27C540AF7: sender non-delivery notification: D9244547B99"
        ## bounced_re = 

        self.rd = [(connect_re, 'connect'), (client_re, 'client'), (disconnect_re, 'disconnect'), (cleanup_re, 'cleanup'), (envfrom_re, 'envfrom'), (result_re, 'result'), (lda_re, 'lda'), (local_re, 'local'), (removed_re, 'removed'), (rejected_re, 'rejected')]
        if include_local:
            self.rd.append((pickup_re, 'pickup'))


    def find(self, s, line_num):
        """
        Iterates through a list of tuples of the form (re_object, label).
        If one of those matches, return the label and the match group.
        """
        for r in self.rd:
            m = r[0].match(s)
            if m:
                return r[1], m.groups()
