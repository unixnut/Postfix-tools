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
        self.scanner = Scanner(params['local'])

        if params['client_ip']:
            ip_re = re.compile(params['client_ip'])
        else:
            ip_re = None
        self.handler = StateMachine(params['to'], params['spam_level'], ip_re, logger)


    def parse_stream(self, stream):
        line_num = 1
        for line in stream:
            result = self.scanner.find(line)
            if result:
                label, groups = result
                self.handler.dispatch(label, groups, line_num)
            ## else:
            ##     print("?")

            line_num = line_num + 1
