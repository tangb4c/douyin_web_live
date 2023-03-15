import os
from pathlib import Path
from ruamel import yaml


def config():
    settings_file = str(Path(__file__).parent.absolute()) + '/settings.yml'

    with open(settings_file, 'r') as f:
        return yaml.load(f, Loader=yaml.UnsafeLoader)


def getConfig(key: str):
    items = key.split('.')
    cc = config()
    for x in items:
        if x not in cc:
            raise NameError(f"{key} 配置项不存在，请检查配置")
        cc = cc.get(x)
    return cc


def getPath(yaml_path: str, create_if_not_exist: bool = False):
    dst = os.path.expanduser(getConfig(yaml_path)).strip()
    if create_if_not_exist:
        os.makedirs(dst, exist_ok=True)
    return dst

