from ivaldi.shared.collect import collect
from ivaldi.shared.python import install as install_python
from ivaldi.shared.uv import install as install_uv


def Install(settings):

    install_uv(settings)
    install_python(settings)
    collect(settings)
