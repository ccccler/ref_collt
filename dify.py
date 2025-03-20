async def call_dify_sse(input_obj=None, api_key=''):
    url = 'https://llm.linkdoc.com/difyapi/v1/workflows/run'
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    if not input_obj:
        input_obj = {}

    data = {
        "inputs": input_obj,
        "response_mode": "streaming",
        "user": "cc"
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url=url, headers=headers, data=json.dumps(data), timeout=None) as response:
            assert response.status == 200
            async for line in response.content:
                if line:
                    try:
                        line_str = line.decode('utf-8')
                        match = re.match(r'data: ({.*})', line_str)
                        if match:
                            json_data = json.loads(match.group(1))
                            yield json_data
                    except json.JSONDecodeError as e:
                        print(f"Error decoding JSON: {e}")