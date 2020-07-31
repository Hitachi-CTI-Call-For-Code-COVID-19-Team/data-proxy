/*
Copyright 2020 Hitachi Ltd.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

/**
 * This action will read from Cloud Object Storage.  If the Cloud Object Storage
 * service is not bound to this action or to the package containing this action,
 * then you must provide the service information as argument input to this function.
 * Cloud Functions actions accept a single parameter, which must be a JSON object.
 *
 * In this case, the args variable will look like:
 *   {
 *     "bucket": "your COS bucket name",
 *     "key": "Name of the object to read"
 *   }
 */
const CloudObjectStorage = require('ibm-cos-sdk');


async function main(args) {
  const { cos, params } = getParamsCOS(args, CloudObjectStorage);
  let response;
  const result = params;

  if (!params.bucket || !params.key || !cos) {
    result.message = "bucket name, key, and apikey are required for this operation.";
    throw result;
  }

  try {
    response = await cos.getObject({ Bucket: params.bucket, Key: params.key }).promise();
  } catch (err) {
    console.log(err);
    result.message = err.message;
    throw result;
  }

  result.headers = {
    'content-type': response.ContentType
  };
  result.body = isBinary(response.ContentType) ? response.Body.toString('base64') : response.Body.toString('utf-8');

  return result;
}

function getParamsCOS(args, COS) {
  var bxCredsApiKey;
  var bxCredsResourceInstanceId;

  if (args.__bx_creds && args.__bx_creds['cloud-object-storage']) {
    if (args.__bx_creds['cloud-object-storage'].apikey) {
      bxCredsApiKey = args.__bx_creds['cloud-object-storage'].apikey;
    }
    if (args.__bx_creds['cloud-object-storage'].resource_instance_id) {
      bxCredsResourceInstanceId = args.__bx_creds['cloud-object-storage'].resource_instance_id;
    }
  }

  var bucket, key;
  if (args.bucket && args.key) {
    bucket = args.bucket;
    key = args.key;
  } else if (args.__ow_body) {
    decoded = JSON.parse(Buffer.from(args.__ow_body, 'base64').toString('utf-8'));
    bucket = decoded.bucket;
    key = decoded.key;
  }

  const endpoint = args.endpoint || 's3.us.cloud-object-storage.appdomain.cloud';
  const ibmAuthEndpoint = args.ibmAuthEndpoint || 'https://iam.cloud.ibm.com/identity/token';
  const apiKeyId = args.apikey || args.apiKeyId || bxCredsApiKey || process.env.__OW_IAM_NAMESPACE_API_KEY;
  const serviceInstanceId = args.resource_instance_id || args.serviceInstanceId || bxCredsResourceInstanceId;

  const params = {};
  params.bucket = bucket;
  params.key = key;

  if (!apiKeyId) {
    const cos = null;
    return { cos, params };
  }

  const cos = new COS.S3({
    endpoint, ibmAuthEndpoint, apiKeyId, serviceInstanceId,
  });
  return { cos, params };
}

function isBinary(contentType) {
  if (contentType.startsWith('text/') || contentType.startsWith('message/'))
    return false;
  if (contentType.startsWith('audio/') || contentType.startsWith('image/') ||
    contentType.startsWith('video/') || contentType.startsWith('font/'))
    return true;
  return mediaTypes[contentType];
}

const mediaTypes = {
  "application/atom+xml": false,
  "application/base64": true,
  "application/excel": true,
  "application/font-woff": true,
  "application/font-woff2": true,
  "application/gnutar": true,
  "application/java-archive": true,
  "application/javascript": false,
  "application/json": true,
  "application/json-patch+json": true,
  "application/lha": true,
  "application/lzx": true,
  "application/mspowerpoint": true,
  "application/msword": true,
  "application/octet-stream": true,
  "application/pdf": true,
  "application/postscript": true,
  "application/rss+xml": false,
  "application/soap+xml": false,
  "application/vnd.api+json": true,
  "application/vnd.google-earth.kml+xml": false,
  "application/vnd.google-earth.kmz": true,
  "application/vnd.ms-fontobject": true,
  "application/vnd.oasis.opendocument.chart": true,
  "application/vnd.oasis.opendocument.database": true,
  "application/vnd.oasis.opendocument.formula": true,
  "application/vnd.oasis.opendocument.graphics": true,
  "application/vnd.oasis.opendocument.image": true,
  "application/vnd.oasis.opendocument.presentation": true,
  "application/vnd.oasis.opendocument.spreadsheet": true,
  "application/vnd.oasis.opendocument.text": true,
  "application/vnd.oasis.opendocument.text-master": true,
  "application/vnd.oasis.opendocument.text-web": true,
  "application/vnd.openxmlformats-officedocument.presentationml.presentation": true,
  "application/vnd.openxmlformats-officedocument.presentationml.slide": true,
  "application/vnd.openxmlformats-officedocument.presentationml.slideshow": true,
  "application/vnd.openxmlformats-officedocument.presentationml.template": true,
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": true,
  "application/vnd.openxmlformats-officedocument.spreadsheetml.template": true,
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": true,
  "application/vnd.openxmlformats-officedocument.wordprocessingml.template": true,
  "application/x-7z-compressed": true,
  "application/x-ace-compressed": true,
  "application/x-apple-diskimage": true,
  "application/x-arc-compressed": true,
  "application/x-bzip": true,
  "application/x-bzip2": true,
  "application/x-chrome-extension": true,
  "application/x-compress": true,
  "application/x-compressed": true,
  "application/x-debian-package": true,
  "application/x-dvi": true,
  "application/x-font-truetype": true,
  "application/x-font-opentype": true,
  "application/x-gtar": true,
  "application/x-gzip": true,
  "application/x-latex": true,
  "application/x-rar-compressed": true,
  "application/x-redhat-package-manager": true,
  "application/x-shockwave-flash": true,
  "application/x-tar": true,
  "application/x-tex": true,
  "application/x-texinfo": true,
  "application/x-vrml": false,
  "application/x-www-form-urlencoded": false,
  "application/x-x509-ca-cert": true,
  "application/x-xpinstall": true,
  "application/xhtml+xml": false,
  "application/xml-dtd": false,
  "application/xml": false,
  "application/zip": true
};