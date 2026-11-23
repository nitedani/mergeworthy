"""The plugin's options as hooks and scripts read them."""
import os


def setting(name, default=''):
    """MERGEWORTHY_<name> from the environment, else from ~/.mergeworthy/settings.env (written at session start from the plugin's options)."""
    f = os.path.expanduser('~/.mergeworthy/settings.env')
    saved = dict(l.strip().split('=', 1) for l in open(f) if '=' in l) if os.path.exists(f) else {}
    return os.environ.get(f'MERGEWORTHY_{name}') or saved.get(f'MERGEWORTHY_{name}', default)
