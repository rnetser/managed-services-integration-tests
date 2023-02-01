import io
import logging

from jinja2 import Environment, FileSystemLoader, TemplateNotFound


LOGGER = logging.getLogger(__name__)


def render_template_from_dict(
    template_name, template_dict, base_templates="templates/"
):
    """
    This function can be used to render a yaml content from a jinja2 template file
    given as template_name and to be populated with a dict of corresponding variables
    given as template_dict.
    """
    env = Environment(
        loader=FileSystemLoader(base_templates),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    try:
        template = env.get_template(name=template_name)
        return io.StringIO(template.render(template_dict))

    except TemplateNotFound:
        LOGGER.error(f"Cannot find template {template_name} under {base_templates}")
        raise
