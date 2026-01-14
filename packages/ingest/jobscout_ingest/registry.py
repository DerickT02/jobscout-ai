#call all connectors in this file to grab the jobs
from jobscout_ingest.sites.Google import GoogleCareersQuery, GoogleCareersConnector
from jobscout_ingest.connectors.Greenhouse import GreenhouseConnector, GreenhouseQuery



def get_connectors():
    return [
        GreenhouseConnector(GreenhouseQuery(board_token="stripe")),
        GreenhouseConnector(GreenhouseQuery(board_token="anthropic")),
    ]