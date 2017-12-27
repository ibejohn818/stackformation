import jinja2
import re


def jinja_env(context, capture_vars=False):

    var_capture = []

    def _handle_context(var):
        if capture_vars:
            var_capture.append(var)
        else:
            if context.check_var(var):
                return context.get_var(var)
            raise Exception("Context Error: Output Missing ({})".format(var))

    env = jinja2.Environment(loader=jinja2.FileSystemLoader(searchpath="."))

    env.globals['context'] = _handle_context

    return env, var_capture


def match_stack(selector, stack):
    """Match stacks using selector as the comparison var.
    Strings prefixed with ^ will be treated as negative

    Args:
        selector (str|list[str]): String tokens or list used for matching
        stack (:obj:`stackformation.BaseStack`): stack used for comparison. Will match on get_stack_name() and get_remote_stack_name()

    Returns:
        :obj:`stackformation.BaseStack`: If stack matches
        bool: False if selector did not match
    """
    if not isinstance(selector, list):
        selector = selector.split(' ')

    pos = []
    neg = []
    sn = stack.get_stack_name()
    rn = stack.get_remote_stack_name()
    result = False

    for s in selector:
        if s[0] == "^":
            neg.append(s[1:])
        else:
            pos.append(s)

    for s in pos:
        if re.search(s, sn) or re.search(s, rn):
            result = True

    for s in neg:
        if re.search(s, sn) or re.search(s, rn):
            result = False

    return result
