import json
import urllib.request
import urllib.parse
from html.parser import HTMLParser

try:
    req = urllib.request.Request('http://localhost:9222/json')
    with urllib.request.urlopen(req) as response:
        targets = json.loads(response.read())

    ws_url = next((t['webSocketDebuggerUrl'] for t in targets if 'moodle.usherbrooke' in t.get('url', '')), None)

    if ws_url:
        import websocket
        ws = websocket.create_connection(ws_url, suppress_origin=True)
        
        script = """
        JSON.stringify({
            html: document.body.innerHTML
        })
        """
        
        ws.send(json.dumps({
            'id': 1,
            'method': 'Runtime.evaluate',
            'params': {'expression': script, 'returnByValue': True}
        }))
        
        result = json.loads(ws.recv())
        ws.close()
        
        val = result.get('result', {}).get('result', {}).get('value')
        if val:
            parsed = json.loads(val)
            with open("moodle_dom_structure.json", "w", encoding="utf-8") as f:
                json.dump(parsed, f, indent=2, ensure_ascii=False)
            print("Successfully saved to moodle_dom_structure.json")
        else:
            print("No value returned. Result:", result)
    else:
        print('Moodle tab not found in CDP.')
except Exception as e:
    print(f"Connection failed: {e}")
