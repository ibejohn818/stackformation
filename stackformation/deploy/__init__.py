import re
import time
import logging
from stackformation.utils import (match_stack)
from colorama import Fore, Back, Style


logger = logging.getLogger(__name__)

class Deploy(object):
    """
        Base deploy class
    """
    def cli_confirm(self, infra, selector=[]):

        c = 0

        for stack in infra.get_stacks():
            if len(selector)>0 and not match_stack(selector, stack):
                continue
            c += 1
            print("Stack: {}{}/{}{}".format(
                    Fore.CYAN+Style.BRIGHT,
                    stack.get_stack_name(),
                    stack.get_remote_stack_name(),
                    Style.RESET_ALL
                    ))

        if c<=0:
            print("NO STACKS SELCTED!")
            return False

        ans = input("Deploy stacks?: [y/n] \n".format())

        if ans.lower().startswith("y"):
            return True

        return False


class SerialDeploy(Deploy):
    """
    Sequential deployment
    """
    def deploy(self, infra, selector=False):

        stacks = infra.get_stacks()

        for stack in stacks:
            if selector and not match_stack(selector, stack):
                continue;

            dependent_stacks = infra.get_dependent_stacks(stack)

            for k, stk in dependent_stacks.items():
                stk.load_stack_outputs(stack.infra)

            start = stack.start_deploy(infra, stack.infra.context)
            time.sleep(2)

            while stack.deploying(infra):
                pass
            logger.info("DEPLOY COMPLETE: {}".format(stack.get_stack_name()))


