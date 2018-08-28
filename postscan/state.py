from __future__ import absolute_import

from .uuid_helper import UUIDs


# TO-DO: implement handle_pickup()
class StateMachine(object):
    messages = {}
    messages_by_id = {}
    self.id_user_queue_map = []  # Each msg_id mapping is {'queue_ids': [], 'users': []}
    uuid_queue = UUIDs()


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
            self.messages[queue_id] = {'dt': dt, 'ip': ip, 'fake_msg_id': False}


    def handle_disconnect(self, match_groups, line_num):
        dt, smtpd_pid, host, ip = match_groups


    def handle_cleanup(self, match_groups, line_num):
        dt, cleanup_pid, queue_id, msg_id = match_groups
        self.log.debug(queue_id)

        if queue_id in self.messages:
            if not msg_id:
                # For messages without an ID ("message-id=<>"), push onto onto the
                # front of the queue, i.e. last in, first out order; this is done
                # even if ignoring this message, to keep pushes and pops balanced.
                msg_id = self.uuid_queue.create()
                self.messages[queue_id]['fake_msg_id'] = True
                self.log.debug("cleanup pushing id: %s", msg_id)

            self.messages[queue_id]['msg_id'] = msg_id
            if msg_id in self.messages_by_id:
                # Duplicate msg_id
                self.id_user_queue_map[msg_id] = {'queue_ids': [self.messages_by_id[msg_id]], 'users': []}
                self.messages_by_id[msg_id] = None
            else:
                # Normal case
                self.messages_by_id[msg_id] = queue_id
            self.messages[queue_id]['to'] = []
            self.messages[queue_id]['deliveries'] = {}


    def handle_envfrom(self, match_groups, line_num):
        dt, qmgr_pid, queue_id, envfrom, num_rcpt = match_groups
        if queue_id in self.messages:
            self.log.debug(envfrom)
            self.messages[queue_id]['envfrom'] = envfrom


    def handle_result(self, match_groups, line_num):
        dt, spamd_pid, int_score, tags, user, msg_id = match_groups
        uuid_del = False  # Do we need to clean up the queue or save for handle_local()?

        if not msg_id:
            # For messages without an ID ("mid=(unknown)"), get the first one
            # from the queue, i.e. last in, first out order
            msg_id = self.uuid_queue.peek()
            self.log.debug("result peeking id: %s", msg_id)
            uuid_del = True

        if msg_id in self.messages_by_id:
            queue_id = self.messages_by_id[msg_id]
            if self.discard_threshold is None or \
               int_score < self.discard_threshold:
                self.log.debug("score is %d (%s)", int(int_score), user)
                self.messages[queue_id]['last_int_score'] = int(int_score)
                self.messages[queue_id]['deliveries'][user] = { 'int_score': int(int_score), 'user': user, 'count': 1 }
            else:
                self.log.debug("X %s", queue_id)
                del self.messages[queue_id]
                del self.messages_by_id[msg_id]
                if uuid_del: self.uuid_queue.pop()


    def handle_lda(self, match_groups, line_num):
        dt, user, msg_id, mailbox = match_groups
        if not msg_id:
            # For messages without an ID ("msgid=unspecified"), get the first one
            # from the queue, i.e. last in, first out order
            msg_id = self.uuid_queue.pop()
            self.log.debug("LDA scan popping id; %d left", len(self.uuid_queue.uuids))

        if msg_id in self.messages_by_id:
            queue_id = self.messages_by_id[msg_id]
            # Record the delivery, with a spam score if available
            if 'user' in self.messages[queue_id]['deliveries']:
                u = self.messages[queue_id]['deliveries'][user]
                u['mailbox'] = mailbox
                u['count'] += 1
            else:
                if 'last_int_score' in self.messages[queue_id]:
                    int_score = self.messages[queue_id]['last_int_score']
                else:
                    int_score = 0
                self.messages[queue_id]['deliveries'][user] = { 'int_score': int_score, 'user': user, 'mailbox': mailbox, 'count': 1 }
        else:
            self.log.debug("Ignoring LDA for %s", msg_id)


    def handle_local(self, match_groups, line_num):
        dt, local_pid, queue_id, rcpt, envto = match_groups
        if queue_id in self.messages and \
            (self.target_rcpt is None or \
             self.target_rcpt == rcpt or self.target_rcpt == envto):
            ## if envto:
            ## print(line_num, file=sys.stderr)
            self.messages[queue_id]['to'].append((rcpt, envto))


    def handle_removed(self, match_groups, line_num):
        dt, qmgr_pid, queue_id = match_groups
        self.log.debug(queue_id + " deleted")
        if queue_id in self.messages:
            msg_id = self.messages[queue_id]['msg_id']
            m = self.messages[queue_id]
            print(queue_id + ": ({dt}) {envfrom} [{ip}]\n  ({msg_id})".format(**m))
            # Note: each delivery is not currently tied to a recipient
            for rcpt, envto in m['to']:
                if envto:
                    print("  {0} = {1}".format(rcpt, envto))
                else:
                    print("  {0}".format(rcpt))
            for user in m['deliveries']:
                d = m['deliveries'][user]
                if 'mailbox' in m['deliveries'][user]:
                    print("  ...{user}: saved to '{mailbox}', spam level {int_score}".format(**d))
                else:
                    # It's a system user used only for spam scoring
                    pass
            print("")

            del self.messages[queue_id]
            del self.messages_by_id[msg_id]


    def handle_rejected(self, match_groups, line_num):
        dt, cleanup_pid, queue_id = match_groups

        if queue_id in self.messages:
            msg_id = self.messages[queue_id]['msg_id']
            if self.messages[queue_id]['fake_msg_id']: self.uuid_queue.pop()
