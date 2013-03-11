from scheme import *
from spire.schema import NoResultFound
from spire.support.logs import LogHelper

from flux.engine.interpolation import Interpolator
from flux.engine.rule import Environment, RuleList
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
        operation = session.query(Operation).get(self.operation)
        if not operation:
            log('error', 'workflow operation %s is not registered', self.operation)
            run.complete(session, 'failed')
            session.commit()
            return

        params = {}
        if self.parameters:
            params.update(self.parameters)
        if parameters:
            params.update(parameters)

        if params:
            interpolator = self._construct_interpolator(run)
            params = interpolator.interpolate(operation.schema, params)
        else:
            params = None

        execution = run.create_execution(session, self.name, params, ancestor)
        operation.initiate(id=execution.id, tag=self.name, input=params, timeout=self.timeout)
        session.commit()

    def complete(self, session, execution, workflow, output):
        from flux.models import Run
        run = Run.load(session, id=execution.run_id, lockmode='update')

        status = execution.status
        if status != 'completed':
            if status in ('failed', 'timedout'):
                run.complete(session, status)
            return

        environment = Environment(workflow, run, output, execution)

        postoperation = self.postoperation
        if postoperation:
            postoperation.evaluate(session, environment)
            return

        run.complete(session, 'completed')

    def _construct_interpolator(self, run):
        interpolator = Interpolator()
        run.contribute(interpolator)
        return interpolator

