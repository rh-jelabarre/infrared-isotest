import ConfigParser
import os
import yaml

import clg
import yamlordereddictloader

from cli import exceptions
from cli import utils


def load_config_file():
    """Load config file order(ENV, CWD, USER HOME, SYSTEM).

    :return ConfigParser: config object
    """

    # create a parser with default path to InfraRed's main dir
    cwd_path = os.path.join(os.getcwd(), utils.IR_CONF_FILE)
    _config = ConfigParser.ConfigParser()

    env_path = os.getenv(utils.ENV_VAR_NAME, None)
    if env_path is not None:
        env_path = os.path.expanduser(env_path)
        if os.path.isdir(env_path):
            env_path = os.path.join(env_path, utils.IR_CONF_FILE)

    for path in (env_path, cwd_path, utils.USER_PATH, utils.SYSTEM_PATH):
        if path is not None and os.path.exists(path):
            _config.read(path)
            return _config

    conf_file_paths = "\n".join([cwd_path, utils.USER_PATH, utils.SYSTEM_PATH])
    raise exceptions.IRFileNotFoundException(
        conf_file_paths,
        "IR configuration not found. "
        "Please set it in one of the following paths:\n")


def IniFileType(value):
    """
    The custom type for clg spec
    :param value: the argument value.
    :return: dict based on a provided ini file.
    """
    _config = ConfigParser.ConfigParser()
    _config.read(value)

    d = dict(_config._sections)
    for k in d:
        d[k] = dict(_config._defaults, **d[k])
        for key, value in d[k].iteritems():
            # check if we have lists
            if value.startswith('[') and value.endswith(']'):
                value = value[1:-1].split(',')
            d[k][key] = value
        d[k].pop('__name__', None)

    return d


class SpecManager(object):
    """
    Holds everything related to specs.
    """

    SPEC_EXTENSION = '.spec'

    @classmethod
    def parse_args(cls, module_name, config, args=None):
        """
        Looks for all the specs for specified module
        and parses the commandline input arguments accordingly.

        :param module_name: the module name: installer|provisioner|tester
        """
        cmd = clg.CommandLine(cls._get_specs(module_name, config))
        res_args = cmd.parse(args)

        # override the command specific arguments from file
        if 'from-file' in res_args:
            file_args = res_args['from-file']
            if res_args['command0'] in file_args:
                utils.dict_merge(res_args, file_args[res_args['command0']])

        # todo(obaranov) try to resolve 'None' arguments from environment.
        return res_args

    @classmethod
    def _get_specs(cls, module_name, config):
        """
        Gets specs files as a dict from settings/<module_name> folder.
        :param module_name: the module name: installer|provisioner|tester
        """
        res = {}
        for spec_file in cls._get_all_specs(config, subfolder=module_name):
            spec = yaml.load(open(spec_file),
                             Loader=yamlordereddictloader.Loader)
            utils.dict_merge(res, spec)
        return res

    @classmethod
    def _get_all_specs(cls, config, subfolder=None):
        root_dir = utils.validate_settings_dir(
            config.get('defaults', 'settings'))
        if subfolder:
            root_dir = os.path.join(root_dir, subfolder)

        res = []
        for dirpath, _, filenames in os.walk(root_dir):
            for filename in [f for f in filenames
                             if f.endswith(cls.SPEC_EXTENSION)]:
                res.append(os.path.join(dirpath, filename))

        return res


config = load_config_file()

# update clg types
clg.TYPES.update({'IniFile': IniFileType})
