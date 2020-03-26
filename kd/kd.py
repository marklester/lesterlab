#!/usr/bin/python3

from mako.template import Template
from mako.lookup import TemplateLookup
import click
import os
import yaml
import subprocess

def create_mako_template(file):
    cwd = os.path.dirname(os.path.abspath(__file__))
    mylookup = TemplateLookup(directories=[cwd])
    template = Template(filename=file,lookup=mylookup)
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
    template = create_mako_template(file)
    click.echo(template.render())

if __name__ == "__main__":
    cli.add_command(print)
    cli.add_command(apply)
    cli()