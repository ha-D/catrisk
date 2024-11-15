#!/usr/bin/env python3

import json
import os
from os import path

import yaml


def get_model_services(config, shared_envs):
    skip = []
    services = {}

    model_dir = config["model_dir"]

    for model in os.listdir(model_dir):
        if not os.path.isdir(os.path.join(model_dir, model)):
            continue

        if model in skip:
            print(f"Model {model} skipped")
            continue

        try:
            with open(path.join(model_dir, model, "meta_data.json")) as f:
                metadata = json.loads(f.read())
        except FileNotFoundError:
            continue

        print(f"Found model {model}")

        if config.get("worker_requires_root", False):
            root_hack = "\nUSER root\nRUN ln -s /home/worker/.local /root/.local"
        else:
            root_hack = ""

        for v in ["v1", "v2"]:
            services[f"worker-{model.lower()}-{v}"] = {
                "restart": "always",
                "build": {
                    "context": ".",
                    "dockerfile_inline": f"""FROM {config['worker_img']}:{config['worker_version']}{root_hack}\nRUN pip3 install --break-system-packages msoffcrypto-tool openpyxl""",
                },
                "links": ["celery-db", "broker:mybroker"],
                "environment": {
                    **shared_envs,
                    "OASIS_MODEL_SUPPLIER_ID": metadata.get('supplier_id', 'CatRisk'),
                    "OASIS_MODEL_ID": metadata.get('model_id', model),
                    "OASIS_MODEL_VERSION_ID": metadata.get('version_id', '0.0.1'),
                    "OASIS_RUN_MODE": v, 
                    "OASIS_MODEL_DATA_DIRECTORY": "/home/worker/model",
                },
                "volumes": [
                    f"./{model_dir}/{model}/:/home/worker/model",
                    "filestore-OasisData:/shared-fs:rw",
                    "./data/output:/home/worker/output",
                ],
            }

    return services


def merge(a, b, path=None):
    if path is None:
        path = []
    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                merge(a[key], b[key], path + [str(key)])
            elif a[key] == b[key]:
                pass  # same leaf value
            else:
                print(a[key])
                print()
                print(b[key])
                raise Exception("Conflict at %s" % ".".join(path + [str(key)]))
        else:
            a[key] = b[key]
    return a


def replace_vars(template, config):
    from string import Template

    return Template(template).safe_substitute(config)


def compose(config):
    docker_dir = config["docker_dir"]

    with open(os.path.join(docker_dir, "oasis-platform.yml")) as f:
        shared_envs = yaml.safe_load(f)["x-shared-env"]

    merged_compose = {}
    services = get_model_services(config, shared_envs)

    for filename in os.listdir(docker_dir):
        if not filename.endswith(".yml"):
            continue
        with open(path.join(docker_dir, filename)) as f:
            config_yaml = replace_vars(f.read(), config)
            merged_compose = merge(merged_compose, yaml.safe_load(config_yaml))

    merged_compose = merge(merged_compose, {"services": services})

    def str_presenter(dumper, data):
        """configures yaml for dumping multiline strings
        Ref: https://stackoverflow.com/questions/8640959/how-can-i-control-what-scalar-form-pyyaml-uses-for-my-data
        """
        if data.count("\n") > 0:  # check for multiline string
            return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
        return dumper.represent_scalar("tag:yaml.org,2002:str", data)

    yaml.add_representer(str, str_presenter)
    yaml.representer.SafeRepresenter.add_representer(
        str, str_presenter
    )  # to use with safe_dum

    print("\nWriting config")
    with open("docker-compose.yml", "w") as f:
        f.write(yaml.dump(merged_compose, indent=2, default_flow_style=False))
