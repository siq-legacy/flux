from mesh.standard import OperationError, bind
from scheme import current_timestamp
from spire.schema import *
from spire.support.logs import LogHelper

from flux.bindings import platoon
from flux.constants import *
from flux.models.execution import WorkflowExecution
from flux.models.workflow import Workflow

__all__ = ('Run',)

Event = bind(platoon, 'platoon/1.0/event')

schema = Schema('flux')
log = LogHelper('flux')

class Run(Model):
    """A workflow run."""

    class meta:
        schema = schema
        tablename = 'run'

    id = Identifier()
    workflow_id = ForeignKey('workflow.id', nullable=False)
    name = Text(nullable=False)
    status = Enumeration(RUN_STATUSES, nullable=False, default='pending')
    parameters = Json()
    started = DateTime(timezone=True)
    ended = DateTime(timezone=True)

    executions = relationship(WorkflowExecution, backref='run',
        cascade='all,delete-orphan', passive_deletes=True,
        order_by=WorkflowExecution.execution_id)

    def __repr__(self):
        return 'Run(id=%r, name=%r, status=%r)' % (self.id, self.name, self.status)

    @property
    def next_execution_id(self):
        return len(self.executions) + 1

    def complete(self, session, status):
        self.status = status
        self.ended = current_timestamp()

        try:
            Event.create(topic='run:changed', aspects={'id': self.id})
        except Exception:
            log('exception', 'failed to file run:changed event')

    def contribute_values(self):
        run = {'id': self.id, 'name': self.name, 'started': self.started}
        if self.parameters:
            run['env'] = self.parameters
        else:
            run['env'] = {}
        return {'run': run}

    @classmethod
    def create(cls, session, workflow_id, name=None, **attrs):
        try:
            workflow = Workflow.load(session, id=workflow_id)
        except NoResultFound:
            raise OperationError('unknown-workflow')

        if not name:
            name = workflow.name

        run = cls(name=name, workflow_id=workflow.id, **attrs)
        session.add(run)
        return run

    def create_execution(self, session, step, parameters=None, ancestor=None, name=None):
        return WorkflowExecution.create(session, run_id=self.id, execution_id=self.next_execution_id,
            ancestor=ancestor, step=step, name=name, parameters=parameters)

    def initiate(self, session):
        self.started = current_timestamp()
        self.workflow.workflow.initiate(session, self)
