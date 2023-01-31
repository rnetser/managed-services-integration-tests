import io
import logging

from jinja2 import Environment, FileSystemLoader, TemplateNotFound


LOGGER = logging.getLogger(__name__)


def render_template_from_dict(template_name, _dict, base_templates="templates/"):
    env = Environment(
        loader=FileSystemLoader(base_templates),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    try:
        template = env.get_template(name=template_name)
        return io.StringIO(template.render(_dict))

    except TemplateNotFound:
        LOGGER.error(f"Cannot find template {template_name} under {base_templates}")
        raise
