import jinja2




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

