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

/*
MIT License

Copyright (c) 2017 christiansalazar

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
*/

/**
 * This action will write to Cloud Object Storage.  If the Cloud Object Storage
 * service is not bound to this action or to the package containing this action,
 * then you must provide the service information as argument input to this function.
 * Cloud Functions actions accept a single parameter, which must be a JSON object.
 *
 * In this case, the args variable will look like:
 *   {
 *     "bucket": "your COS bucket name",
 *     "key": "Name of the object to write",
 *     "body": "Body of the object to write"
 *   }
 */
const CloudObjectStorage = require('ibm-cos-sdk');

async function main(args) {
	const { cos, params } = getParamsCOS(args, CloudObjectStorage);
	let response;
	const result = {
		bucket: params.bucket,
		key: params.key,
	};

	if (!params.bucket || !params.key || !params.body || !cos) {
		result.message = "bucket name, key, body, and apikey are required for this operation.";
		throw result;
	}

	try {
		response = await cos.putObject({
			Bucket: params.bucket, Key: params.key, Body: params.body,
		}).promise();
	} catch (err) {
		console.log(err);
		result.message = err.message;
	}
	result.body = response;
	return {
		headers: { 'content-type': 'application/json' },
		body: result,
	};
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

	// get info from form data
	const boundary = args && args.__ow_headers && args.__ow_headers['content-type'] &&
		args.__ow_headers['content-type'].match(/multipart\/(?:mixed|form-data);\ *boundary=(.*)/);
	const raw = args && args.__ow_body;

	if (!boundary || !raw) {
		return { cos: null, params: {} };
	}

	const parts = multipart(Buffer.from(raw, 'base64'), boundary[1]);
	let { body, bucket, key } = parts.reduce((next, part) => {
		if (part.type === 'application/json') {
			// metadata
			const metadata = JSON.parse(part.data.toString('utf-8'));
			if (metadata.bucket && metadata.key) {
				next = { ...next, ...metadata };
			}
		} else {
			// uploaded file
			next.body = part.data;
		}
		return next;
	}, {});

	if (body.type === 'Buffer') {
		body = Buffer.from(body.data);
	}

	const endpoint = args.endpoint || 's3.us.cloud-object-storage.appdomain.cloud';
	const ibmAuthEndpoint = args.ibmAuthEndpoint || 'https://iam.cloud.ibm.com/identity/token';
	const apiKeyId = args.apikey || args.apiKeyId || bxCredsApiKey || process.env.__OW_IAM_NAMESPACE_API_KEY;
	const serviceInstanceId = args.resource_instance_id || args.serviceInstanceId || bxCredsResourceInstanceId;

	const params = {};
	params.bucket = bucket;
	params.key = key;
	params.body = body;

	if (!apiKeyId) {
		const cos = null;
		return { cos, params };
	}

	const cos = new COS.S3({
		endpoint, ibmAuthEndpoint, apiKeyId, serviceInstanceId,
	});
	return { cos, params };
}

/**
 	Multipart Parser (Finite State Machine)

	usage:

	var multipart = require('./multipart.js');
	var body = multipart.DemoData(); 							   // raw body
	var body = new Buffer(event['body-json'].toString(),'base64'); // AWS case
	
	var boundary = multipart.getBoundary(event.params.header['content-type']);
	var parts = multipart.Parse(body,boundary);
	
	// each part is:
	// { filename: 'A.txt', type: 'text/plain', data: <Buffer 41 41 41 41 42 42 42 42> }

	author:  Cristian Salazar (christiansalazarh@gmail.com) www.chileshift.cl
			 Twitter: @AmazonAwsChile
 */
function multipart(multipartBodyBuffer, boundary) {
	var process = function (part) {
		// will transform this object:
		// { header: 'Content-Disposition: form-data; name="uploads[]"; filename="A.txt"',
		//	 info: 'Content-Type: text/plain',
		//	 part: 'AAAABBBB' }
		// into this one:
		// { filename: 'A.txt', type: 'text/plain', data: <Buffer 41 41 41 41 42 42 42 42> }
		var obj = function (str) {
			if (!str) return {};

			var k = str.split('=');
			var a = k[0].trim();
			var b = JSON.parse(k[1].trim());
			var o = {};
			Object.defineProperty(o, a,
				{ value: b, writable: true, enumerable: true, configurable: true })
			return o;
		}
		var header = part.header.split(';');
		var file = obj(header[2]);
		var contentType = part.info.split(':')[1].trim();
		Object.defineProperty(file, 'type',
			{ value: contentType, writable: true, enumerable: true, configurable: true })
		Object.defineProperty(file, 'data',
			{ value: Buffer.from(part.part), writable: true, enumerable: true, configurable: true })
		return file;
	}
	var prev = null;
	var lastline = '';
	var header = '';
	var info = ''; var state = 0; var buffer = [];
	var allParts = [];

	for (i = 0; i < multipartBodyBuffer.length; i++) {
		var oneByte = multipartBodyBuffer[i];
		var prevByte = i > 0 ? multipartBodyBuffer[i - 1] : null;
		var newLineDetected = ((oneByte == 0x0a) && (prevByte == 0x0d)) ? true : false;
		var newLineChar = ((oneByte == 0x0a) || (oneByte == 0x0d)) ? true : false;

		if (!newLineChar)
			lastline += String.fromCharCode(oneByte);

		if ((0 == state) && newLineDetected) {
			if (("--" + boundary) == lastline) {
				state = 1;
			}
			lastline = '';
		} else
			if ((1 == state) && newLineDetected) {
				header = lastline;
				state = 2;
				lastline = '';
			} else
				if ((2 == state) && newLineDetected) {
					info = lastline;
					state = 3;
					lastline = '';
				} else
					if ((3 == state) && newLineDetected) {
						state = 4;
						buffer = [];
						lastline = '';
					} else
						if (4 == state) {
							if (lastline.length > (boundary.length + 4)) lastline = ''; // mem save
							if (((("--" + boundary) == lastline))) {
								var j = buffer.length - lastline.length;
								var part = buffer.slice(0, j - 1);
								var p = { header: header, info: info, part: part };
								allParts.push(process(p));
								buffer = []; lastline = ''; state = 5; header = ''; info = '';
							} else {
								buffer.push(oneByte);
							}
							if (newLineDetected) lastline = '';
						} else
							if (5 == state) {
								if (newLineDetected)
									state = 1;
							}
	}
	return allParts;
};



