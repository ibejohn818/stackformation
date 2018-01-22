from stackformation.aws.stacks import (BaseStack)


class ENI(object):
    pass


class ENIStack(BaseStack):

    def __init__(self, name=""):

        super(ENIStack, self).__init__("ENI", 400)
        self.stack_name = name
        self.interfaces = []

    def build_template(self):

        t = self._init_template()

        return t
