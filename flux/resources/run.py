from mesh.standard import *
from scheme import *

from flux.constants import *

class Run(Resource):
    """A workflow run."""

    name = 'run'
    version = 1

    class schema:
        id = UUID(operators='equal')
        workflow_id = UUID(nonempty=True, operators='equal')
        name = Text(operators='equal')
        status = Enumeration(RUN_STATUSES, oncreate=False)
        parameters = Field(onupdate=False)
        started = DateTime(utc=True, readonly=True)
        ended = DateTime(utc=True, readonly=True)
        executions = Sequence(Structure({
            'id': UUID(nonempty=True),
            'execution_id': Integer(),
            'ancestor_id': UUID(),
            'step': Token(segments=2),
            'name': Text(),
            'status': Enumeration(RUN_STATUSES, nonnull=True),
            'started': DateTime(),
            'ended': DateTime(),
        }), readonly=True, deferred=True)

    class task:
        endpoint = ('TASK', 'run')
        title = 'Initiating a run task'
        schema = Structure(
            structure={
                'initiate-run': {
                    'id': UUID(nonempty=True),
                },
            },
            nonempty=True,
            polymorphic_on=Enumeration(['initiate-run'],
                name='task', nonempty=True))
        responses = {
            OK: Response(),
            INVALID: Response(Errors),
        }
