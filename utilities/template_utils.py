import io
import logging

from jinja2 import Environment, FileSystemLoader, TemplateNotFound


LOGGER = logging.getLogger(__name__)


def render_yaml_from_dict(template, _dict):
    return io.StringIO(template.render(_dict))


def get_resource_j2_template(template_name, base_templates="templates/"):
    env = Environment(
        loader=FileSystemLoader(base_templates),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    try:
        return env.get_template(name=template_name)
    except TemplateNotFound:
        LOGGER.error(f"Cannot find template {template_name} under {base_templates}")
        raise
