from serpapi import GoogleSearch

params = {
  "engine": "google_trends",
  "q": "football",
  "data_type": "GEO_MAP_0",
  "api_key": "934b601b0908067948a53616306c790179658a297a2e103379a55d09e7b75a7c",
  "date": "today 5-y",
  "region": "IN",
}

search = GoogleSearch(params)
results = search.get_dict()
interest_by_region = results["interest_by_region"]
print(interest_by_region)
