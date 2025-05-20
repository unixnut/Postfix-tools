# -*- coding: utf-8 -*-

"""Console script for postscan."""

from __future__ import absolute_import
from __future__ import print_function

import sys
import logging

import click

from .postscan import Controller
from . import __version__


@click.command()
@click.option('-t', '--to',        type=click.STRING,
              help="Saves iff 'to' or 'orig_to' matches <addr>")
@click.option('-C', '--client-ip', type=click.STRING,
              help="Ignores e-mails if the client host's address matches <ipfragment>")
@click.option('-l/-L', '--local/--no-local', default=False,
              help="Save e-mails generated locally (ignored by default)")
@click.option('-s', '--spam-level', type=click.INT,
              help="Ignores if the integer spam level is greater than or equal to <level>")
@click.option('-v', '--verbose', count=True)
@click.option('-o/-e', '--stdout/--no-stdout', default=False,
              help="Logs to stdout instead of stderr")
@click.option('-V', '--version', is_flag=True, default=False)
@click.argument('files', type=click.File(), nargs=-1)
def main(files, to, client_ip, local, spam_level, verbose, stdout, version, args=None):
    """Console script for postscan."""

    if version:
        print("postscan v" + __version__)
        return 0

    logger = logging.getLogger("postscan")
    if stdout:
        logger.addHandler(logging.StreamHandler(sys.stdout))
    else:
        logger.addHandler(logging.StreamHandler())
    if verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    params = {}
    params['to'] = to
    params['client_ip'] = client_ip
    params['local'] = local
    params['spam_level'] = spam_level

    controller = Controller(params, logger)

    if files:
        for stream in files:
            controller.parse_stream(stream)
    else:
        controller.parse_stream(sys.stdin)

    return 0


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
