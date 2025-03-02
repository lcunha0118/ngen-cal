from pydantic import BaseModel, Field
from typing import Optional, Mapping, Sequence
from datetime import datetime
from .configurations import Forcing, Time, Routing
from .formulation import Formulation

class Realization(BaseModel):
    """Simple model of a Realization, containing formulations and forcing
    """
    formulations: Sequence[Formulation]
    forcing: Forcing

class CatchmentRealization(Realization):
    forcing: Optional[Forcing]

class NgenRealization(BaseModel):
    """A complete ngen realization confiiguration model, including global and catchment overrides
    """
    global_config: Realization = Field(alias='global')
    time: Time
    routing: Optional[Routing]
    #FIXME have not tested catchments...
    catchments: Optional[ Mapping[str, CatchmentRealization] ] = {}

    #FIXME https://github.com/samuelcolvin/pydantic/issues/2277
    #Until 1.10, it looks like nested encoder config doesn't apply
    #so you have to define the encoder at the top level object that
    #will be serialized...
    class Config:
        allow_population_by_field_name = True
        json_encoders = {
            datetime: lambda v: v.strftime("%Y-%m-%d %H:%M:%S")
        }
