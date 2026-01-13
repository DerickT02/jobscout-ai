#call all connectors in this file to grab the jobs
from jobscout_ingest.sites.Google import GoogleCareersQuery, GoogleCareersConnector



def get_connectors():
    return [
        GoogleCareersConnector(
            GoogleCareersQuery(
             locations=['California', 'United States']   
            )
        )
    ]