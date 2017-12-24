import re


def match_stack(selector, stack):

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


class Deploy(object):
    """

    """
    def cli_confirm(self, infra, selector=[]):

        c = 0

        for stack in infra.get_stacks():
            if len(selector)>0 and not match_stack(selector, stack):
                continue
            c += 1
            print("Stack: {}/{}".format(stack.get_stack_name(),stack.get_remote_stack_name()))

        if c<=0:
            print("NO STACKS SELCTED!")
            return False

        ans = input("Deploy stacks?: [y/n] \n")

        if ans.lower().startswith("y"):
            return True

        return False


class SerialDeploy(Deploy):
    pass


class DeployStacks(Deploy):

    def __init__(self):
        pass

    def fill_params(self, params, context):

        p = []

        for k, v in params.items():
            val = context.get_var(k)
            if not val:
                val = None
            p.append({
                'ParameterKey': k,
                'ParameterValue': val
            })
        return p

    def test_match(self, infra):

        stacks = infra.get_stacks()

        sel = "vpc !dev"
        sel = "prod-jch-vpc"

        for s in stacks:
            print(s.get_stack_name())
            print(s.get_remote_stack_name())
            res = match_stack(sel, s)
            print(res)


    def deploy_stacks(self, infra, selector=False):

        stacks = infra.get_stacks()

        for s in stacks:
            if selector and not match_stack(selector, s):
                continue;

            print(s.start_deploy(infra))


