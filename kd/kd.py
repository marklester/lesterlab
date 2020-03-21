#!/usr/bin/python3

from jinja2 import Environment, FileSystemLoader
import click
import os
import yaml
import subprocess

def create_template(file):
    parts = os.path.split(file);
    file_loader = FileSystemLoader(parts[0])
    env = Environment(loader=file_loader)
    template = env.get_template(parts[1])
    return template

@click.group()
def cli():
  pass

@click.command()
@click.argument('file',"file")
def apply(file):
    config.load_kube_config()
    template = create_template(file)
    crd = yaml.load_all(template.render())
    # p = subprocess.Popen('kubectl apply 0f - ', shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    # for line in p.stdout.readlines():
    # print line,
    # retval = p.wait()
@click.command()
@click.argument('file',"file")
def print(file):
    template = create_template(file)
    click.echo(template.render())


if __name__ == "__main__":
    cli.add_command(print)
    cli.add_command(apply)
    cli()