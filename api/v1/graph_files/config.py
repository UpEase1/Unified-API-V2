from configparser import ConfigParser

def read_azure_config():
    config = ConfigParser()
    config.read('config.dev.cfg')
    return config['azure']

