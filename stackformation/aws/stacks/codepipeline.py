from stackformation.aws.stacks import (BaseStack)
import troposphere.codepipeline as cpl  # noqa
from troposphere import (  # noqa
    FindInMap, GetAtt, Join,
    Parameter, Output, Ref,
    Select, Tags, Template,
    GetAZs, Export, Base64
)


class CodePipelineStack(BaseStack):

    def __init__(self, name):

        self.stack_name = name
        super(CodePipelineStack, self).__init__("CodePipeline", 800)

    def build_template(self):

        t = self._init_template()

        return t
