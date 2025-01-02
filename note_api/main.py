# -*- coding: utf-8 -*-
from uuid import uuid4
from typing import List, Optional
from os import getenv
from typing_extensions import Annotated

from fastapi import Depends, FastAPI
from starlette.responses import RedirectResponse
from .backends import Backend, RedisBackend, MemoryBackend, GCSBackend
from .model import Note, CreateNoteRequest

app = FastAPI()

my_backend: Optional[Backend] = None


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


@app.get('/notes')
def get_notes(backend: Annotated[Backend, Depends(get_backend)]) -> List[Note]:
    keys = backend.keys()

    Notes = []
    for key in keys:
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
########################################################
#For Exercise 4:
# Configuration of the trace provider
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider

#from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter


import os

#Setze die Umgebungsvariable für den Google Cloud-Dienstkontoschlüssel
#os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "path/to/google-cloud-key.json" #TODO

#Konfiguriere den TracerProvider und Exporter
tracer_provider = TracerProvider()
#cloud_trace_exporter = CloudTraceSpanExporter()

# OTLP Exporter hinzufügen (für Google Cloud Operations oder andere OTLP-kompatible Plattformen)
# Authentifizierung erfolgt automatisch in Cloud Run
otlp_exporter = OTLPSpanExporter()#endpoint="https://otel.googleapis.com:443")  
span_processor = BatchSpanProcessor(otlp_exporter)
tracer_provider.add_span_processor(span_processor)

#Füge den BatchSpanProcessor hinzu
#span_processor = BatchSpanProcessor(cloud_trace_exporter)
#tracer_provider.add_span_processor(span_processor)

# Setze den Tracer Provider global
trace.set_tracer_provider(tracer_provider)

# Erstelle einen Tracer mit einem spezifischen Namen
tracer = trace.get_tracer("my-application")

#Instrumentiere die FastAPI-Anwendung
FastAPIInstrumentor.instrument_app(app)

#Beispiel-Routen hinzufügen
@app.get("/trace")
async def trace_example():
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("example-span"):
        return {"message": "This request is traced!"}
    
@app.get("/echo")
def echo()->str:
    return(os.environ['GOOGLE_APPLICATION_CREDENTIALS'])
#######################################################