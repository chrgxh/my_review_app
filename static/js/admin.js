const form = document.getElementById("reviewRequestForm");
const previewButton = document.getElementById("previewButton");

previewButton.addEventListener("click", function () {
    const recipientEmail = document.getElementById("recipientEmail").value;
    const identifier = document.getElementById("identifier").value;
    const message = document.getElementById("message").value;

    const params = new URLSearchParams({
        recipientEmail: recipientEmail,
        identifier: identifier,
        message: message
    });

    window.open(`/preview-email?${params.toString()}`, "_blank");
});

form.addEventListener("submit", function () {
    form.action = "/request-feedback";
    form.method = "post";
    form.target = "_self";
});