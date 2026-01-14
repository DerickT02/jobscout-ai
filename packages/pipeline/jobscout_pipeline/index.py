from jobscout_ingest.registry import get_connectors


def call_connectors():
    print("Getting connectors from registry")
    connectors = get_connectors()
    for connector in connectors:
        jobs = connector.fetch()
        print(connector.name, "jobs:", len(jobs))
        for j in jobs:
            print("-", j["title"], "|" , j["departments"][0]['name'], "|", j["location"], "|", j["absolute_url"])

if __name__ == "__main__":
    call_connectors()
