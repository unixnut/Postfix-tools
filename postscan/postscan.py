# -*- coding: utf-8 -*-

"""
Main module.

Parses string input using :class:Scanner and hands events to
:class:StateMachine.
"""

from __future__ import absolute_import

import re

from .state import StateMachine
from .scanner import Scanner


class Controller(object):
    def __init__(self, params, logger):
        self.log = logger

        self.scanner = Scanner(params['local'], logger)

        if params['client_ip']:
            ip_re = re.compile(params['client_ip'])
        else:
            ip_re = None
        self.handler = StateMachine(params['to'], params['spam_level'], ip_re, logger)


    def parse_stream(self, stream):
        for line_num, line in enumerate(stream):
            result = self.scanner.find(line, line_num + 1)
            if result:
                label, groups = result
                self.log.debug("Handling %s on %d", label, line_num + 1)
                self.handler.dispatch(label, groups, line_num + 1)
            ## else:
            ##     print("?")
