from spire.mesh import ModelController
from spire.schema import SchemaDependency

from flux.models import *
from flux.resources import Workflow as WorkflowResource
from flux.engine.workflow import Workflow as WorkflowEngine

class WorkflowController(ModelController):
    resource = WorkflowResource
    version = (1, 0)

    model = Workflow
    mapping = 'id name designation specification modified'
    schema = SchemaDependency('flux')

    def generate(self, request, response, subject, data):
        name = data['name']
        operations = data['operations']
        specification = {'name': name, 'entry': 'step:0'}
        steps = {}

        step_name = None
        for i, op in enumerate(operations):
            new_step_name = 'step:%s' % i
            step = {
                'operation': op['operation'],
                'parameters': op['parameters'],
                'postoperation': [{
                    'condition': {},
                    'actions': [],
                    'terminal': True,
                }],
            }
            if step_name:
                steps[step_name]['postoperation'][0]['actions'].append({
                    'action': 'execute-step',
                    'step': new_step_name,
                    'parameters': step['parameters']
                })

            step_name = new_step_name
            steps[step_name] = step

        specification['steps'] = steps
        specification = WorkflowEngine.schema.serialize(specification,
                format='yaml')

        response({'name': name, 'specification': specification})
