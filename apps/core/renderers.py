from rest_framework.renderers import BaseRenderer


class EventStreamRenderer(BaseRenderer):
    """Renderer passthrough para Server-Sent Events.

    Los endpoints SSE devuelven StreamingHttpResponse de Django directamente,
    pero DRF negocia el contenido ANTES de ejecutar el handler: si el cliente
    (EventSource) pide `Accept: text/event-stream` y el view solo ofrece
    JSONRenderer, DRF responde 406 sin llegar al handler. Este renderer hace
    que la negociación acepte `text/event-stream` (y `*/*`); la respuesta
    cruda pasa intacta por `finalize_response`.
    """

    media_type = "text/event-stream"
    format = "events"

    def render(self, data, accepted_media_type=None, renderer_context=None):
        return data
