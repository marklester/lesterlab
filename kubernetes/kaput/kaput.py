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
@click.argument('file')
def apply(file):
    template = create_mako_template(file)
    raster = template.render()
    result = subprocess.run(["kubectl","apply","-f","-"],stdout=subprocess.PIPE,input=raster.encode())
    click.echo(result.stdout)

@click.command()
@click.argument('file')
def diff(file):
    green = '\033[92m'
    red = '\033[31m'
    end = '\033[0m'

    template = create_mako_template(file)
    raster = template.render()
    result = subprocess.run(["kubectl","diff","-f","-"],stdout=subprocess.PIPE,stderr=subprocess.PIPE,input=raster.encode())
    for line in result.stdout.decode().splitlines():
        if line.startswith("+"):
            click.echo(f"{green}{line}{end}")
        elif line.startswith("-"):
            click.echo(f"{red}{line}{end}")
        else:
            click.echo(line)
@click.command()
@click.argument('file')
def print(file):
    template = create_mako_template(file)
    click.echo(template.render())

if __name__ == "__main__":
    cli.add_command(print)
    cli.add_command(apply)
    cli.add_command(diff)
    cli()