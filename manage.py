#!/usr/bin/env python3

import click
import yaml
import settings

@click.group()
def cli():
    pass

@cli.command()
def install():
    from scripts.install import run_services

    click.echo("Installing Oasis...")
    run_services(docker_dir=settings.docker_dir, model_dir=settings.model_dir)

@cli.command()
def compose():
    from scripts.install import create_compose

    click.echo("Creating compose file...")
    create_compose(docker_dir=settings.docker_dir, model_dir=settings.model_dir)

@cli.command()
def download():
    from scripts.download import download_models
    
    download_models(
        storage_account_name=settings.storage_account_name,
        storage_account_key=settings.storage_account_key,
        storage_container_name=settings.storage_container_name,
        local_download_path=settings.model_dir
    )

if __name__ == "__main__":
    cli()