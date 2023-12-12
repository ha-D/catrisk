#!/usr/bin/env python3

import json
import os
import yaml
import subprocess
from os import path



def get_model_services(model_dir):
    skip = []
    services = {}

    for model in os.listdir(model_dir):
        if not os.path.isdir(os.path.join(model_dir, model)):
            continue

        if model in skip:
            print(f"Model {model} skipped")
            continue

        print(f"Found model {model}")

        with open(path.join(model_dir, model, "meta_data.json")) as f:
            metadata = json.loads(f.read())

        services[f"worker-{model}"] = {
            "restart": "always",
            "image": "coreoasis/model_worker:1.19.0",
            "links": [
                "celery-db",
                "rabbit:myrabbit"
            ],
            "environment": [
                f"OASIS_MODEL_SUPPLIER_ID={metadata.get('supplier_id', 'CatRisk')}",
                f"OASIS_MODEL_ID={metadata.get('model_id', model)}",
                f"OASIS_MODEL_VERSION_ID={metadata.get('version_id', '0.0.1')}",
                "OASIS_RABBIT_HOST=rabbit",
                "OASIS_RABBIT_PORT=5672",
                "OASIS_RABBIT_USER=rabbit",
                "OASIS_RABBIT_PASS=rabbit",
                "OASIS_SERVER_DB_ENGINE=django.db.backends.postgresql_psycopg2",
                "OASIS_CELERY_DB_ENGINE=db+mysql+pymysql",
                "OASIS_CELERY_DB_HOST=celery-db",
                "OASIS_CELERY_DB_PASS=password",
                "OASIS_CELERY_DB_USER=celery",
                "OASIS_CELERY_DB_NAME=celery",
                "OASIS_CELERY_DB_PORT=5432",
                "OASIS_MODEL_DATA_DIRECTORY=/home/worker/model",
            ],
            "volumes": [
                f"./{model_dir}/{model}/:/home/worker/model",
                "filestore-OasisData:/shared-fs:rw",
                "./data/output:/home/worker/output"
            ]
        }

    return services


def merge(a, b, path=None):
    if path is None: path = []
    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                merge(a[key], b[key], path + [str(key)])
            elif a[key] == b[key]:
                pass # same leaf value
            else:
                print(a[key])
                print()
                print( b[key])
                raise Exception('Conflict at %s' % '.'.join(path + [str(key)]))
        else:
            a[key] = b[key]
    return a

def create_compose(docker_dir, model_dir):
    config = {}
    services = get_model_services(model_dir)

    with open(path.join(docker_dir, 'oasis-platform.yml')) as f:
        config = merge(config, yaml.safe_load(f.read()))

    with open(path.join(docker_dir, 'oasis-ui.yml')) as f:
        config = merge(config, yaml.safe_load(f.read()))

    with open(path.join(docker_dir, 'system.yml')) as f:
        config = merge(config, yaml.safe_load(f.read()))

    config = merge(config, {"services": services})

    print("\nWriting config")
    with open("docker-compose.yml", "w") as f:
        f.write(yaml.dump(config))


def run_services(docker_dir, model_dir):
    create_compose(docker_dir, model_dir)

    subprocess.run(["docker-compose", "restart"])
    subprocess.run(["docker-compose", "up", "--remove-orphans", "-d"])

