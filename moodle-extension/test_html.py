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
            fetch('https://moodle.usherbrooke.ca/mod/assign/view.php?id=3022003')
            .then(res => res.text())
            .then(html => {
                const regex = /href="(https?:\\/\\/[^\\/]+\\/pluginfile\\.php\\/[^\\/]+\\/mod_assign\\/introattachment\\/0\\/[^"]+)"/g;
                let matches = [];
                let match;
                while ((match = regex.exec(html)) !== null) {
                    matches.push(match[1]);
                }
                resolve(JSON.stringify(matches));
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
            data = json.loads(val)
            print("Successfully extracted links:", data)
        else:
            print('Script returned no value. Result:', result)
    else:
        print('Moodle tab not found.')
except Exception as e:
    print('Error:', e)
