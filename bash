curl -X PATCH 'http://192.168.1.90:5000/v1/parameters' \
--header 'Authorization: Bearer app-2sp4iSClLe2lMN4mCFgIoRUg' \
--header 'Content-Type: application/json' \
--data '{
  "file_upload": {
    "image": {
      "enabled": true,
      "number_limits": 3,
      "detail": "high",
      "transfer_methods": ["remote_url", "local_file"]
    }
  }
}'

curl -X GET 'http://192.168.1.90:5000/v1/parameters' --header 'Authorization: Bearer app-2sp4iSClLe2lMN4mCFgIoRUg'