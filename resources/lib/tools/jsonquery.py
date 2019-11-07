
import json
import xbmc

def json_query(query):

    xbmc_request = json.dumps(query)
    raw = xbmc.executeJSONRPC(xbmc_request)
    clean = unicode(raw, "utf-8", errors="ignore")
    response = json.loads(clean)
    result = response.get("result", response)

    return result
