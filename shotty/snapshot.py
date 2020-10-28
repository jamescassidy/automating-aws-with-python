import boto3
import botocore
import click

session = boto3.Session(profile_name='default')
ec2 = session.resource('ec2')

def filter_instances(project):
    instances = []

    if project:
        filters = [{'Name':'tag:Project', 'Values':[project]}]
        instances = ec2.instances.filter(Filters=filters)
    else:
        instances = ec2.instances.all()

    return instances

def has_pending_snapshot(volume):
    snapshots = list(volume.snapshots.all())
    return snapshots and snapshots[0].state == 'pending'

@click.group()
@click.option('--profile', default=None,
    help="Use --profile to override the AWS default profile")
def cli(profile):
    """Commands to do EC2 things"""

    if profile:
        session = boto3.Session(profile_name=profile)
        ec2 = session.resource('ec2')
    return

@cli.group('snapshots')
def snapshots():
    """Commands for snapshots"""

@snapshots.command('list')
@click.option('--project', default=None,
    help="Only volumes for project (tag Project:<name>)")
@click.option('--all', 'list_all', default=False, is_flag=True,
    help="List all snapshots for each volume, not just the most recent")
def list_snapshots(project, list_all):
    "List ec2 snapshots"

    instances = filter_instances(project)

    for i in instances:
        for v in i.volumes.all():
            for s in v.snapshots.all():
                print(", ".join((
                    s.id,
                    v.id,
                    i.id,
                    s.state,
                    s.progress,
                    s.start_time.strftime("%c")
                )))
                if s.state == 'completed' and not list_all: break
    return


@cli.group('volumes')
def volumes():
    """Commands for volumes"""

@volumes.command('list')
@click.option('--project', default=None,
    help="Only volumes for project (tag Project:<name>)")
@click.option('--instance', default=None,
    help="Use --instance to reboot a single")
def list_volumes(project, instance):
    "List ec2 volumes"

    instances = filter_instances(project)

    if instance:
        for v in ec2.Instance(instance).volumes.all():
            print(", ".join((
                v.id,
                v.state,
                str(v.size) + "GiB",
                v.encrypted and "Encrypted" or "Not Encrypted"
            )))
        return

    for i in instances:
        for v in i.volumes.all():
            print(", ".join((
                v.id,
                i.id,
                v.state,
                str(v.size) + "GiB",
                v.encrypted and "Encrypted" or "Not Encrypted"
            )))
    return

@cli.group('instances')
def instances():
    """Commands for instances"""

@instances.command('snapshot',
    help="Create snapshots of all volumes")
@click.option('--project', default=None,
    help="Only instances for project (tag Project:<name>)")
@click.option('--force', default=False, is_flag=True,
    help="Use --force to stop instances without the project name")
def list_instances(project, force):
    "Create snapshots for EC2 instances"

    instances = filter_instances(project)

    if project or force:
        for i in instances:
            state = i.state['Name']

            try:
                if state == "running":
                    print("Stopping {0}...".format(i.id))

                    i.stop()
                    i.wait_until_stopped()
                else:
                    continue

                for v in i.volumes.all():
                    if has_pending_snapshot(v):
                        print(" Skipping {0}, snapshot already in progress".format(v.id))
                        continue
                    print("Creating snapshot of instance {0}, volume {1}".format(i.id, v.id))
                    v.create_snapshot(Description="Created by SnapshotAutoCreator")
                
                if state == "running":
                    print("Starting {0}...".format(i.id))

                    i.start()
                    i.wait_until_running()
                else:
                    continue
            
            except botocore.exceptions.ClientError as e:
                print(" Could not snapshot {0}. ".format(i.id) + str(e))
                continue

        print("Job's done")

        return

    else:
        print("Error: Cannot stop instances without either the --project or --force flag")
        return 1

@instances.command('list',
    help="List instances")
@click.option('--project', default=None,
    help="Only instances for project (tag Project:<name>)")
def list_instances(project):
    "List ec2 instances"

    instances = filter_instances(project)

    for i in instances:
        tags = { t['Key']: t['Value'] for t in i.tags or [] }
        print(', '.join((
            i.id,
            i.instance_type,
            i.placement['AvailabilityZone'],
            i.state['Name'],
            i.public_dns_name,
            tags.get('Project', '<no project>')
            )))

    return

@instances.command('stop')
@click.option('--project', default=None,
    help="Only instances for project (tag Project:<name>)")
@click.option('--force', default=False, is_flag=True,
    help="Use --force to stop instances without the project name")
@click.option('--instance', default=None,
    help="Use --instance to reboot a single")
def list_instances(project, force, instance):
    "Stop ec2 instances"

    if instance:
        print(f"Stopping {instance}...")
        ec2.Instance(instance).stop()
        return

    instances = filter_instances(project)
    
    if project or force:
        for i in instances:
            print("Stopping {0}...".format(i.id))
            try:
                i.stop()
            except botocore.exceptions.ClientError as e:
                print(" Could not stop {0}. ".format(i.id) + str(e))
                continue
        return
    else:
        print("Error: Cannot stop instances without either the --project or --force flag")
        return 1

@instances.command('start')
@click.option('--project', default=None,
    help="Only instances for project (tag Project:<name>)")
@click.option('--force', default=False, is_flag=True,
    help="Use --force to stop instances without the project name")
@click.option('--instance', default=None,
    help="Use --instance to reboot a single")
def list_instances(project, force, instance):
    "Start ec2 instances"

    if instance:
        print(f"Starting {instance}...")
        ec2.Instance(instance).start()
    
        return

    instances = filter_instances(project)

    if project or force:
        for i in instances:
            print("Starting {0}...".format(i.id))
            try:
                i.start()
            except botocore.exceptions.ClientError as e:
                print(" Could not start {0}. ".format(i.id) + str(e))
                continue
        return
    else:
        print("Error: Cannot stop instances without either the --project or --force flag")
        return 1

@instances.command('reboot')
@click.option('--project', default=None,
    help="Only instances for project (tag Project:<name>)")
@click.option('--force', default=False, is_flag=True,
    help="Use --force to reboot instances without the project name")
@click.option('--instance', default=None,
    help="Use --instance to reboot a single")
def list_instances(project, force, instance):
    "Reboot ec2 instances"

    if instance:
        print(f"Rebooting {instance}...")
        ec2.Instance(instance).reboot()
        
        return

    instances = filter_instances(project)

    if project or force:
        for i in instances:
            print("Rebooting {0}...".format(i.id))
            try:
                i.reboot()
            except botocore.exceptions.ClientError as e:
                print(" Could not reboot {0}. ".format(i.id) + str(e))
                continue
        return
    else:
        print("Error: Cannot stop instances without either the --project or --force flag")
        return 1

if __name__ == '__main__':
    cli()
