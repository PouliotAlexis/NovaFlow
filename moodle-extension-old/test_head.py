import json, urllib.request, websocket

try:
    req = urllib.request.Request('http://localhost:9222/json')
    with urllib.request.urlopen(req) as response:
        targets = json.loads(response.read())

    ws_url = next((t['webSocketDebuggerUrl'] for t in targets if 'moodle.usherbrooke' in t.get('url', '')), None)

    if ws_url:
        ws = websocket.create_connection(ws_url, suppress_origin=True)
        
        script = """
        new Promise((resolve) => {
            const logoutLink = document.querySelector('a[href*="logout.php?sesskey="]');
            if (!logoutLink) return resolve(JSON.stringify({error: 'No sesskey'}));
            
            const directUrl = "https://moodle.usherbrooke.ca/pluginfile.php/4409149/mod_assign/introattachment/0/Devoir1%20H2026.pdf?forcedownload=1&redirect=1";
            
            fetch(directUrl, { method: 'HEAD' })
            .then(res => {
                let headersObj = {};
                for (let [key, value] of res.headers.entries()) {
                    headersObj[key] = value;
                }
                resolve(JSON.stringify({
                    status: res.status,
                    url: res.url,
                    headers: headersObj
                }));
            }).catch(err => resolve(JSON.stringify({error: err.toString()})));
        })
        """
        
        ws.send(json.dumps({
            'id': 1,
            'method': 'Runtime.evaluate',
            'params': {'expression': script, 'awaitPromise': True, 'returnByValue': True}
        }))
        
        result = json.loads(ws.recv())
        ws.close()
        
        val = result.get('result', {}).get('result', {}).get('value')
        if val:
            print("HEAD Request Result:", json.loads(val))
        else:
            print('Script returned no value. Result:', result)
    else:
        print('Moodle tab not found.')
except Exception as e:
    print('Error:', e)
