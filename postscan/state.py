from __future__ import absolute_import

from .uuid_helper import UUIDs


class StateMachine(object):
    messages = {}
    deliveries_by_id = {}     # Mapping of message-id to { <username>: {<delivery-data>}}
    uuid_queue = UUIDs()
    uuid_owners = {}          # Mapping of fake msg_id string to username string


    def __init__(self, target_rcpt, discard_threshold, ip_re, logger):
        self.target_rcpt = target_rcpt
        self.discard_threshold = discard_threshold
        self.ip_re = ip_re
        self.log = logger


    def dispatch(self, label, match_groups, line_num):
        method_name = 'handle_{0}'.format(label)
        return getattr(self, method_name)(match_groups, line_num)


    def handle_connect(self, match_groups, line_num):
        dt, smtpd_pid, host, ip = match_groups
        self.log.debug(ip)


    def handle_client(self, match_groups, line_num):
        dt, smtpd_pid, queue_id, host, ip = match_groups
        self.log.debug(queue_id)
        if self.ip_re is None or not self.ip_re.match(ip):
            self.messages[queue_id] = {'dt': dt, 'ip': ip, 'msg_id_faked': False,
                                       'duplicate_msg_id': False, 'blessed': False}


    def handle_pickup(self, match_groups, line_num):
        dt, pickup_pid, queue_id, uid, username = match_groups
        self.log.debug(queue_id)
        self.messages[queue_id] = {'dt': dt, 'ip': "%s(%s)" % (username, uid),
                                   'msg_id_faked': False,
                                   'duplicate_msg_id': False, 'blessed': False}


    def handle_disconnect(self, match_groups, line_num):
        dt, smtpd_pid, host, ip = match_groups


    def handle_cleanup(self, match_groups, line_num):

        # E.g. "... postfix/cleanup[44462]: EBA07667720: message-id=<1533884753792.b2c522e5-18f2-4b30-bd0d-1a622ab63539@notify.sendle.com>"
        dt, cleanup_pid, queue_id, msg_id = match_groups
        self.log.debug(queue_id)

        if queue_id in self.messages:
            if not msg_id:
                # For messages without an ID ("message-id=<>"), push onto onto the
                # front of the queue, i.e. last in, first out order; this is done
                # even if ignoring this message, to keep pushes and pops balanced.
                msg_id = self.uuid_queue.create()
                self.messages[queue_id]['msg_id_faked'] = True
                self.log.debug("cleanup pushing id: %s", msg_id)

            self.messages[queue_id]['to'] = []
            self.messages[queue_id]['msg_id'] = msg_id
            if msg_id in self.deliveries_by_id:
                # It's a duplicate
                ## self.messages[queue_id]['msg_id_count'] += 1
                pass
            else:
                # Normal case
                self.deliveries_by_id[msg_id] = {}
            ## self.messages[queue_id]['deliveries'] = {}


    def handle_envfrom(self, match_groups, line_num):
        dt, qmgr_pid, queue_id, envfrom, num_rcpt = match_groups
        if queue_id in self.messages:
            self.log.debug(envfrom)
            self.messages[queue_id]['envfrom'] = envfrom


    def handle_result(self, match_groups, line_num):
        """Handle a spamd result line with the message score, tags and
        properties."""

        dt, spamd_pid, int_score, tags, user, msg_id = match_groups
        uuid_del = False  # Do we need to clean up the queue or save for handle_local()?

        if not msg_id:
            try:
                # For messages without an ID ("mid=(unknown)"), get the first one
                # from the queue, i.e. last in, first out order; hunt for the
                # correct fake msg_id in the queue unless the message was delivered
                # to multiple recipients
                msg_id = self.uuid_queue.peek()
                if user != 'spamass-milter':
                    # Check for the case where this is a "new" UUID
                    if msg_id not in self.uuid_owners or \
                       self.uuid_owners[msg_id] != user:
                        # Cycle through UUIDs to find the first un-owned one and claim it
                        queue_index = 0
                        while msg_id in self.uuid_owners:
                            queue_index += 1
                            msg_id = self.uuid_queue.peek(queue_index)
                        self.uuid_owners[msg_id] = user

                uuid_del = True

            except IndexError:
                # No message IDs in the queue
                msg_id = "?"

        self.log.debug("result id: %s", msg_id)

        # Note: queue_id is not unique per message-id, so only store info per message-id
        if msg_id in self.deliveries_by_id:
            self.log.debug("score is %d (%s)", int(int_score), user)
            self.record_delivery(msg_id, user, int(int_score))


    def handle_lda(self, match_groups, line_num):
        dt, user, msg_id_a, msg_id_b, mailbox = match_groups

        msg_id = msg_id_a if msg_id_a else msg_id_b

        if not msg_id:
            # For messages without an ID ("msgid=unspecified"), look at the first one
            # on the queue, i.e. last in, first out order
            if self.uuid_queue.empty():
                return
            msg_id = self.uuid_queue.peek()

        if msg_id in self.deliveries_by_id:
            # Note: queue_id is not unique per message-id, so only store info per message-id
            ## queue_id = self.deliveries_by_id[msg_id]
            # Record the delivery, with a spam score if available
            if user in self.deliveries_by_id[msg_id]:
                self.deliveries_by_id[msg_id][user]['mailbox'] = mailbox
                self.deliveries_by_id[msg_id][user]['count'] += 1
            else:
                self.record_delivery(msg_id, user, None, mailbox)
        else:
            self.log.debug("Ignoring LDA for %s", msg_id)


    def record_delivery(self, msg_id, user, int_score=None, mailbox=None):
        self.deliveries_by_id[msg_id][user] = { 'int_score': int_score,
                                                'user': user,
                                                'count': 1 }
        if mailbox:
            self.deliveries_by_id[msg_id][user]['mailbox'] = mailbox


    def handle_local(self, match_groups, line_num):
        dt, local_pid, queue_id, rcpt, envto = match_groups
        if queue_id in self.messages:
            ## if envto:
            ## print(line_num, file=sys.stderr)
            parts = rcpt.lower().split("@")
            self.messages[queue_id]['to'].append((rcpt, envto, parts[0]))
            self.messages[queue_id]['blessed'] = self.target_rcpt in (None, rcpt, envto)


    def handle_removed(self, match_groups, line_num):
        dt, qmgr_pid, queue_id = match_groups
        self.log.debug(queue_id + " deleted")
        if queue_id in self.messages:
            msg_id = self.messages[queue_id]['msg_id']
            if 'envfrom' not in self.messages[queue_id]:
                # Bounce message
                self.messages[queue_id]['envfrom'] = "<mail daemon>"
            default_score = None
            max_int_score = -1000
            if msg_id in self.deliveries_by_id:
                # Find the highest spame score across all users this message was delivered to
                for username in self.deliveries_by_id[msg_id]:
                    delivery = self.deliveries_by_id[msg_id][username]
                    if delivery['int_score'] is not None and \
                       max_int_score < delivery['int_score']:
                        max_int_score = delivery['int_score']
                    if 'mailbox' not in delivery:
                        default_score = delivery['int_score']

            if (self.discard_threshold is None or \
                max_int_score < self.discard_threshold) and \
               self.messages[queue_id]['blessed']:
                self.print_info(queue_id, default_score)
            else:
                self.log.debug("X %s", queue_id)
            if msg_id in self.deliveries_by_id:
                del self.deliveries_by_id[msg_id]

            if self.messages[queue_id]['msg_id_faked']:
                fake_msg_id = self.uuid_queue.pop(msg_id)
                self.log.debug("handle_removed() got id %s from queue", fake_msg_id)
                assert fake_msg_id == msg_id
                self.log.debug("handle_removed() popping id; %d left", len(self.uuid_queue.uuids))
                self.log.debug("uuid_owners: %s", self.uuid_owners)
                if msg_id in self.uuid_owners:
                    # This is only present when the username is not "spamass-milter"
                    del self.uuid_owners[msg_id]
            del self.messages[queue_id]


    def print_info(self, queue_id, default_score):
        msg_id = self.messages[queue_id]['msg_id']
        m = self.messages[queue_id]
        print(queue_id + ": ({dt}) {envfrom} [{ip}]\n  ({msg_id})".format(**m))
        # Note: each delivery is not currently tied to a recipient
        for rcpt, envto, username in m['to']:
            if envto:
                print("  {0} = {1}".format(rcpt, envto))
            else:
                print("  {0}".format(rcpt))
            if msg_id in self.deliveries_by_id and username in self.deliveries_by_id[msg_id]:
                delivery = self.deliveries_by_id[msg_id][username]
                if delivery['int_score'] is None:
                    delivery['int_score'] = default_score
                fields = {'mailbox': "(none)"}
                fields.update(delivery)
                print("  ...{user}: saved to '{mailbox}', spam level {int_score}".format(**fields))
        print("")


    def handle_rejected(self, match_groups, line_num):
        dt, cleanup_pid, queue_id = match_groups

        if queue_id in self.messages:
            msg_id = self.messages[queue_id]['msg_id']
            if self.messages[queue_id]['msg_id_faked']:
                self.uuid_queue.pop(msg_id)

    # TODO
    def handle_bounce(self, match_groups, line_num):
        pass


    def cleanup(self):
        self.log.debug("zombie messages: %d; zombie message IDs: %d",
                       len(self.messages), len(self.deliveries_by_id))
