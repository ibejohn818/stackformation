import time
import logging
from stackformation.utils import (match_stack, _match_stack)
from colorama import Fore, Back, Style  # noqa


logger = logging.getLogger(__name__)


class Deploy(object):
    """
        Base deploy class
    """

    def cli_confirm(self, infra, selector=[], **kwargs):

        c = 0

        defaults = {
            'reverse': False,
            'ask': 'Deploy Stack(s)?'
        }

        defaults.update(kwargs)

        stacks = infra.list_stacks(reverse=defaults['reverse'])

        results = match_stack(selector, stacks)

        for stack in results:
            c += 1
            print("Stack: {}{}/{}{}".format(
                Fore.CYAN + Style.BRIGHT,
                stack.get_stack_name(),
                stack.get_remote_stack_name(),
                Style.RESET_ALL
            ))

        if c <= 0:
            print("NO STACKS SELCTED!")
            return False

        ans = input("{} [y/n]: \n".format(defaults['ask']))

        if ans.lower().startswith("y"):
            return True

        return False

    def destroy(self, infra, selector=False, **kw):


        stacks = infra.list_stacks(reverse=True)

        stacks = match_stack(selector, stacks)

        for stack in stacks:

            try:
                start = stack.start_destroy(infra, stack.infra.context)
                if not start:
                    print("{} Skipping destroy..".format(stack.get_stack_name()))
            except Exception as e:
                print(str(e))
                continue
            time.sleep(2)
            while stack.deploying(infra):
                pass
            logger.info("DESTROY COMPLETE: {}".format(stack.get_stack_name()))

    def __destroy(self, infra, selector=False, **kwargs):

        stacks = infra.list_stacks(reverse=True)

        for stack in stacks:
            if selector and not _match_stack(selector, stack):
                continue

            start = stack.start_destroy(infra, stack.infra.context)
            if not start:
                continue
            time.sleep(2)
            while stack.deploying(infra):
                pass
            logger.info("DESTROY COMPLETE: {}".format(stack.get_stack_name()))


class SerialDeploy(Deploy):
    """
    Sequential deployment
    """

    def deploy(self, infra, selector=False):

        stacks = infra.get_stacks()

        stacks = match_stack(selector, stacks)

        for stack in stacks:

            dependent_stacks = infra.get_dependent_stacks(stack)

            for k, stk in dependent_stacks.items():
                stk.load_stack_outputs(stack.infra)

            start = stack.start_deploy(infra, stack.infra.context)
            if not start:
                print("{} Skipping deploy..".format(stack.get_stack_name()))
            time.sleep(2)

            while stack.deploying(infra):
                pass
            logger.info("DEPLOY COMPLETE: {}".format(stack.get_stack_name()))
