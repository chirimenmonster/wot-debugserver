import os
import shutil
import py_compile
import zipfile
import ConfigParser
import json
from string import Template

BUILD_DIR = 'build'
CONFIG = 'config.ini'
FILE_LIST = 'files.json'
RELEASE_LIST = 'release.json'

def get_config():
    inifile = ConfigParser.SafeConfigParser()
    inifile.read(CONFIG)

    parameters = dict(inifile.items('mod'))
    for section in inifile.sections():
        for k, v in inifile.items(section):
            parameters[section + '_' + k] = v
    return parameters


def compile_python(src, dst, virtualdir):
    try:
        os.makedirs(os.path.dirname(dst))
    except:
        pass
    py_compile.compile(file=src, cfile=dst, dfile=os.path.join(virtualdir, os.path.basename(src)), doraise=True)

def apply_template(src, dst, parameters):
    try:
        os.makedirs(os.path.dirname(dst))
    except:
        pass
    with open(src, 'r') as in_file, open(dst, 'w') as out_file:
        out_file.write(Template(in_file.read()).substitute(parameters))

def split(path):
    head, tail = os.path.split(path)
    if not head:
        return [ tail ]
    result = split(head)
    result.append(path)
    return result

def process_filelist(parameters, desc):
    paths = []
    for target in desc:
        if target['method'] == 'apply+python':
            for src in target['files']:
                root, ext = os.path.splitext(src)
                dst = root + '.pyc'
                prepared = os.path.join(BUILD_DIR, src)
                cooked = os.path.join(BUILD_DIR, dst)
                release = os.path.join(target['root'], target['reldir'], os.path.basename(dst))
                apply_template(src, prepared, parameters)
                compile_python(prepared, cooked, target['reldir'])
                paths.append([ cooked, release ])
        elif target['method'] == 'python':
            for src in target['files']:
                root, ext = os.path.splitext(src)
                dst = root + '.pyc'
                cooked = os.path.join(BUILD_DIR, dst)
                release = os.path.join(target['root'], target['reldir'], os.path.basename(dst))
                compile_python(src, cooked, target['reldir'])
                paths.append([ cooked, release])
        elif target['method'] == 'apply':
            for src in target['files']:
                cooked = os.path.join(BUILD_DIR, src)
                release = os.path.join(target['root'], target['reldir'], os.path.basename(src))
                apply_template(src, cooked, parameters)
                paths.append([ cooked, release ])
        elif target['method'] == 'plain':
            for src in target['files']:
                cooked = src
                release = os.path.join(target['root'], target['reldir'], os.path.basename(src))
                paths.append([ cooked, release ])
    return paths


def create_zipfile(package, paths, compression=zipfile.ZIP_DEFLATED):
    donelist = []
    with zipfile.ZipFile(package, 'w', compression=compression) as file:
        for source, target in paths:
            for dir in split(target)[0:-1]:
                if dir not in donelist:
                    file.write('.', dir, compression)
                    donelist.append(dir)
            file.write(source, target, compression)
            donelist.append(target)


def create_wotmod(jsonfile, params):
    with open(jsonfile, 'r') as f:
        desc = json.loads(Template(f.read()).substitute(params))
    paths = process_filelist(params, desc['files'])
    package = os.path.join(BUILD_DIR, params['package'])
    create_zipfile(package, paths, zipfile.ZIP_STORED)


def create_release(jsonfile, params):
    with open(jsonfile, 'r') as f:
        desc = json.loads(Template(f.read()).substitute(params))
    paths = process_filelist(params, desc['files'])
    package = os.path.join(BUILD_DIR, desc['package'])
    create_zipfile(package, paths, zipfile.ZIP_DEFLATED)


def main():
    params = get_config()
    try:
        shutil.rmtree(BUILD_DIR)
    except:
        pass
    os.makedirs(BUILD_DIR)

    create_wotmod(FILE_LIST, params)

    if os.path.exists(RELEASE_LIST):
        create_release(RELEASE_LIST, params)


if __name__ == "__main__":
    main()
