from scheme import *
from spire.schema import NoResultFound
from spire.support.logs import LogHelper

from flux.engine.rule import RuleList
from flux.models import Operation

log = LogHelper('flux')

class Step(Element):
    """A workflow element."""

    key_attr = 'name'
    schema = Structure({
        'description': Text(),
        'operation': Token(nonempty=True),
        'parameters': Map(Field(), nonnull=True),
        'preoperation': RuleList.schema,
        'postoperation': RuleList.schema,
        'timeout': Integer(),
    }, nonnull=True)

    def initiate(self, session, run, parameters=None, ancestor=None):
        params = {}
        if self.parameters:
            params.update(self.parameters)
        if parameters:
            params.update(parameters)
        if not params:
            params = None

        try:
            operation = session.query(Operation).get(self.operation)
        except NoResultFound:
            raise Exception('FIX ME')

        candidates = {}
        if run.parameters:
            for key, value in run.parameters.iteritems():
                candidates['$%s' % key] = value

        if params and candidates:
            params = operation.schema.interpolate(params, candidates)

        execution = run.create_execution(session, self.name, params, ancestor)
        session.commit()

        operation.initiate(id=execution.id, tag=self.name, input=params, timeout=self.timeout)

    def complete(self, session, execution, workflow, output):
        from flux.models import Run
        run = Run.load(session, id=execution.run_id, lockmode='update')

        status = execution.status
        if status != 'completed':
            if status in ('failed', 'timedout',):
                run.status = status
            return 

        postoperation = self.postoperation
        if not postoperation:
            # finish workflow
            return

        action = postoperation.rules[0].actions[0]
        step = workflow.steps[action.step]

        try:
            operation = session.query(Operation).get(step.operation)
        except NoResultFound:
            raise Exception('FIX ME')

        candidates = {}
        if output:
            for key, value in output.iteritems():
                candidates['$%s' % key] = value

        params = action.parameters
        if params and candidates:
            params = operation.schema.interpolate(params, candidates)

        print params

        step.initiate(session, run, params, execution)
