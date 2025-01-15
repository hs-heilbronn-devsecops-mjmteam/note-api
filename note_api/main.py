# -*- coding: utf-8 -*-
from uuid import uuid4
from typing import List, Optional
from os import getenv
import os
import time
import random
from typing_extensions import Annotated

from fastapi import Depends, FastAPI
from starlette.responses import RedirectResponse
from .backends import Backend, RedisBackend, MemoryBackend, GCSBackend
from .model import Note, CreateNoteRequest

from opentelemetry.sdk.resources import SERVICE_INSTANCE_ID, SERVICE_NAME, Resource

from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter

app = FastAPI()

my_backend: Optional[Backend] = None

#add unque id to traces
resource = Resource.create(attributes={
    SERVICE_INSTANCE_ID: f"worker-{os.getpid()}",
})

#configure tracer and provider
tracer_provider = TracerProvider(resource=resource)
cloud_trace_exporter = CloudTraceSpanExporter()

span_processor = BatchSpanProcessor(cloud_trace_exporter)
tracer_provider.add_span_processor(span_processor)

# set tracer globally
trace.set_tracer_provider(tracer_provider)

# Setup tracer with a specific name
tracer = trace.get_tracer("my-application")

#Instrument the FastAPI-application
FastAPIInstrumentor.instrument_app(app)


def get_backend() -> Backend:
    global my_backend  # pylint: disable=global-statement
    if my_backend is None:
        backend_type = getenv('BACKEND', 'memory')
        print(backend_type)
        if backend_type == 'redis':
            my_backend = RedisBackend()
        elif backend_type == 'gcs':
            my_backend = GCSBackend()
        else:
            my_backend = MemoryBackend()
    return my_backend


@app.get('/')
def redirect_to_notes() -> None:
    return RedirectResponse(url='/notes')

#add spans to each key
@app.get('/notes')
def get_notes(backend: Annotated[Backend, Depends(get_backend)]) -> List[Note]:
    with tracer.start_as_current_span("add keys"):
        keys = backend.keys()

        Notes = []
        for key in keys:
            with tracer.start_as_current_span("adding single key"):
                Notes.append(backend.get(key))
        return Notes


@app.get('/notes/{note_id}')
def get_note(note_id: str,
             backend: Annotated[Backend, Depends(get_backend)]) -> Note:
    return backend.get(note_id)


@app.put('/notes/{note_id}')
def update_note(note_id: str,
                request: CreateNoteRequest,
                backend: Annotated[Backend, Depends(get_backend)]) -> None:
    backend.set(note_id, request)


@app.post('/notes')
def create_note(request: CreateNoteRequest,
                backend: Annotated[Backend, Depends(get_backend)]) -> str:
    note_id = str(uuid4())
    backend.set(note_id, request)
    return note_id





#Beispiel-Routen hinzufügen
@app.get("/trace")
async def trace_example():
    #tracer = trace.get_tracer("my-application")
    with tracer.start_as_current_span("First span"):
        time.sleep(random.random() ** 2)
        with tracer.start_as_current_span("Second span"):
            time.sleep(random.random() ** 2)
            return {"message": "This request is traced!"}