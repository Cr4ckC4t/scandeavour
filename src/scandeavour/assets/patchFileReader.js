/*
 * Fix the dcc.Upload component to allow large file uploads.
 * The main culprit was this line: https://github.com/plotly/dash/blob/0d9cd2c2a611e1b8cce21d1d46b69234c20bdb11/components/dash-core-components/src/fragments/Upload.react.js#L36
* Large files would be stored on the client side and crash the browser.
 * Here, we overwrite the FileReader.readAsDataURL to implement our own logic.
 * This sends files to a POST endpoint.
 */
class PatchFileReader extends FileReader {

	async moveDataToBackend(file) {
		// The upload itself shouldn't take to long, since this is a local app.
		// The parsing will probably take longer.
		// Alternatively, implement a stream sender to track the upload progress.

		const response = await fetch('/upload-file', {
			method: 'POST',
			body: file
		});

		/* Approach a)
		 * Send the file, the server stores it, sends back a tmp name.
		 * We send the tmp name as "content" and thus, we can access large files.
		 * This also allows us to do all the parsing logic in the dash callbacks!
		 */
		const tmpName = await response.text();
		return tmpName;

		/* Approach b)
		 * Implement an API endpoint that does all the parsing and sends progress back
		 * via streamed responses (https://flask.palletsprojects.com/en/stable/patterns/streaming/).
		 * The problem with this is, that dash can not easily access the parsing process.
		 * And I want my toasts.
		 * Anyway, here would be the prototype for the client side when a streamed response comes back:
		 * Use a stream reader to get status updates during the processing of the file. 
		 * https://developer.mozilla.org/en-US/docs/Web/API/Streams_API/Using_readable_streams
		const decoder = new TextDecoder();
		const reader = response.body.getReader();
		while (true) {
			const { done, value } = await reader.read();
			if (done) {
				// Do something with last chunk of data then exit reader
				console.log('Received final chunk.');
				return;
			}
			// Otherwise do something here to process current chunk
			console.log("Got a chunk back: ", decoder.decode(value));
		}
		 */
	}

	async readAsDataURL(file) {
		/* Start progress bar */
		document.getElementById('upload-progress').style.visibility='visible';
		document.getElementById('upload-progress').children[0].style.width='20%';
		document.getElementById('upload-progress').children[0].innerText='Uploading file(s)';

		// Synchronously send the file to Dash
		const tmpName = await this.moveDataToBackend(file);

		/* Our main goal now is to avoid Dash to store the potentialy large file in the contents attribute.
		 * Therefore, we call readAsDataURL with a custom File, with the content being the filename that
		 * we generated via the API route on the server. This informs Dash where it will find our uploaded
		 * file.
		 * Note that we don't need to pass a filename, because the
		 * onload callback of the Upload component uses the file object directly.
		 */
		super.readAsDataURL(new File([tmpName],''));
	}
}

FileReader=PatchFileReader;
