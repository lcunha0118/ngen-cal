import pytest
from typing import Generator
from pathlib import Path
from copy import deepcopy
import json
import pandas as pd # type: ignore
import geopandas as gpd # type: ignore
from ..configuration import General
from ..ngen import Ngen
from ..meta import CalibrationMeta
from ..calibration_cathment import CalibrationCatchment
from hypy import Nexus, HydroLocation

from .utils import *

@pytest.fixture(scope="session")
def workdir(tmpdir_factory):
    return tmpdir_factory.mktemp("workdir")

@pytest.fixture(scope="session")
def realization_config(tmpdir_factory) -> str:
    """
        Fixture to provide a staged testing input files
    """
    fn = tmpdir_factory.mktemp("data").join("realization_config.json")
    with(open(fn, 'w')) as fp:
        json.dump(config, fp)
    return fn

@pytest.fixture(scope="session")
def general_config(workdir) -> General:
    """A general configuration using default values where possible

    Returns:
        General: _description_

    Yields:
        Iterator[General]: _description_
    """
    #override the workdir, must do this to properly clean up
    #test states, even though this technically overrides the default
    general_w_defaults.update({"workdir": workdir})
    general = General(**general_w_defaults)
    return general

@pytest.fixture(scope="session")
def general_config_custom(workdir) -> General:
    """A general configuration using custom values for all possible defaults

    Returns:
        General: _description_

    Yields:
        Iterator[General]: _description_
    """
    #override the workdir
    general_no_defaults.update({"workdir": workdir})
    general = General(**general_no_defaults)
    return general

@pytest.fixture(scope="session")
def ngen_config(realization_config) -> Ngen:
    """Fixture to provided a staged ngen configuration

    Args:
        realization_config (str): path to realization config for ngen

    Returns:
        Ngen: Ngen model data class and configuration

    Yields:
        Iterator[Ngen]: Ngen model data class and configuration
    """
    ngen_config = {"type":"ngen",
                   "realization": realization_config,
                   "catchments": Path(__file__).parent/"data/catchment_data.geojson",
                   "nexus": Path(__file__).parent/"data/nexus_data.geojson",
                   "crosswalk": Path(__file__).parent/"data/crosswalk.json",
                   "binary": "echo ngen"}
    model = Ngen(**ngen_config)
    return model

# @pytest.fixture
# def conf(realization_config, workdir) -> Generator[Configuration, None, None]:
#     """
#         Staging of a generator to test
#     """
#     catchment_data = Path(__file__).parent/"data/catchment_data.geojson"
#     nexus_data = Path(__file__).parent/"data/nexus_data.geojson"
#     x_walk = Path(__file__).parent/"data/crosswalk.json"
#     yield Configuration(realization_config, catchment_data, nexus_data, x_walk, workdir)

@pytest.fixture
def meta(ngen_config, general_config, mocker) -> Generator[CalibrationMeta, None, None]:
    """
        build up a meta object to test
    """
    m = CalibrationMeta(ngen_config, general_config)
    #Override the eval range property
    #should probably refactor to allow testing of eval range,
    #but that also rquires creating a MockLocation using a time range
    #that we can subset out of for creation of a meta object
    mocker.patch(__name__+'.CalibrationMeta.evaluation_range',
                new_callable=mocker.PropertyMock,
                return_value = None
                )
    yield m

@pytest.fixture
def fabric():
    """
        Mock geoseries for defining catchment gemomentry/attributes
    """
    catchment_data = Path(__file__).parent/"data/catchment_data.geojson"
    df = gpd.read_file(catchment_data)
    return df.loc[0]

class MockLocation:
    def __init__(self):
        now = pd.Timestamp.now().round('H')
        self.ts = pd.DataFrame({'value':[1,2,3,4,5], "value_time":pd.date_range(now, periods=5, freq='H')})

    def get_data(self, *args, **kwargs):
        return self.ts

@pytest.fixture
def nexus():
    """
        Mock nexus for building catchments
    """
    id = "test_nexus"
    nexus = Nexus(id, MockLocation())

    return nexus

@pytest.fixture
def catchment(nexus, fabric, workdir, mocker) -> Generator[CalibrationCatchment, None, None]:
    """
        A hy_features catchment implementing the calibratable interface
    """
    output = nexus._hydro_location.get_data().rename(columns={'value':'sim_flow'})
    output.set_index('value_time', inplace=True)
    #Override the output property so it doesn't try to reload output each time
    mocker.patch(__name__+'.CalibrationCatchment.output',
                new_callable=mocker.PropertyMock,
                return_value = output
                )
    #Disable output saving for testing purpose
    mocker.patch(__name__+'.CalibrationCatchment.save_output',
                return_value=None)

    id = 'tst-1'
    data = deepcopy(config)['catchments'][id] # type: ignore
    #now = pd.Timestamp.now().round('H')
    #ts = pd.DataFrame({'obs_flow':[1,2,3,4,5]}, index=pd.date_range(now, periods=5, freq='H'))
    start = output.index[0]
    end = output.index[-1]
    catchment = CalibrationCatchment(workdir, id, nexus, start, end, fabric, data)
    #Reset observed here since it does unit conversion from cfs -> cms
    catchment.observed = output.rename(columns={'sim_flow':'obs_flow'})
    return catchment

@pytest.fixture
def catchment2(nexus, fabric, workdir) -> Generator[CalibrationCatchment, None, None]:
    """
        A hy_features catchment implementing the calibratable interface
        Doesn't mock output, can be used to test semantics of erronous output
    """
    ts = nexus._hydro_location.get_data().rename(columns={'value':'obs_flow'})
    ts.set_index('value_time', inplace=True)

    id = 'tst-1'
    data = deepcopy(config)['catchments'][id] # type: ignore
    #now = pd.Timestamp.now().round('H')
    #ts = pd.DataFrame({'obs_flow':[1,2,3,4,5]}, index=pd.date_range(now, periods=5, freq='H'))
    start = ts.index[0]
    end = ts.index[-1]
    catchment = CalibrationCatchment(workdir, id, nexus, start, end, fabric, data)

    return catchment
