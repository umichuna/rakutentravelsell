function doPost(e) {
  try {
    var data = JSON.parse(e.postData.contents);
    var to = data.to;
    var subject = data.subject;
    var body = data.body;

    if (!to || !subject || !body) {
      return ContentService.createTextOutput(
        JSON.stringify({ status: "error", message: "Missing parameters" })
      ).setMimeType(ContentService.MimeType.JSON);
    }

    MailApp.sendEmail(to, subject, body);

    return ContentService.createTextOutput(
      JSON.stringify({ status: "ok" })
    ).setMimeType(ContentService.MimeType.JSON);

  } catch (err) {
    return ContentService.createTextOutput(
      JSON.stringify({ status: "error", message: err.toString() })
    ).setMimeType(ContentService.MimeType.JSON);
  }
}
