from datetime import date
from typing import List, Optional

from aiohttp import web
from pydantic import BaseModel

from argantic import Argantic


class Model(BaseModel):
    name: str
    birth_date: date
    skills: Optional[List[str]]


def handler(req: web.Request, model: Model):
    return web.json_response(text=model.json())


argantic = Argantic()
app = web.Application(middlewares=[argantic.middleware()])

app.router.add_get('/person', handler)
app.router.add_post('/person', handler)

web.run_app(app, host='localhost', port=8080)
