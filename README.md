# Data Proxy API Service

## API Specification

### With Cloud Object Storage

This is an example for reading object.

```sh
curl -s --request POST --url "https://${ENDPOINT}/public/api/files" --header "x-ibm-client-id: ${SECRET}" --header "content-type: application/json" --data "{\"bucket\": \"${BUCKET_NAME}\", \"key\": \"${KEY_NAME}\"}"
```

This cURL command is for writing object.

```sh
curl -ik --request POST --url "https://${ENDPOINT}/private/api/files" --header "x-ibm-client-id: ${SECRET}" -H "content-type: multipart/mixed" -F "data=@${FILE_PATH}" -F "metadata={\"bucket\": \"${BUCKET_NAME}\", \"key\": \"${KEY_NAME}\"};type=application/json"
```

### With Cloudant

This is an example for reading documents.

```sh
curl -ik --request POST --url "https://${ENDPOINT}/public/api/docs" --header "content-type: application/json" --header "x-ibm-client-id: ${SECRET}" --data "{\"dbname\": \"${DB_NAME}\", \"query\": {\"selector\": {}, \"fields\":[], \"sort\":[]}}"
```

This cURL command is for writing data.

```sh
curl -s --request POST --url "https://${ENDPOINT}/private/api/docs" --header "x-ibm-client-id: ${SECRET}" --header "content-type: application/json" --data "{\"bucket\": \"${BUCKET_NAME}\", \"key\": \"OBJECT_KEY\"}"

curl -ik --request POST --url "https://${ENDPOINT}/private/api/docs" --header "x-ibm-client-id: ${SECRET}" --header 'content-type: application/json' --data "{\"dbname\":\"${DBNAME}\",\"doc\":{}}"
```

## How to deploy the data-proxy

First, run the following command with parameters for your environment.

```sh
cd deploy
# if you want to get help, please run
python3 ./deploy.py --help

python3 ./deploy.py -o create -r jp-tok -g c4c-covid-19 -n data-proxy -c cos-hmac-reader,cos-hmac-writer -l cloudant-key-reader,cloudant-key-writer
```

IBM Cloud doesn't provide CLI for adding API keys on API... So, we should do it manually. Please follow the next steps for both public and private API, which means please do the following steps two times.

1. go to the Functions page and select the namaspace you created above.

2. click the "public-api" in the api list

3. click "Define and Secure" menu, and turn the "Require application authentication via API key" on, then clicking the save button at the bottom of the page.

4. click "Manage Sharing and Keys" menu, and click "create API key" in the section "Sharing within IBM Cloud account", then adding key name and clicking "create" button.

5. copy API key and save it in `.api-list` created by the script `deploy.py`. Please follow the following format. When creating the key for public API, fill it in the format of `PUBLIC_API_KEY=COPIED_API_KEY`, as well as fill it in `PRIVATE_API_KEY=COPIED_API_KEY` when creating the private one.

As for private API, we also need to associate it with App ID. Unfortunately, CLI also doesn't support the association so that this should be done manuarly.

1. go to the Functions page and select the namaspace you created above.

2. click the "private-api" in the api list

3. click "Define and Secure" menu, and turn the "OAuth user authentication" on and select "IBM Cloud App ID" for the provider as well as `app-id` or the instance name you decided for the App ID service, then clicking the save button at the bottom of the page.

Lastly, copy and paste all environment variables to `covsafe-view/build/.env`.

## How to delete the data-proxy

```sh
cd deploy
python3 ./deploy.py -o delete -r jp-tok -g c4c-covid-19 -n data-proxy -c cos-hmac-reader,cos-hmac-writer -l cloudant-key-reader,cloudant-key-writer
```
