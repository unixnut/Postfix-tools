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
        self.handler = StateMachine(params['to'], params['spam_level'], ip_re, logger.getChild('state'))


    def parse_stream(self, stream):
        for i, line in enumerate(stream):
            line_num = i + 1
            result = self.scanner.find(line, line_num)
            if result:
                label, groups = result
                self.log.debug("Handling %s on %d", label, line_num)
                self.handler.dispatch(label, groups, line_num)
            ## else:
            ##     print("?")
        self.handler.cleanup()
