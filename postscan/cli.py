# -*- coding: utf-8 -*-

"""Console script for postscan."""

from __future__ import absolute_import

import sys
import click
import logging

from postscan import Controller


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
def main(to, client_ip, local, spam_level, verbose, args=None):
    """Console script for postscan."""
    
    logger = logging.getLogger("postscan")

    params = {}
    params['to'] = to
    params['client_ip'] = client_ip
    params['local'] = local
    params['spam_level'] = spam_level

    controller = Controller(params, logger)

    # TO-DO: handle multiple files, etc.
    return controller.parse_stream(sys.stdin)


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
