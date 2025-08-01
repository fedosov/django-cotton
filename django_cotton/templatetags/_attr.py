import re
from django.template import Library
from django.template.base import (
    Node,
    TemplateSyntaxError,
)
from django.utils.safestring import mark_safe

from django_cotton.templatetags import DynamicAttr, UnprocessableDynamicAttr
from django_cotton.utils import get_cotton_data

# Pre-compiled regex pattern for performance optimization
CONDITIONAL_ATTR_PATTERN = re.compile(
    r'([a-zA-Z][a-zA-Z0-9_-]*)(?:\s*=\s*(?:(["\'])((?:[^"\'\\]|\\.)*)?\2|([^\s]+)))?'
)

register = Library()


def cotton_attr(parser, token):
    bits = token.split_contents()[1:]
    if len(bits) < 1:
        raise TemplateSyntaxError("cotton complex-attr must include a 'name'")

    nodelist = parser.parse(("endattr",))
    parser.delete_first_token()
    return ComplexAttrNode(bits[0], nodelist)


class ComplexAttrNode(Node):
    def __init__(self, attr_name, nodelist):
        self.attr_name = attr_name
        self.nodelist = nodelist

    def render(self, context):
        cotton_data = get_cotton_data(context)
        if cotton_data["stack"]:
            content = self.nodelist.render(context)
            if self.attr_name.startswith("_conditional_"):
                # Special handling for conditional attributes
                # Parse the content as attribute declarations and add them to attrs
                self._process_conditional_attributes(content, cotton_data["stack"][-1]["attrs"])
            elif self.attr_name.startswith(":"):
                key = self.attr_name[1:]
                try:
                    cotton_data["stack"][-1]["attrs"][key] = DynamicAttr(content).resolve(context)
                except UnprocessableDynamicAttr:
                    cotton_data["stack"][-1]["attrs"].unprocessable(key)
            else:
                # just template partial
                cotton_data["stack"][-1]["attrs"][self.attr_name] = mark_safe(content)
        return ""

    def _process_conditional_attributes(self, content, attrs_dict):
        """Parse conditional attribute content and add attributes to the component - OPTIMIZED"""
        # Remove leading/trailing whitespace
        content = content.strip()
        if not content:
            return

        # OPTIMIZATION: Use pre-compiled regex pattern instead of compiling each time
        # Pattern matches: key="value" or key='value' or key=value or just key (boolean)
        # Handles attribute names that can contain dashes and other characters
        
        # Find all matches in the content using pre-compiled pattern
        matches = list(CONDITIONAL_ATTR_PATTERN.finditer(content))

        for match in matches:
            key = match.group(1)
            quote = match.group(2)
            quoted_value = match.group(3)
            unquoted_value = match.group(4)

            if quoted_value is not None:
                # Quoted value (handle empty quotes too)
                attrs_dict[key] = quoted_value if quoted_value is not None else ""
            elif unquoted_value is not None:
                # Unquoted value
                attrs_dict[key] = unquoted_value
            else:
                # Boolean attribute (no value)
                attrs_dict[key] = True
