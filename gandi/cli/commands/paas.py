import click

from gandi.cli.core.cli import cli
from gandi.cli.core.utils import output_paas, output_generic
from gandi.cli.core.params import pass_gandi, DATACENTER, PAAS_TYPE, option


@cli.command()
@click.option('--state', default=None, help='filter results by state')
@click.option('--id', help='display ids', is_flag=True)
@click.option('--vhosts', help='display vhosts', default=True, is_flag=True)
@click.option('--limit', help='limit number of results', default=100,
              show_default=True)
@pass_gandi
def list(gandi, state, id, vhosts, limit):
    """List PaaS instances."""

    options = {
        'items_per_page': limit,
    }
    if state:
        options['state'] = state

    output_keys = ['name', 'state']
    if id:
        output_keys.append('id')
    if vhosts:
        output_keys.append('vhost')

    paas_hosts = {}
    result = gandi.paas.list(options)
    for paas in result:
        paas_hosts[paas['id']] = []
        if vhosts:
            list_vhost = gandi.vhost.list({'paas_id': paas['id']})
            for host in list_vhost:
                paas_hosts[paas['id']].append(host['name'])

        gandi.separator_line()
        output_paas(gandi, paas, [], paas_hosts[paas['id']],
                    output_keys)

    return result


@cli.command()
@click.argument('resource')
@pass_gandi
def info(gandi, resource):
    """Display information about a PaaS instance.

    Resource can be a vhost, a hostname, or an ID
    """

    output_keys = ['name', 'type', 'size', 'memory', 'console', 'vhost',
                   'dc', 'sftp_server', 'git_server']

    paas = gandi.paas.info(resource)
    paas_hosts = []
    list_vhost = gandi.vhost.list({'paas_id': paas['id']})
    for host in list_vhost:
        paas_hosts.append(host['name'])

    output_paas(gandi, paas, [], paas_hosts, output_keys)

    return paas


@cli.command()
@click.argument('vhost', required=False)
@pass_gandi
def clone(gandi, vhost):
    """Clone a remote vhost in a local git repository."""

    paas_access = gandi.get('paas.access')
    if not vhost and not paas_access:
        gandi.error('missing VHOST parameter')

    if vhost and not paas_access:
        gandi.paas.init_conf(vhost)

    paas_access = gandi.get('paas.access')
    gandi.shell('git clone ssh+git://%s/%s.git' % (paas_access, vhost))


@cli.command(root=True)
@click.argument('vhost', required=False)
@pass_gandi
def deploy(gandi, vhost):
    """Deploy code on a remote vhost."""

    paas_access = gandi.get('paas.access')
    if not vhost and not paas_access:
        gandi.error('missing VHOST parameter')

    if vhost and not paas_access:
        gandi.paas.init_conf(vhost)

    paas_access = gandi.get('paas.access')
    deploy_git_host = gandi.get('paas.deploy_git_host')

    gandi.shell("ssh %s 'deploy %s'" % (paas_access, deploy_git_host))


@cli.command()
@click.option('--background', default=False, is_flag=True,
              help='run in background mode (default=False)')
@click.option('--force', '-f', is_flag=True,
              help='This is a dangerous option that will cause CLI to continue'
                   ' without prompting. (default=False)')
@click.argument('resource', nargs=-1)
@pass_gandi
def delete(gandi, background, force, resource):
    """Delete a PaaS instance.

    Resource can be a vhost, a hostname, or an ID
    """

    output_keys = ['id', 'type', 'step']

    if not force:
        instance_info = "'%s'" % ', '.join(resource)
        proceed = click.confirm("Are you sure to delete PaaS instance %s ?" %
                                instance_info)

        if not proceed:
            return

    opers = gandi.paas.delete(resource, background)
    if background:
        for oper in opers:
            output_generic(gandi, oper, output_keys)

    return opers


@cli.command()
@option('--name', default='paastempo',
        help='Name of the PaaS instance')
@option('--size', default='s',
        type=click.Choice(['s', 'm', 'x', 'xl', 'xxl']),
        help='Size of the PaaS instance')
@option('--type', default='pythonpgsql',
        type=PAAS_TYPE,
        help='Type of the PaaS instance')
@option('--quantity', default=0,
        help='Additional disk amount (in GB)')
@option('--duration', default='1m',
        help='number of month, suffixed with m')
@option('--datacenter', type=DATACENTER, prompt=True,
        help='datacenter where the PaaS will be spawned')
@click.option('--vhosts', default=None, multiple=True,
              help='List of virtual hosts to be linked to the instance')
@click.option('--password', prompt=True, hide_input=True,
              confirmation_prompt=True, required=True,
              help='Password of the PaaS instance')
@click.option('--snapshot-profile', default=None,
              help='Set a snapshot profile associated to this paas disk')
@click.option('--background', default=False, is_flag=True,
              help='run creation in background mode (default=False)')
@option('--ssh-key',
        help='Authorize ssh authentication for the given ssh key')
@pass_gandi
def create(gandi, name, size, type, quantity, duration, datacenter, vhosts,
           password, snapshot_profile, background, ssh_key):
    """Create a new PaaS instance and initialize associated git repository.

    you can specify a configuration entry named 'ssh_key' containing
    path to your ssh_key file

    >>> gandi config -g ssh_key ~/.ssh/id_rsa.pub

    to know which PaaS instance type to use as type

    >>> gandi types

    """
    result = gandi.paas.create(name, size, type, quantity, duration,
                               datacenter, vhosts, password,
                               snapshot_profile, background, ssh_key)
    if background:
        gandi.pretty_echo(result)

    gandi.paas.init_conf(name)

    return result


@cli.command()
@click.option('--name', type=click.STRING, default=None,
              help='Name of the PaaS instance')
@click.option('--size', default=None,
              type=click.Choice(['s', 'm', 'x', 'xl', 'xxl']),
              help='Size of the PaaS instance')
@click.option('--quantity', type=click.INT, default=0,
              help='Additional disk amount (in GB)')
@click.option('--password', default=False, is_flag=True,
              help='Password of the PaaS instance')
@click.option('--ssh-key', default=None,
              help='Authorize ssh authentication for the given ssh key')
@click.option('--upgrade', default=None,
              help='Upgrade the instance to the last system image if needed')
@click.option('--console', default=None,
              help='Activate or deactivate the Console')
@click.option('--snapshot-profile', default=None,
              help='Set a snapshot profile associated to this paas disk')
@click.option('--reset-mysql-password', default=None,
              help='Reset mysql password for root')
@click.option('--background', default=False, is_flag=True,
              help='run update in background mode (default=False)')
@pass_gandi
@click.argument('resource')
def update(gandi, resource, name, size, quantity, password, ssh_key,
           upgrade, console, snapshot_profile, reset_mysql_password,
           background):
    """Update a PaaS instance.

    Resource can be a Hostname or an ID
    """
    pwd = None
    if password:
        pwd = click.prompt('password', hide_input=True,
                           confirmation_prompt=True)

    result = gandi.paas.update(resource, name, size, quantity, pwd,
                               ssh_key, upgrade, console, snapshot_profile,
                               reset_mysql_password, background)
    if background:
        gandi.pretty_echo(result)

    return result


@cli.command()
@pass_gandi
def types(gandi):
    """List types PaaS instances."""

    options = {}
    types = gandi.paas.type_list(options)
    for type_ in types:
        gandi.echo(type_['name'])

    return types
