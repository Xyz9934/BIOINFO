import requests

def get_medline_info(disease):
    url = "https://connect.medlineplus.gov/service"

    params = {
        "mainSearchCriteria.v.c": disease,
        "knowledgeResponseType": "application/json"
    }

    try:
        res = requests.get(url, params=params)
        data = res.json()

        entry = data['feed']['entry'][0]

        title = entry['title']['_value']
        summary = entry['summary']['_value']

        return title, summary

    except Exception as e:
        return "No Data", "No medical info found"